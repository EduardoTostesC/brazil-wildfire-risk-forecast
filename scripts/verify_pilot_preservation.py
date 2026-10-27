"""Compare the scientific pilot bytes with the explicitly selected historical commit."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

BASE = "c1bead578bb0417538df56fd7f232477fba1c519"
ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ("models/", "data/", "reports/", "docs/audits/", "src/", "api/", "app/",
             "tests/", "scripts/", "config.yaml", "dvc.yaml", "dvc.lock",
             "requirements", "pyproject.toml")


def verify(root=ROOT, base=BASE):
    """New files are allowed; every selected historical file must remain byte-identical."""
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args])

    commit = git("rev-parse", "--verify", base + "^{commit}").decode().strip()
    names = git("ls-tree", "-r", "--name-only", "-z", commit).decode().split("\0")
    checked, failures = {}, []
    for name in filter(None, names):
        if not name.startswith(PROTECTED):
            continue
        expected = hashlib.sha256(git("show", f"{commit}:{name}")).hexdigest()
        path = root / name
        if not path.is_file() or path.is_symlink():
            failures.append(name)
            continue
        current = hashlib.sha256(path.read_bytes()).hexdigest()
        checked[name] = current
        if current != expected:
            failures.append(name)
    return {"base_commit": commit, "checked_files": len(checked),
            "sha256": checked, "changed_or_missing": failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(base=args.base)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Historical files checked: {result['checked_files']}; changed/missing: {len(result['changed_or_missing'])}")
    if result["changed_or_missing"]:
        raise SystemExit("Historical pilot modified: " + ", ".join(result["changed_or_missing"]))


if __name__ == "__main__":
    main()
