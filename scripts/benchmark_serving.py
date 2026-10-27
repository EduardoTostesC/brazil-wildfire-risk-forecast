"""Isolated-process HTTP latency, startup, CPU and sampled RSS benchmark."""

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil
import requests

ROOT = Path(__file__).resolve().parents[1]


def summary(rows, elapsed):
    values = np.asarray([row["latency_ms"] for row in rows])
    return {"requests": len(rows), "elapsed_seconds": elapsed,
            "p50_ms": float(np.percentile(values, 50)), "p95_ms": float(np.percentile(values, 95)),
            "p99_ms": float(np.percentile(values, 99)), "mean_ms": float(values.mean()),
            "sample_std_ms": float(values.std(ddof=1)) if len(values) > 1 else None,
            "errors": sum(row["status"] != 200 for row in rows), "requests_per_second": len(rows) / elapsed}


def hardware():
    cpu = platform.processor()
    if os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    return {"os": platform.platform(), "cpu": cpu, "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(), "total_ram_bytes": psutil.virtual_memory().total,
            "controller_python": platform.python_version(), "psutil": psutil.__version__}


def run_once(args, index, output):
    environment = dict(os.environ, WILDFIRE_USE_SAMPLE="1", PYTHONIOENCODING="utf-8")
    if args.thread_limit:
        environment["OMP_THREAD_LIMIT"] = str(args.thread_limit)
    probe = subprocess.run([args.python, "scripts/serving_probe.py"], cwd=ROOT, env=environment,
                            capture_output=True, encoding="utf-8", errors="replace", check=True)
    load_measurements = json.loads(probe.stdout)
    base = "http://127.0.0.1:8012"
    logfile = (output / f"server-{index}.txt").open("w", encoding="utf-8")
    started = time.perf_counter()
    child = subprocess.Popen([args.python, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8012"],
        cwd=ROOT, env=environment, stdout=logfile, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    process = psutil.Process(child.pid)
    memory, rows = [], []
    stop = threading.Event()
    def tree():
        return [process, *process.children(recursive=True)]
    def cpu_snapshot():
        result = {}
        for member in tree():
            try:
                times = member.cpu_times()
                result[member.pid] = times.user + times.system
            except psutil.Error:
                pass
        return result
    def sample_memory():
        while not stop.is_set():
            try:
                snapshots = [member.memory_info().rss for member in tree()]
                memory.append({"seconds_since_spawn": time.perf_counter() - started,
                               "tree_rss_bytes": sum(snapshots), "largest_process_rss_bytes": max(snapshots), "processes": len(snapshots)})
            except psutil.Error:
                return
            stop.wait(.02)
    thread = threading.Thread(target=sample_memory, daemon=True)
    thread.start()
    session = requests.Session()
    session.trust_env = False
    payload = dict(latitude=-12.5, longitude=-55., date="2024-08-15", horizon_days=7)
    def timed(endpoint, horizon, scenario, client=None):
        client = client or requests
        body = dict(payload, horizon_days=horizon)
        before = time.perf_counter()
        response = client.get(base + endpoint, timeout=60) if endpoint == "/health" else client.post(base + endpoint, json=body, timeout=60)
        record = {"run": index, "scenario": scenario, "endpoint": endpoint, "horizon": horizon,
                  "status": response.status_code, "latency_ms": (time.perf_counter() - before) * 1000}
        return record
    try:
        for _ in range(300):
            if child.poll() is not None:
                raise RuntimeError("Benchmark server exited; inspect log")
            try:
                response = session.get(base + "/health", timeout=.5)
                if response.status_code == 200 and response.json()["status"] == "ok":
                    break
            except requests.RequestException:
                pass
            time.sleep(.05)
        else:
            raise RuntimeError("API startup timed out")
        startup = time.perf_counter() - started
        cpu_start = cpu_snapshot()
        api_process = max(tree(), key=lambda member: member.memory_info().rss)
        measured_start = time.perf_counter()
        scenarios = {}
        before = time.perf_counter()
        cold = [timed("/predict", 7, "first_predict", session)]
        rows.extend(cold)
        scenarios["first_predict"] = summary(cold, time.perf_counter() - before)
        for endpoint in ["/health", "/predict", "/explain"]:
            for horizon in ([0] if endpoint == "/health" else [1, 3, 7]):
                scenario = f"warm_{endpoint[1:]}_{horizon}d"
                timed(endpoint, horizon, "unmeasured_warmup", session)
                before = time.perf_counter()
                batch = [timed(endpoint, horizon, scenario, session) for _ in range(args.requests)]
                rows.extend(batch)
                scenarios[scenario] = summary(batch, time.perf_counter() - before)
        before = time.perf_counter()
        def concurrent_request(i):
            return timed("/predict" if i % 2 == 0 else "/explain", [1, 3, 7][i % 3], "concurrent_mixed")
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            batch = list(executor.map(concurrent_request, range(args.concurrent_requests)))
        rows.extend(batch)
        scenarios["concurrent_mixed"] = summary(batch, time.perf_counter() - before)
        duration = time.perf_counter() - measured_start
        cpu_end = cpu_snapshot()
        cpu_seconds = sum(max(0, total - cpu_start.get(pid, 0)) for pid, total in cpu_end.items())
        info = api_process.memory_info()
        result = {"run": index, "startup_to_ready_seconds": startup, "isolated_load_probe": load_measurements,
            "api_process_pid": api_process.pid, "processes_at_ready": len(cpu_start),
            "sampled_peak_api_rss_bytes": max(row["largest_process_rss_bytes"] for row in memory),
            "sampled_peak_tree_rss_bytes": max(row["tree_rss_bytes"] for row in memory),
            "final_api_rss_bytes": info.rss, "os_peak_api_working_set_bytes": getattr(info, "peak_wset", None),
            "cpu_seconds_during_requests": cpu_seconds, "request_phase_seconds": duration,
            "cpu_percent_one_logical_core_basis": 100 * cpu_seconds / duration,
            "concurrency": args.concurrency, "scenarios": scenarios}
        return result, rows, memory
    finally:
        session.close()
        stop.set()
        thread.join(timeout=2)
        for member in reversed(tree()):
            try:
                member.terminate()
            except psutil.Error:
                pass
        child.wait(timeout=20)
        logfile.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Interpreter running the API, separate from this controller")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--concurrent-requests", type=int, default=120)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--thread-limit", type=int, default=0, help="OpenMP thread cap for child processes; 0 inherits environment")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/benchmarks/serving-process-tree")
    args = parser.parse_args()
    if min(args.requests, args.concurrent_requests, args.runs) < 2 or not 1 <= args.concurrency <= 16:
        parser.error("Need at least 2 observations/runs and concurrency in [1,16]")
    args.python = str(Path(args.python).resolve()) if Path(args.python).is_file() else args.python
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Refusing to overwrite existing benchmark evidence")
    args.output.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    snapshot = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                ["api/main.py", "scripts/benchmark_serving.py", "scripts/serving_probe.py", "requirements-serving.lock", "models/artifact_manifest.json"]}
    matches = {}
    for name in snapshot:
        old = subprocess.run(["git", "show", head + ":" + name], cwd=ROOT, capture_output=True)
        matches[name] = old.returncode == 0 and old.stdout.replace(b"\r\n", b"\n") == (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
    record = {"started_utc": datetime.now(timezone.utc).isoformat(), "git_head_before_execution": head,
        "working_tree_dirty_at_start": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip()),
        "sources_match_recorded_commit_after_eol_normalization": matches,
        "source_sha256_before_execution": snapshot, "hardware": hardware(),
        "method": {"rss_sampling_interval_seconds": .02, "percentiles": "NumPy linear interpolation", "source": "existing public sample only",
            "OMP_THREAD_LIMIT": str(args.thread_limit) if args.thread_limit else os.environ.get("OMP_THREAD_LIMIT"),
            "process_scope": "API child and launcher descendants; largest-process RSS identifies API on Windows venv redirectors. Tree RSS may count shared pages more than once.",
            "serial_connections": "requests.Session keep-alive; one unmeasured warmup per scenario",
            "concurrent_connections": "fresh requests connection per call; mixed predict/explain and 1/3/7 days",
            "cold": "new process; OS filesystem caches are not flushed; no production network latency guarantee"}, "runs": []}
    all_rows = []
    for index in range(1, args.runs + 1):
        result, rows, memory = run_once(args, index, args.output)
        record["runs"].append(result)
        all_rows.extend(rows)
        (args.output / f"memory-{index}.json").write_text(json.dumps(memory, indent=2) + "\n", encoding="utf-8")
        print(f"Run {index}: {len(rows)} measured requests, peak sampled API RSS {result['sampled_peak_api_rss_bytes']} bytes")
    for name, expected in snapshot.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Source changed during measurement: {name}")
    with (args.output / "requests.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    record["http_errors"] = sum(row["status"] != 200 for row in all_rows)
    (args.output / "results.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if record["http_errors"]:
        raise SystemExit("HTTP errors occurred; results retained")


if __name__ == "__main__":
    main()
