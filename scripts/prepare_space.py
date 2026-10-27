"""Export an explicit runtime allowlist; never copies raw data, secrets or caches."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".venv/hf-space")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Refusing to overwrite a nonempty export directory")
    if output == ROOT or ROOT.is_relative_to(output):
        raise SystemExit("Export must not contain the source workspace")
    files = ["config.yaml", "requirements-serving.lock", ".streamlit/config.toml", "app/locales.json",
             "app/requirements.txt", "data/geo/mato_grosso_ibge.geojson", "data/sample/features_sample.parquet",
             "data/sample/sample_metadata.json", "models/artifact_manifest.json", "reports/drift_report.json",
             "reports/model_comparison.csv", "reports/multi_horizon_comparison.csv", "reports/walk_forward_metrics.csv",
             "scripts/smoke_api.py", "LICENSE"]
    files += [p.relative_to(ROOT).as_posix() for directory in ("app", "api", "src") for p in (ROOT / directory).rglob("*.py")]
    files += ["models/" + name for name in json.loads((ROOT / "models/artifact_manifest.json").read_text())["files"]]
    mapping = {name: name for name in files}
    mapping.update({"Dockerfile.serving": "Dockerfile", "README.hf.md": "README.md"})
    fingerprints = {}
    for source, destination in mapping.items():
        path = (ROOT / source).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f"Invalid export source: {source}")
        target = output / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
        fingerprints[destination] = digest
    (output / "export-manifest.json").write_text(json.dumps({"files": fingerprints,
        "scope": "runtime code, frozen model bundle and existing public demonstration sample; no complete raw archive"}, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(fingerprints)} allowlisted files; no upload performed")


if __name__ == "__main__":
    main()
