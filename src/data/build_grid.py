"""Build a regular geographic grid over the configured region.

Creates a grid of cells with the configured resolution (default 0.25°) and
assigns each cell a unique ID based on its row and column index.
"""

import numpy as np
import pandas as pd

from src.config import get_project_root, load_config


def build_grid(config: dict | None = None) -> pd.DataFrame:
    """Generate a regular lat/lon grid for the configured region.

    Each cell is identified by (grid_id, lat_center, lon_center). The grid_id
    encodes the row and column index for easy neighbor lookup.

    Args:
        config: Optional config dict.

    Returns:
        DataFrame with columns: grid_id, lat_center, lon_center, lat_min, lat_max, lon_min, lon_max.
    """
    cfg = config or load_config()
    res = cfg["grid"]["resolution_deg"]
    region = cfg["region"]

    lat_edges = np.arange(region["lat_min"], region["lat_max"] + res, res)
    lon_edges = np.arange(region["lon_min"], region["lon_max"] + res, res)

    rows: list[dict] = []
    for i in range(len(lat_edges) - 1):
        for j in range(len(lon_edges) - 1):
            rows.append({
                "grid_id": f"{i:03d}_{j:03d}",
                "grid_row": i,
                "grid_col": j,
                "lat_center": round((lat_edges[i] + lat_edges[i + 1]) / 2, 4),
                "lon_center": round((lon_edges[j] + lon_edges[j + 1]) / 2, 4),
                "lat_min": round(lat_edges[i], 4),
                "lat_max": round(lat_edges[i + 1], 4),
                "lon_min": round(lon_edges[j], 4),
                "lon_max": round(lon_edges[j + 1], 4),
            })

    grid_df = pd.DataFrame(rows)
    return grid_df


def assign_to_grid(
    lat: float | np.ndarray,
    lon: float | np.ndarray,
    config: dict | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Assign latitude/longitude points to grid cells.

    Args:
        lat: Latitude(s).
        lon: Longitude(s).
        config: Optional config dict.

    Returns:
        Tuple of (grid_row, grid_col) arrays.
    """
    cfg = config or load_config()
    res = cfg["grid"]["resolution_deg"]
    region = cfg["region"]

    lat = np.asarray(lat)
    lon = np.asarray(lon)

    grid_row = np.floor((lat - region["lat_min"]) / res).astype(int)
    grid_col = np.floor((lon - region["lon_min"]) / res).astype(int)

    return grid_row, grid_col


def save_grid(config: dict | None = None) -> pd.DataFrame:
    """Build and save the grid to data/processed/grid.csv.

    Returns:
        The grid DataFrame.
    """
    cfg = config or load_config()
    grid_df = build_grid(cfg)
    root = get_project_root()
    out_path = root / "data" / "processed"
    out_path.mkdir(parents=True, exist_ok=True)
    grid_df.to_csv(out_path / "grid.csv", index=False)
    print(f"Grid saved: {len(grid_df)} cells ({grid_df['grid_row'].nunique()} rows × {grid_df['grid_col'].nunique()} cols)")
    return grid_df


if __name__ == "__main__":
    print("Building geographic grid...")
    grid = save_grid()
    print(f"Lat range: {grid['lat_min'].min():.2f} to {grid['lat_max'].max():.2f}")
    print(f"Lon range: {grid['lon_min'].min():.2f} to {grid['lon_max'].max():.2f}")
    print("Done!")

