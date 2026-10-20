"""Feature engineering for wildfire risk prediction.

All features use ONLY information available up to day D (the prediction date).
No future data leaks into features. This is enforced by:
1. All rolling windows look BACKWARD in time.
2. Fire count on day D itself IS available (the satellite has already passed).
3. The target uses days D+1 to D+7 (strictly future).

Features created:
- Fire history: count of hotspots in the cell over 7/14/30 days, and same
  period last year. Also neighbor cell fire counts.
- Climate: rolling means/sums for temperature, humidity, precipitation, wind.
- Dry spell: consecutive days without rain (precip < 1mm).
- Seasonality: cyclic encoding of month and day-of-year using sin/cos.
- Position: latitude and longitude of the cell center.
"""

import numpy as np
import pandas as pd

from src.config import get_project_root, load_config


def build_features(config: dict | None = None) -> pd.DataFrame:
    """Load the processed dataset and add engineered features.

    Args:
        config: Optional config dict.

    Returns:
        DataFrame with all features added, saved to data/processed/features.parquet.
    """
    cfg = config or load_config()
    root = get_project_root()

    # Load processed dataset
    ds_path = root / "data" / "processed" / "dataset.parquet"
    df = pd.read_parquet(ds_path)
    df = df.sort_values(["grid_id", "date"]).reset_index(drop=True)

    print(f"Loaded dataset: {df.shape}")
    print("Building features (backward-looking only)...")

    # --- 1. Fire history features (per cell) ---
    print("  [1/5] Fire history...")
    for window in [7, 14, 30]:
        df[f"fire_count_{window}d"] = (
            df.groupby("grid_id")["fire_count"]
            .transform(lambda s: s.rolling(window, min_periods=1).sum())
        )

    # Same period last year (365 days ago ± 7 days window)
    df["fire_count_lastyear"] = (
        df.groupby("grid_id")["fire_count"]
        .transform(lambda s: s.shift(358).rolling(14, min_periods=1).sum())
    )

    # --- 2. Neighbor fire counts ---
    print("  [2/5] Neighbor fire activity...")
    # Pivot to get fire_count per day per cell, then for each cell sum neighbors
    _add_neighbor_features(df, cfg)

    # --- 3. Climate rolling features ---
    print("  [3/5] Climate features...")
    climate_vars = ["T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "WS10M"]
    existing_climate = [v for v in climate_vars if v in df.columns]

    for var in existing_climate:
        for window in [7, 14]:
            df[f"{var}_mean_{window}d"] = (
                df.groupby("grid_id")[var]
                .transform(lambda s: s.rolling(window, min_periods=1).mean())
            )
        if var == "PRECTOTCORR":
            # Accumulated precipitation
            for window in [7, 14, 30]:
                df[f"precip_sum_{window}d"] = (
                    df.groupby("grid_id")[var]
                    .transform(lambda s: s.rolling(window, min_periods=1).sum())
                )

    # --- 4. Dry spell (consecutive days without rain) ---
    print("  [4/5] Dry spell...")
    if "PRECTOTCORR" in df.columns:
        df["is_dry"] = (df["PRECTOTCORR"].fillna(0) < 1.0).astype(int)
        df["dry_days"] = (
            df.groupby("grid_id")["is_dry"]
            .transform(_consecutive_count)
        )
        df = df.drop(columns=["is_dry"])
    else:
        df["dry_days"] = 0

    # --- 5. Seasonality and position ---
    print("  [5/5] Seasonality and position...")
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear

    # Cyclic encoding: sin/cos transform preserves continuity
    # (Dec 31 is close to Jan 1, unlike raw month numbers)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

    # Position features (already in the dataset as lat_center, lon_center)
    # These help the model learn spatial patterns without explicit spatial modeling

    # --- Drop intermediate columns ---
    cols_to_drop = ["fire_count", "month", "day_of_year"]
    cols_to_drop = [c for c in cols_to_drop if c in df.columns]
    df = df.drop(columns=cols_to_drop)

    # --- Save ---
    out_path = root / "data" / "processed" / "features.parquet"
    df.to_parquet(out_path, index=False)

    feature_cols = [c for c in df.columns if c not in ("grid_id", "date", "target", "grid_row", "grid_col")]
    print(f"\nFeatures saved: {out_path}")
    print(f"  Shape: {df.shape}")
    print(f"  Feature count: {len(feature_cols)}")
    print(f"  Features: {feature_cols}")

    return df


def _consecutive_count(series: pd.Series) -> pd.Series:
    """Count consecutive True/1 values ending at each position.

    For example, [1, 1, 0, 1, 1, 1] → [1, 2, 0, 1, 2, 3].
    """
    groups = (series != series.shift()).cumsum()
    return series.groupby(groups).cumsum()


def _add_neighbor_features(df: pd.DataFrame, cfg: dict) -> None:
    """Add fire counts from neighboring grid cells (in-place).

    For each cell, sums fire_count_7d from the 8 surrounding cells.
    This captures spatial fire spread patterns.
    """
    # Build a lookup of (row, col) neighbors
    if "grid_row" not in df.columns or "grid_col" not in df.columns:
        df["neighbor_fire_7d"] = 0
        return

    # Pivot: date × grid_id → fire_count_7d
    fire_7d_pivot = df.pivot_table(
        index="date", columns="grid_id", values="fire_count_7d", fill_value=0
    )

    # For each cell, identify its 8 neighbors and sum
    grid_lookup = df[["grid_id", "grid_row", "grid_col"]].drop_duplicates()
    neighbor_map: dict[str, list[str]] = {}

    for _, row in grid_lookup.iterrows():
        r, c = int(row["grid_row"]), int(row["grid_col"])
        neighbors = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nid = f"{r + dr:03d}_{c + dc:03d}"
                if nid in fire_7d_pivot.columns:
                    neighbors.append(nid)
        neighbor_map[row["grid_id"]] = neighbors

    # Compute neighbor sums
    neighbor_sums = {}
    for gid, neighbors in neighbor_map.items():
        if neighbors:
            neighbor_sums[gid] = fire_7d_pivot[neighbors].sum(axis=1)
        else:
            neighbor_sums[gid] = pd.Series(0, index=fire_7d_pivot.index)

    # Melt back and merge
    neighbor_df = pd.DataFrame(neighbor_sums)
    neighbor_df.index.name = "date"
    neighbor_melted = neighbor_df.reset_index().melt(
        id_vars="date", var_name="grid_id", value_name="neighbor_fire_7d"
    )
    neighbor_melted["date"] = pd.to_datetime(neighbor_melted["date"])

    # Merge into main dataframe
    df_idx = df.set_index(["grid_id", "date"]).index
    neighbor_melted = neighbor_melted.set_index(["grid_id", "date"])
    df["neighbor_fire_7d"] = df.set_index(["grid_id", "date"]).join(
        neighbor_melted, how="left"
    )["neighbor_fire_7d"].values
    df["neighbor_fire_7d"] = df["neighbor_fire_7d"].fillna(0)


if __name__ == "__main__":
    print("=" * 60)
    print("Building features")
    print("=" * 60)
    build_features()
    print("\nDone!")

