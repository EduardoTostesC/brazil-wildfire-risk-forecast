"""Download daily climate data from NASA POWER API for each grid cell center.

NASA POWER provides gridded reanalysis data (MERRA-2) at ~0.5° resolution.
We query it for each cell centroid. Variables:
  - T2M_MAX: max daily temperature at 2m (°C)
  - T2M_MIN: min daily temperature at 2m (°C)
  - RH2M: relative humidity at 2m (%)
  - PRECTOTCORR: corrected precipitation (mm/day)
  - WS10M: wind speed at 10m (m/s)

The API is free, requires no token, and has generous rate limits.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

from src.config import get_project_root, load_config
from src.data.build_grid import build_grid
from src.data.quality import climate_quality


def _fetch_one_cell(
    lat: float,
    lon: float,
    grid_id: str,
    params_str: str,
    start_date: str,
    end_date: str,
    base_url: str,
    max_retries: int = 3,
) -> pd.DataFrame | None:
    """Fetch daily climate data for a single grid cell from NASA POWER.

    Args:
        lat: Cell center latitude.
        lon: Cell center longitude.
        grid_id: Cell identifier.
        params_str: Comma-separated parameter names.
        start_date: Start date as YYYYMMDD.
        end_date: End date as YYYYMMDD.
        base_url: NASA POWER API base URL.
        max_retries: Number of retries on failure.

    Returns:
        DataFrame with daily climate data, or None on failure.
    """
    url_params = {
        "parameters": params_str,
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_date,
        "end": end_date,
        "format": "JSON",
        "time-standard": "LST",  # Explicitly preserves the legacy POWER day definition.
    }

    for attempt in range(max_retries):
        try:
            resp = requests.get(base_url, params=url_params, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            # Parse the parameters dict into a DataFrame
            param_data = data["properties"]["parameter"]
            df = pd.DataFrame(param_data)
            df.index.name = "date"
            df = df.reset_index()
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
            df["grid_id"] = grid_id

            # Remove fill values (-999)
            for col in df.columns:
                if col not in ("date", "grid_id"):
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    df.loc[df[col] < -900, col] = None

            check = climate_quality(df, pd.Timestamp(start_date), pd.Timestamp(end_date), grid_id)
            if not check["valid"]:
                raise ValueError(f"Incomplete or invalid daily series: {check}")
            return df

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [error] Cell {grid_id} ({lat}, {lon}): {e}")
                return None


def download_climate_data(config: dict | None = None) -> Path:
    """Download NASA POWER climate data for all grid cells.

    Checks for existing files and only downloads missing cells.
    Uses ThreadPoolExecutor for parallel downloads.

    Args:
        config: Optional config dict.

    Returns:
        Path to the output directory.
    """
    cfg = config or load_config()
    root = get_project_root()
    out_dir = root / "data" / "raw" / "climate"
    out_dir.mkdir(parents=True, exist_ok=True)

    grid_df = build_grid(cfg)
    base_url = cfg["data"]["power_base_url"]
    params_str = ",".join(cfg["data"]["power_params"])
    start_date = f"{cfg['data']['start_year']}0101"
    end_date = f"{cfg['data']['end_year']}1231"

    total_cells = len(grid_df)
    print(f"  Total grid cells: {total_cells}")

    # Check which cells already have data
    existing = set()
    for f in out_dir.glob("climate_*.csv"):
        gid = f.stem.replace("climate_", "")
        try:
            check = climate_quality(pd.read_csv(f), f"{cfg['data']['start_year']}-01-01",
                                    f"{cfg['data']['end_year']}-12-31", gid)
            if check["valid"]:
                existing.add(gid)
        except (OSError, ValueError):
            pass  # Invalid cache is downloaded again, not accepted as complete.

    to_download = grid_df[~grid_df["grid_id"].isin(existing)]
    print(f"  Already downloaded: {len(existing)}")
    print(f"  To download: {len(to_download)}")

    if len(to_download) == 0:
        print("  All cells already downloaded!")
        return out_dir

    # Download in parallel (limit to 5 concurrent to be polite to NASA API)
    completed = 0
    failed = 0

    def _download_and_save(row: pd.Series) -> bool:
        df = _fetch_one_cell(
            lat=row["lat_center"],
            lon=row["lon_center"],
            grid_id=row["grid_id"],
            params_str=params_str,
            start_date=start_date,
            end_date=end_date,
            base_url=base_url,
        )
        if df is not None:
            df.to_csv(out_dir / f"climate_{row['grid_id']}.csv", index=False)
            return True
        return False

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_download_and_save, row): row["grid_id"]
            for _, row in to_download.iterrows()
        }
        for future in as_completed(futures):
            gid = futures[future]
            try:
                success = future.result()
                if success:
                    completed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            total_done = completed + failed
            if total_done % 10 == 0 or total_done == len(to_download):
                print(f"  Progress: {total_done}/{len(to_download)} "
                      f"(ok={completed}, fail={failed})")

    print(f"\n  Climate download complete: {completed} ok, {failed} failed")
    if failed:
        raise RuntimeError(f"Climate acquisition incomplete: {failed} cells failed")
    return out_dir


if __name__ == "__main__":
    print("=" * 60)
    print("Downloading NASA POWER climate data")
    print("=" * 60)
    cfg = load_config()
    print(f"Region: {cfg['region']['name']}")
    print(f"Period: {cfg['data']['start_year']}-{cfg['data']['end_year']}")
    print(f"Parameters: {', '.join(cfg['data']['power_params'])}")
    print()
    download_climate_data(cfg)
    print("\nDone!")

