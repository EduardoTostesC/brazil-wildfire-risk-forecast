"""Extract a contiguous demonstration interval from actual processed observations."""

import json

import pandas as pd

from src.config import get_project_root
from src.data.manifest import compute_sha256


def main():
    root = get_project_root()
    output = root / "data/sample"
    grid = pd.read_csv(root / "data/processed/grid.csv")
    grid = grid[grid.state_status != "outside"]
    source = root / "data/processed/features.parquet"
    filters = [("date", ">=", pd.Timestamp("2024-08-12")), ("date", "<=", pd.Timestamp("2024-08-18"))]
    frame = pd.read_parquet(source, filters=filters)
    frame = frame[frame.grid_id.isin(grid.grid_id)].sort_values(["grid_id", "date"])
    frame.to_parquet(output / "features_sample.parquet", index=False)
    grid.to_csv(output / "grid_sample.csv", index=False)
    raw = pd.read_parquet(root / "data/processed/dataset.parquet", filters=filters)
    raw = raw[raw.grid_id.isin(grid.grid_id)]
    raw[["date", "grid_id", "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "WS10M"]].to_csv(output / "climate_sample.csv", index=False)
    metadata = {"purpose": "Historical demonstration, not an unbiased evaluation sample",
                "selection": "All territorial cells, 2024-08-12 through 2024-08-18 inclusive; observed records only",
                "rows": len(frame), "cells": frame.grid_id.nunique(), "source_features_sha256": compute_sha256(source),
                "sample_sha256": compute_sha256(output / "features_sample.parquet")}
    (output / "sample_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
