"""Process raw fire and climate data into a unified tabular dataset.

Steps:
1. Load fire hotspot data, assign each hotspot to a grid cell and date.
2. Aggregate: count hotspots per cell per day.
3. Load and merge climate data for each cell.
4. Create the binary target: at least one hotspot in the cell in the next 7 days.
5. Save the processed dataset.

IMPORTANT: The target is computed BEFORE feature engineering to keep the logic
clear. The target for day D uses fire data from days D+1 to D+7, which is
information from the future that the model must predict, NOT use as input.
"""

import pandas as pd
import numpy as np
from pathlib import Path

from src.config import get_project_root, load_config
from src.data.build_grid import build_grid, assign_to_grid


def process_data(config: dict | None = None) -> pd.DataFrame:
    """Build the processed dataset from raw fire + climate data.

    Args:
        config: Optional config dict.

    Returns:
        Processed DataFrame saved to data/processed/dataset.parquet.
    """
    cfg = config or load_config()
    root = get_project_root()
    horizon = cfg["model"]["forecast_horizon_days"]

    # --- 1. Load and assign fire data to grid ---
    print("Step 1: Loading fire data...")
    fire_dir = root / "data" / "raw" / "fire"
    state = cfg["region"]["state_code"]
    fire_file = fire_dir / f"focos_{state}_all.csv"
    if not fire_file.exists():
        raise FileNotFoundError(f"Combined fire file not found: {fire_file}")

    fire_df = pd.read_csv(fire_file)

    # Parse date from the datetime column
    if "data_hora_gmt" in fire_df.columns:
        fire_df["date"] = pd.to_datetime(
            fire_df["data_hora_gmt"], errors="coerce"
        ).dt.date
    elif "datahora" in fire_df.columns:
        fire_df["date"] = pd.to_datetime(
            fire_df["datahora"], errors="coerce"
        ).dt.date
    else:
        # Try common alternatives
        date_cols = [c for c in fire_df.columns if "data" in c.lower() or "date" in c.lower()]
        if date_cols:
            fire_df["date"] = pd.to_datetime(fire_df[date_cols[0]], errors="coerce").dt.date
        else:
            raise ValueError(f"No date column found. Columns: {list(fire_df.columns)}")

    fire_df = fire_df.dropna(subset=["date", "lat", "lon"])
    fire_df["date"] = pd.to_datetime(fire_df["date"])

    # Assign to grid cells
    grid_row, grid_col = assign_to_grid(fire_df["lat"].values, fire_df["lon"].values, cfg)
    fire_df["grid_row"] = grid_row
    fire_df["grid_col"] = grid_col
    fire_df["grid_id"] = fire_df["grid_row"].apply(lambda x: f"{x:03d}") + "_" + fire_df["grid_col"].apply(lambda x: f"{x:03d}")

    # Aggregate: count hotspots per cell per day
    fire_daily = (
        fire_df.groupby(["grid_id", "date"])
        .agg(fire_count=("lat", "size"))
        .reset_index()
    )
    print(f"  Fire data: {len(fire_df):,} hotspots -> {len(fire_daily):,} cell-day records")

    # --- 2. Build full date × cell grid ---
    print("Step 2: Building full date × cell grid...")
    grid_df = build_grid(cfg)
    date_range = pd.date_range(
        start=f"{cfg['data']['start_year']}-01-01",
        end=f"{cfg['data']['end_year']}-12-31",
        freq="D",
    )

    # Create all cell-date combinations
    full_index = pd.MultiIndex.from_product(
        [grid_df["grid_id"].values, date_range],
        names=["grid_id", "date"],
    )
    dataset = pd.DataFrame(index=full_index).reset_index()
    print(f"  Full grid: {len(dataset):,} cell-day records "
          f"({len(grid_df)} cells × {len(date_range)} days)")

    # Merge fire counts
    dataset = dataset.merge(fire_daily, on=["grid_id", "date"], how="left")
    dataset["fire_count"] = dataset["fire_count"].fillna(0).astype(int)

    # --- 3. Create binary target ---
    print(f"Step 3: Creating binary target (horizon={horizon} days)...")
    # For each cell, the target at day D is: any fire in [D+1, D+7]?
    # We compute a rolling sum over the NEXT 7 days.
    # Sorting by date ascending, a forward-looking window = shift(-1) then rolling(7).
    dataset = dataset.sort_values(["grid_id", "date"]).reset_index(drop=True)

    # Use groupby + shift to look into the future
    def _compute_target(group: pd.DataFrame) -> pd.Series:
        # Sum of fire_count in the next `horizon` days (exclusive of current day)
        future_fires = (
            group["fire_count"]
            .shift(-1)                       # start from tomorrow
            .rolling(window=horizon, min_periods=1)  # next 7 days
            .sum()
            .shift(-(horizon - 1))           # align to the first future day
        )
        return (future_fires > 0).astype(int)

    dataset["target"] = (
        dataset.groupby("grid_id", group_keys=False)
        .apply(_compute_target)
    )

    # Drop rows where target cannot be computed (last 7 days of the dataset)
    dataset = dataset.dropna(subset=["target"])
    dataset["target"] = dataset["target"].astype(int)

    # --- 4. Merge climate data ---
    print("Step 4: Merging climate data...")
    climate_dir = root / "data" / "raw" / "climate"
    climate_frames: list[pd.DataFrame] = []
    for csv_file in sorted(climate_dir.glob("climate_*.csv")):
        cdf = pd.read_csv(csv_file)
        cdf["date"] = pd.to_datetime(cdf["date"])
        climate_frames.append(cdf)

    if climate_frames:
        climate_df = pd.concat(climate_frames, ignore_index=True)
        dataset = dataset.merge(climate_df, on=["grid_id", "date"], how="left")
        print(f"  Climate data merged: {len(climate_df):,} records")
    else:
        print("  [warn] No climate data found. Proceeding without climate variables.")

    # --- 5. Add grid metadata ---
    print("Step 5: Adding grid metadata...")
    grid_meta = grid_df[["grid_id", "grid_row", "grid_col", "lat_center", "lon_center"]]
    dataset = dataset.merge(grid_meta, on="grid_id", how="left")

    # --- 6. Save ---
    out_dir = root / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dataset.parquet"
    dataset.to_parquet(out_path, index=False)
    print(f"\nDataset saved: {out_path}")
    print(f"  Shape: {dataset.shape}")
    print(f"  Target distribution: {dataset['target'].value_counts().to_dict()}")
    print(f"  Date range: {dataset['date'].min()} to {dataset['date'].max()}")

    return dataset


if __name__ == "__main__":
    print("=" * 60)
    print("Processing raw data into tabular dataset")
    print("=" * 60)
    process_data()
    print("\nDone!")
