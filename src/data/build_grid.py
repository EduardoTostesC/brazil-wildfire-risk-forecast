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
from pyproj import Geod
from shapely.geometry import box, shape

from src.config import get_project_root, load_config


def _load_ibge_polygon(root: Path):
    """Load the required versioned boundary; never silently omit the mask."""
    geo_path = root / "data" / "geo" / "mato_grosso_ibge.geojson"
    if not geo_path.exists():
        raise FileNotFoundError(f"Required territorial boundary missing: {geo_path}")
    try:
        with open(geo_path, "r", encoding="utf-8") as f:
            geojson = json.load(f)
        polygon = shape(geojson["features"][0]["geometry"])
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid territorial GeoJSON: {geo_path}") from exc
    if polygon.is_empty or not polygon.is_valid or polygon.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Territorial boundary must be a valid nonempty polygon")
    return polygon


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
    geod = Geod(ellps="GRS80")

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
            cell_area_km2 = 0.0
            state_area_km2 = 0.0

            if ibge_poly is not None:
                cbox = box(lon_min, lat_min, lon_max, lat_max)
                cell_area_km2 = abs(geod.geometry_area_perimeter(cbox)[0]) / 1e6
                if not ibge_poly.intersects(cbox):
                    state_status = "outside"
                    coverage_pct = 0.0
                else:
                    inter = ibge_poly.intersection(cbox)
                    if inter.geom_type in {"Polygon", "MultiPolygon"}:
                        state_area_km2 = abs(geod.geometry_area_perimeter(inter)[0]) / 1e6
                    # Geographic fraction is retained for historical comparability.
                    # It is a dimensionless fraction in degree area, not km².
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
                "cell_area_km2": cell_area_km2,
                "state_area_km2": state_area_km2,
                "state_fraction_geodesic": state_area_km2 / cell_area_km2 if cell_area_km2 else 0.0,
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

    # Snap only floating-point arithmetic at exact regular-grid lines.
    lat_index = np.round((lat - region["lat_min"]) / res, 10)
    lon_index = np.round((lon - region["lon_min"]) / res, 10)
    grid_row = np.floor(lat_index).astype(int)
    grid_col = np.floor(lon_index).astype(int)

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
