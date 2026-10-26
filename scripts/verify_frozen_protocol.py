"""Check the frozen protocol identity and model/schema hashes without future data."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify_protocol(root=ROOT):
    path = root / "reports/protocol/future-2027-v1.json"
    document = (root / "reports/PROTOCOLO_CONFIRMATORIO_CONGELADO.md").read_text(encoding="utf-8")
    match = re.search(r"Protocol JSON SHA256: `([a-f0-9]{64})`", document)
    errors = []
    if not match or match[1] != hashlib.sha256(path.read_bytes()).hexdigest():
        errors.append("Frozen protocol JSON digest mismatch")
    protocol = json.loads(path.read_text(encoding="utf-8"))
    for name, expected in protocol["file_sha256"].items():
        target = (root / name).resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            errors.append(f"Missing or invalid frozen path: {name}")
        elif hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            errors.append(f"Frozen artifact mismatch: {name}")
    metadata = json.loads((root / "models/training_metadata.json").read_text(encoding="utf-8"))
    if protocol["feature_schema"] != metadata["feature_cols"]:
        errors.append("Frozen feature schema mismatch")
    return errors


if __name__ == "__main__":
    problems = verify_protocol()
    if problems:
        raise SystemExit("\n".join(problems))
    print("Frozen protocol and model/schema hashes verified; no future observations accessed")
