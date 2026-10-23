"""Generate or verify exhaustive local data fingerprints and quality evidence."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.config import get_project_root, load_config
from src.data.build_grid import _load_ibge_polygon, build_grid
from src.data.quality import climate_quality, fire_quality


def compute_sha256(filepath: Path) -> str:
    digest = hashlib.sha256()
    with filepath.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_manifest(root: Path, cfg: dict) -> dict:
    files = sorted(set((root / "data/raw").glob("*/*.csv")) |
                   set((root / "data/processed").glob("*.parquet")) |
                   set((root / "data/processed").glob("*.csv")) |
                   set((root / "data/sample").glob("*")) |
                   set((root / "data/geo").glob("*.geojson")))
    entries = []
    for path in files:
        entry = {"file": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size,
                 "sha256": compute_sha256(path)}
        if path.suffix == ".csv":
            df = pd.read_csv(path)
            entry.update(rows=len(df), columns=df.columns.tolist())
            if path.parent.name == "climate":
                entry["quality"] = climate_quality(df, f"{cfg['data']['start_year']}-01-01",
                                                    f"{cfg['data']['end_year']}-12-31", path.stem.removeprefix("climate_"))
            elif path.parent.name == "fire":
                suffix = path.stem.rsplit("_", 1)[-1]
                entry["quality"] = fire_quality(df, int(suffix) if suffix.isdigit() else None, cfg["data"]["satellite"])
        elif path.suffix == ".parquet":
            parquet = pq.ParquetFile(path)
            entry.update(rows=parquet.metadata.num_rows, columns=parquet.schema_arrow.names,
                         schema={f.name: str(f.type) for f in parquet.schema_arrow})
            subset = pd.read_parquet(path, columns=[c for c in ("date", "grid_id") if c in entry["columns"]])
            if "date" in subset:
                entry.update(date_min=str(subset.date.min()), date_max=str(subset.date.max()),
                             duplicate_keys=int(subset.duplicated(["grid_id", "date"]).sum()))
        entries.append(entry)
    expected_climate = {f"data/raw/climate/climate_{gid}.csv" for gid in build_grid(cfg).grid_id}
    expected_fire = {f"data/raw/fire/focos_{cfg['region']['state_code']}_{year}.csv"
                     for year in range(cfg["data"]["start_year"], cfg["data"]["end_year"] + 1)}
    existing = {e["file"] for e in entries}
    return {"schema_version": 2, "project": "brazil-wildfire-risk-forecast", "scope": "local_files_not_a_public_data_archive",
            "sources": {"INPE": cfg["data"]["fire_base_url"], "NASA_POWER": cfg["data"]["power_base_url"],
                        "IBGE": "https://servicodados.ibge.gov.br/api/v3/malhas/estados/51?formato=application/vnd.geo+json"},
            "time_basis": "Legacy POWER requests used default LST; INPE dates were UTC. Publication timestamps were not archived.",
            "missing_expected_files": sorted((expected_climate | expected_fire) - existing), "entries": entries}


def generate_data_manifest(config: dict | None = None, root: Path | None = None) -> dict:
    root = root or get_project_root()
    result = collect_manifest(root, config or load_config())
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    path = root / "data/data_manifest.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Generated {len(result['entries'])} fingerprints; missing={len(result['missing_expected_files'])}")
    return result


def verify_data_manifest(config: dict | None = None, root: Path | None = None) -> list[str]:
    root = root or get_project_root()
    saved = json.loads((root / "data/data_manifest.json").read_text(encoding="utf-8"))
    if saved.get("schema_version") != 2:
        return ["Unsupported legacy manifest: regenerate explicitly with --generate; verification did not modify it."]
    current = collect_manifest(root, config or load_config())
    errors = [f"Missing required source: {name}" for name in current["missing_expected_files"]]
    before, after = ({e["file"]: e for e in doc["entries"]} for doc in (saved, current))
    for name in sorted(before.keys() | after.keys()):
        if before.get(name) != after.get(name):
            errors.append(f"Fingerprint/schema/coverage changed: {name}")
        quality = after.get(name, {}).get("quality")
        if quality and not quality["valid"]:
            errors.append(f"Source quality failed: {name}")
        if after.get(name, {}).get("duplicate_keys", 0):
            errors.append(f"Duplicate cell/date records: {name}")
    _load_ibge_polygon(root)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--generate", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        errors = verify_data_manifest()
        print("\n".join(errors) if errors else "Manifest verified: hashes, sizes, schemas and source coverage match.")
        raise SystemExit(1 if errors else 0)
    generate_data_manifest()


if __name__ == "__main__":
    main()
