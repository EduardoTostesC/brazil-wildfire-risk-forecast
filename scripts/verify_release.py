"""Test a committed snapshot without private raw/processed data in both interpreters."""

import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    checkout = ROOT / ".venv" / ("release-" + commit[:10])
    if checkout.exists():
        raise RuntimeError(f"Snapshot already exists; preserve it and create a new commit before repeating: {checkout}")
    archive = ROOT / ".venv" / ("release-" + commit[:10] + ".zip")
    subprocess.run(["git", "archive", "--format=zip", "--output", str(archive), commit], cwd=ROOT, check=True)
    checkout.mkdir()
    with zipfile.ZipFile(archive) as source:
        source.extractall(checkout)
    if (checkout / "data/raw").exists() or (checkout / "data/processed").exists():
        raise RuntimeError("Private data accidentally entered the committed snapshot")
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    results = {"commit": commit, "snapshot": checkout.name, "private_data_present": False, "checks": []}
    for label in ["py311", "py312"]:
        executable = ROOT / ".venv" / label / "Scripts/python.exe"
        logfile = ROOT / f"reports/evidence/clean-{label}.txt"
        xml = ROOT / f"reports/evidence/clean-{label}.xml"
        command = [str(executable), "-m", "pytest", "tests/", "-v", "--tb=short", f"--junitxml={xml}"]
        with logfile.open("w", encoding="utf-8") as stream:
            completed = subprocess.run(command, cwd=checkout, env=environment, stdout=stream, stderr=subprocess.STDOUT)
        results["checks"].append({"interpreter": label, "command": command[1:], "exit_code": completed.returncode,
                                  "log_sha256": hashlib.sha256(logfile.read_bytes()).hexdigest()})
        print(label, "pytest exit:", completed.returncode, flush=True)
        if completed.returncode:
            print(logfile.read_text(encoding="utf-8")[-6000:])
    for module in ["src.models.artifacts", "src.reporting.generate_readme_metrics", "src.reporting.generate_research_tables"]:
        command = [str(ROOT / ".venv/py312/Scripts/python.exe"), "-m", module,
                   "--verify" if module == "src.models.artifacts" else "--check"]
        completed = subprocess.run(command, cwd=checkout, env=environment, capture_output=True, text=True)
        results["checks"].append({"module": module, "exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
    evidence = ROOT / "reports/evidence/clean-snapshot-validation.json"
    evidence.write_text(json.dumps(results, indent=2), encoding="utf-8")
    raise SystemExit(1 if any(check["exit_code"] for check in results["checks"]) else 0)


if __name__ == "__main__":
    main()
