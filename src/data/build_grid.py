"""Build a regular geographic grid over the configured region with IBGE territorial masking.

Creates a grid of cells with the configured resolution (default 0.5°) and
applies the official IBGE state boundary (SIRGAS 2000) to classify each cell as:
- 'inside': completely within the state (coverage >= 95%)
- 'partial': intersecting the border (0% < coverage < 95%)
- 'outside': completely outside the state boundary (coverage = 0%)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import get_project_root, load_config


def _load_ibge_polygon(root: Path):
    """Load official IBGE state polygon if available."""
    geo_path = root / "data" / "geo" / "mato_grosso_ibge.geojson"
    if not geo_path.exists():
        return None
    try:
        from shapely.geometry import shape
        with open(geo_path, "r", encoding="utf-8") as f:
            geojson = json.load(f)
        return shape(geojson["features"][0]["geometry"])
    except Exception:
        return None


def build_grid(
    config: dict | None = None,
    filter_outside: bool | None = None,
) -> pd.DataFrame:
    """Generate a regular lat/lon grid for the configured region with state masking.

    Args:
        config: Optional config dict.
        filter_outside: If True, exclude cells strictly outside the state boundary.
            Defaults to config['grid'].get('filter_outside_state', False) for backward
            compatibility unless explicitly specified.

    Returns:
        DataFrame with columns: grid_id, grid_row, grid_col, lat_center, lon_center,
        lat_min, lat_max, lon_min, lon_max, state_status, state_coverage_pct.
    """
    cfg = config or load_config()
    root = get_project_root()
    res = cfg["grid"]["resolution_deg"]
    region = cfg["region"]

    if filter_outside is None:
        filter_outside = cfg.get("grid", {}).get("filter_outside_state", False)

    lat_edges = np.arange(region["lat_min"], region["lat_max"] + res, res)
    lon_edges = np.arange(region["lon_min"], region["lon_max"] + res, res)

    ibge_poly = _load_ibge_polygon(root)
    has_shapely = False
    try:
        from shapely.geometry import box
        has_shapely = True
    except ImportError:
        has_shapely = False

    rows: list[dict] = []
    for i in range(len(lat_edges) - 1):
        for j in range(len(lon_edges) - 1):
            lat_min = round(float(lat_edges[i]), 4)
            lat_max = round(float(lat_edges[i + 1]), 4)
            lon_min = round(float(lon_edges[j]), 4)
            lon_max = round(float(lon_edges[j + 1]), 4)
            lat_center = round((lat_min + lat_max) / 2.0, 4)
            lon_center = round((lon_min + lon_max) / 2.0, 4)

            # Territorial status
            state_status = "inside"
            coverage_pct = 1.0

            if ibge_poly is not None and has_shapely:
                cbox = box(lon_min, lat_min, lon_max, lat_max)
                if not ibge_poly.intersects(cbox):
                    state_status = "outside"
                    coverage_pct = 0.0
                else:
                    inter = ibge_poly.intersection(cbox)
                    pct = float(inter.area / cbox.area)
                    coverage_pct = round(pct, 4)
                    if pct >= 0.95:
                        state_status = "inside"
                    elif pct > 0.0:
                        state_status = "partial"
                    else:
                        state_status = "outside"

            rows.append({
                "grid_id": f"{i:03d}_{j:03d}",
                "grid_row": i,
                "grid_col": j,
                "lat_center": lat_center,
                "lon_center": lon_center,
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max,
                "state_status": state_status,
                "state_coverage_pct": coverage_pct,
            })

    grid_df = pd.DataFrame(rows)

    if filter_outside:
        grid_df = grid_df[grid_df["state_status"] != "outside"].reset_index(drop=True)

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
    print(f"Grid saved: {len(grid_df)} cells (status breakdown: {grid_df['state_status'].value_counts().to_dict()})")
    return grid_df


if __name__ == "__main__":
    print("Building geographic grid with IBGE masking...")
    grid = save_grid()
    print(f"Lat range: {grid['lat_min'].min():.2f} to {grid['lat_max'].max():.2f}")
    print(f"Lon range: {grid['lon_min'].min():.2f} to {grid['lon_max'].max():.2f}")
    print("Done!")
