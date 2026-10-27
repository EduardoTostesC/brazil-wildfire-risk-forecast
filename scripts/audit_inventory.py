"""Capture a reproducible, read-only inventory of the reference checkout."""

import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/evidence"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8", errors="replace")


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    commits = git("rev-list", "--reverse", "HEAD").splitlines()
    history = []
    for sha in commits:
        diff = git("show", "--root", "--format=fuller", "--find-renames", sha)
        (OUT / f"commit-{sha[:7]}.txt").write_text(diff, encoding="utf-8")
        history.append({"sha": sha, "subject": git("show", "-s", "--format=%s", sha).strip(),
                        "files": git("diff-tree", "--root", "--no-commit-id", "--name-status", "-r", sha).splitlines()})
    files = []
    for name in git("ls-files").splitlines():
        path = ROOT / name
        data = path.read_bytes()
        files.append({"file": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        if path.suffix == ".ipynb":
            nb = json.loads(data)
            cells = [f"CELL {i} ({c['cell_type']}):\n{''.join(c.get('source', []))}\n" +
                     "\n".join("".join(o.get("text", [])) + str(o.get("data", {}).get("text/plain", ""))
                               for o in c.get("outputs", [])) for i, c in enumerate(nb["cells"])]
            (OUT / f"{path.stem}-cells.txt").write_text("\n\n".join(cells), encoding="utf-8")
    datasets = []
    for path in sorted((ROOT / "data/processed").glob("*")):
        if path.suffix not in {".csv", ".parquet"}:
            continue
        df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
        info = {"file": path.relative_to(ROOT).as_posix(), "shape": df.shape,
                "schema": {c: str(t) for c, t in df.dtypes.items()}, "missing": df.isna().sum().to_dict()}
        if "date" in df:
            info.update(date_min=str(df.date.min()), date_max=str(df.date.max()),
                        duplicates=int(df.duplicated(["grid_id", "date"]).sum()), cells=int(df.grid_id.nunique()))
        if "state_status" in df:
            info["state_status"] = df.state_status.value_counts().to_dict()
        datasets.append(info)
    versions = {}
    for name in ["numpy", "pandas", "lightgbm", "scikit-learn", "scipy", "shapely", "torch", "pytest", "ruff", "mlflow", "dvc", "streamlit"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    remote = {}
    for suffix in ["", "/branches", "/tags", "/releases", "/pulls?state=all", "/actions/runs?per_page=10"]:
        try:
            response = requests.get("https://api.github.com/repos/EduardoTostesC/brazil-wildfire-risk-forecast" + suffix, timeout=30)
            response.raise_for_status()
            remote[suffix or "metadata"] = response.json()
        except requests.RequestException as exc:
            remote[suffix or "metadata"] = {"error": str(exc)}
    result = {"head": git("rev-parse", "HEAD").strip(), "branch": git("branch", "--show-current").strip(),
              "os": platform.platform(), "python": platform.python_version(), "versions": versions,
              "docker": shutil.which("docker"), "history": history, "files": files, "datasets": datasets}
    (OUT / "initial-inventory.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT / "initial-github.json").write_text(json.dumps(remote, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"files", "history"}}, indent=2))
    runs = remote.get("/actions/runs?per_page=10", {}).get("workflow_runs", [])
    print("REMOTE RUNS", [(r["id"], r["head_sha"], r["conclusion"]) for r in runs])


if __name__ == "__main__":
    main()
