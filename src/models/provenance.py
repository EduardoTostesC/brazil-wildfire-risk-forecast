"""Capture source bytes, Git state and explicit inputs before an experiment runs."""

import hashlib
import importlib.metadata
import platform
import subprocess
from pathlib import Path


def capture_execution(root: Path, inputs=()) -> dict:
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    commit = git("rev-parse", "HEAD").decode().strip()
    sources = sorted({*root.glob("src/**/*.py"), *root.glob("api/*.py"), *root.glob("app/*.py"),
                      *(root / name for name in ["config.yaml", "requirements.txt", "requirements.lock",
                                                "requirements-cpu.lock", "pyproject.toml"] if (root / name).is_file())})
    tracked = set(git("ls-tree", "-r", "--name-only", commit).decode().splitlines())
    sources = sorted(set(sources) | {root / name for name in tracked
                                    if (name.startswith(("src/", "api/", "app/")) and name.endswith(".py"))
                                    or name in {"config.yaml", "requirements.txt", "requirements.lock", "requirements-cpu.lock", "pyproject.toml"}})
    fingerprints = {}
    for path in sources:
        name = path.relative_to(root).as_posix()
        if not path.is_file():
            fingerprints[name] = {"missing": True, "matches_commit_after_eol_normalization": False}
            continue
        raw = path.read_bytes()
        normalized = raw.replace(b"\r\n", b"\n")
        head = git("show", commit + ":" + name) if name in tracked else None
        fingerprints[name] = {"sha256": hashlib.sha256(raw).hexdigest(),
                              "sha256_lf": hashlib.sha256(normalized).hexdigest(),
                              "matches_commit_after_eol_normalization": head is not None and normalized == head.replace(b"\r\n", b"\n")}
    versions = {}
    for name in ["numpy", "pandas", "scikit-learn", "lightgbm", "torch", "scipy", "mlflow", "dvc"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    input_hashes = {}
    for name in inputs:
        digest = hashlib.sha256()
        with (root / name).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        input_hashes[name] = digest.hexdigest()
    return {"commit_at_start": commit,
            "working_tree_dirty_at_start": bool(git("status", "--porcelain").strip()),
            "sources_match_commit": all(v["matches_commit_after_eol_normalization"] for v in fingerprints.values()),
            "source_files": fingerprints, "input_sha256": input_hashes,
            "python": platform.python_version(), "platform": platform.platform(), "versions": versions,
            "note": "Captured before execution. Matching source bytes do not prove source-data publication timing."}
