"""The national expansion must detect changes to historical scientific evidence."""

import subprocess

from scripts.verify_pilot_preservation import verify


def test_preservation_detects_modified_missing_files_and_allows_new_lineage(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args])

    git("init", "--quiet")
    (tmp_path / "models").mkdir()
    model = tmp_path / "models/pilot.bin"
    model.write_bytes(b"historical model")
    (tmp_path / "data").mkdir()
    data = tmp_path / "data/sample.csv"
    data.write_bytes(b"date,value\n2024-08-15,1\n")
    git("add", ".")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--quiet", "-m", "historical")
    base = git("rev-parse", "HEAD").decode().strip()
    (tmp_path / "models/national.bin").write_bytes(b"different lineage")
    assert verify(tmp_path, base)["changed_or_missing"] == []
    model.write_bytes(b"accidental overwrite")
    data.unlink()
    assert verify(tmp_path, base)["changed_or_missing"] == ["data/sample.csv", "models/pilot.bin"]
    assert model.read_bytes() == b"accidental overwrite"  # read-only verification
