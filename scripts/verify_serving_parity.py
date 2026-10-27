"""Compare actual HTTP inference from audited and runtime-only environments."""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1e-12


def request(url, endpoint, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url + endpoint, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def compare(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        assert set(a) == set(b)
        return max((compare(a[k], b[k]) for k in a if k != "processed_at"), default=0.)
    if isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b)
        return max((compare(x, y) for x, y in zip(a, b)), default=0.)
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        assert math.isclose(a, b, abs_tol=TOLERANCE, rel_tol=0), (a, b)
        return abs(a - b)
    assert a == b, (a, b)
    return 0.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-url")
    parser.add_argument("--candidate-url")
    parser.add_argument("--reference-python", default=sys.executable)
    parser.add_argument("--candidate-python", default=sys.executable)
    parser.add_argument("--candidate-thread-limit", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/evidence/publication/serving-parity.json")
    args = parser.parse_args()
    if bool(args.reference_url) != bool(args.candidate_url):
        parser.error("Supply both URLs or neither")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    processes, logs = [], []
    urls = [args.reference_url, args.candidate_url] if args.reference_url else ["http://127.0.0.1:8008", "http://127.0.0.1:8009"]
    try:
        if not args.reference_url:
            for python, port in [(args.reference_python, 8008), (args.candidate_python, 8009)]:
                environment = dict(os.environ, WILDFIRE_USE_SAMPLE="1", PYTHONIOENCODING="utf-8")
                if port == 8009 and args.candidate_thread_limit:
                    environment["OMP_THREAD_LIMIT"] = str(args.candidate_thread_limit)
                log = (args.output.parent / f"parity-server-{port}.txt").open("w", encoding="utf-8")
                logs.append(log)
                processes.append(subprocess.Popen([python, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(port)],
                    cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        for url in urls:
            for _ in range(120):
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError("Serving process exited; inspect logs")
                try:
                    status, health = request(url, "/health")
                    if status == 200 and health["status"] == "ok" and health["available_horizons"] == [1, 3, 7]:
                        break
                except (OSError, KeyError):
                    pass
                time.sleep(.5)
            else:
                raise RuntimeError("Serving readiness timeout")
        results = []
        for latitude in [-11.0, -12.5, -13.0]:
            for date in ["2024-08-12", "2024-08-15", "2024-08-18"]:
                for horizon in (1, 3, 7):
                    payload = dict(latitude=latitude, longitude=-55., date=date, horizon_days=horizon)
                    for endpoint in ["/predict", "/explain"]:
                        first_status, first = request(urls[0], endpoint, payload)
                        second_status, second = request(urls[1], endpoint, payload)
                        assert first_status == second_status == 200, (payload, first, second)
                        difference = compare(first, second)
                        results.append({"endpoint": endpoint, "request": payload, "reference_probability": first["probability"],
                            "candidate_probability": second["probability"], "model_version": first["model_version"],
                            "max_absolute_numeric_difference": difference, "statuses": [first_status, second_status]})
        invalid = [(dict(latitude=-12.5, longitude=-55., date="2026-08-15"), 404),
                   (dict(latitude=-22., longitude=-40., date="2024-08-15"), 422),
                   (dict(latitude=-12.5, longitude=-55., date="2024-08-15", inference_mode="operational_forecast"), 503)]
        for payload, expected in invalid:
            for url in urls:
                status, _ = request(url, "/predict", payload)
                assert status == expected
        record = {"git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "api_source_sha256": hashlib.sha256((ROOT / "api/main.py").read_bytes()).hexdigest(),
            "candidate_OMP_THREAD_LIMIT": args.candidate_thread_limit or None,
            "absolute_tolerance": TOLERANCE, "relative_tolerance": 0, "ignored_dynamic_field": "processed_at",
            "success_response_pairs": len(results), "error_responses_checked": 6,
            "maximum_absolute_numeric_difference": max(x["max_absolute_numeric_difference"] for x in results), "cases": results}
        args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"Verified {len(results)} response pairs and 6 errors; maximum numeric difference {record['maximum_absolute_numeric_difference']}")
    finally:
        for process in processes:
            process.terminate()
            process.wait(timeout=20)
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()
