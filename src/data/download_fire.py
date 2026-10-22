"""Download fire hotspot data from INPE's open data server.

Downloads annual CSV files for the reference satellite (AQUA_M-T) and filters
by the configured state. Files are saved to data/raw/fire/.

The reference satellite is used because INPE designates AQUA (MODIS sensor,
afternoon pass) as the standard for long-term comparisons. Other satellites
detect more hotspots but change over time, breaking temporal consistency.
"""

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

from src.config import get_project_root, load_config


def download_fire_data(config: dict | None = None) -> Path:
    """Download and filter INPE fire hotspot CSVs.

    Args:
        config: Optional config dict. Loaded from config.yaml if not provided.

    Returns:
        Path to the directory containing the downloaded CSV files.
    """
    cfg = config or load_config()
    root = get_project_root()
    out_dir = root / "data" / "raw" / "fire"
    out_dir.mkdir(parents=True, exist_ok=True)

    base_url = cfg["data"]["fire_base_url"]
    state_code = cfg["region"]["state_code"]
    state_name = cfg["region"].get("state_name", cfg["region"]["name"]).upper()
    start_year = cfg["data"]["start_year"]
    end_year = cfg["data"]["end_year"]

    all_frames: list[pd.DataFrame] = []

    for year in range(start_year, end_year + 1):
        out_file = out_dir / f"focos_{state_code}_{year}.csv"
        if out_file.exists():
            print(f"  [skip] {out_file.name} already exists")
            df = pd.read_csv(out_file)
            all_frames.append(df)
            continue

        # INPE naming convention: focos_br_ref_YYYY.zip
        url = f"{base_url}/focos_br_ref_{year}.zip"
        print(f"  [download] {url}")

        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            # Try alternative naming patterns
            alt_urls = [
                f"{base_url}/focos_abertos_ref_{year}.zip",
                f"{base_url}/Brasil_sat_ref_{year}.zip",
            ]
            downloaded = False
            for alt_url in alt_urls:
                try:
                    print(f"  [retry] {alt_url}")
                    resp = requests.get(alt_url, timeout=120)
                    resp.raise_for_status()
                    downloaded = True
                    break
                except requests.exceptions.HTTPError:
                    continue
            if not downloaded:
                print(f"  [warn] Could not download {year}. Skipping.")
                continue

        # Extract CSV from zip
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
            if not csv_names:
                print(f"  [warn] No CSV found in zip for {year}")
                continue
            with zf.open(csv_names[0]) as csv_file:
                df = pd.read_csv(csv_file, encoding="latin-1")

        # Standardize column names (INPE uses Portuguese)
        col_map = _detect_columns(df)
        df = df.rename(columns=col_map)

        # Filter by state (INPE uses full uppercase state names, e.g. "MATO GROSSO")
        if "estado" in df.columns:
            df = df[df["estado"].str.upper().str.strip() == state_name].copy()
            # Exclude "MATO GROSSO DO SUL" when filtering for "MATO GROSSO"
            if state_name == "MATO GROSSO":
                df = df[df["estado"].str.upper().str.strip() == "MATO GROSSO"].copy()
        elif "state" in df.columns:
            df = df[df["state"].str.upper().str.strip() == state_name].copy()

        # Enforce reference satellite filtering if multiple sensors present
        if "satelite" in df.columns:
            ref_mask = df["satelite"].astype(str).str.upper().str.contains("AQUA|REF")
            if ref_mask.any():
                df = df[ref_mask].copy()

        # Deduplicate identical transmission packets
        dedup_keys = [c for c in ["lat", "lon", "data_hora_gmt"] if c in df.columns]
        if dedup_keys:
            df = df.drop_duplicates(subset=dedup_keys).copy()

        df.to_csv(out_file, index=False)
        all_frames.append(df)
        print(f"  [saved] {out_file.name} — {len(df):,} hotspots")

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        combined_path = out_dir / f"focos_{state_code}_all.csv"
        combined.to_csv(combined_path, index=False)
        print(f"\n  [combined] {combined_path.name} — {len(combined):,} total hotspots")

    return out_dir


def _detect_columns(df: pd.DataFrame) -> dict[str, str]:
    """Map common INPE column name variants to a standard set.

    Returns:
        Dictionary mapping original column names to standardized ones.
    """
    mapping: dict[str, str] = {}
    lower_cols = {c.lower().strip(): c for c in df.columns}

    standard = {
        "lat": ["lat", "latitude"],
        "lon": ["lon", "lng", "longitude"],
        "data_hora_gmt": ["data_hora_gmt", "datahora", "data_hora", "data_pas"],
        "satelite": ["satelite", "satellite"],
        "estado": ["estado", "state"],
        "municipio": ["municipio", "municipality", "county"],
        "bioma": ["bioma", "biome"],
        "frp": ["frp", "fire_radiative_power"],
    }

    for target, variants in standard.items():
        for v in variants:
            if v in lower_cols:
                mapping[lower_cols[v]] = target
                break

    return mapping


if __name__ == "__main__":
    print("=" * 60)
    print("Downloading INPE fire hotspot data (reference satellite)")
    print("=" * 60)
    cfg = load_config()
    print(f"Region: {cfg['region']['name']} ({cfg['region']['state_code']})")
    print(f"Period: {cfg['data']['start_year']}-{cfg['data']['end_year']}")
    print(f"Satellite: {cfg['data']['satellite']}")
    print()
    download_fire_data(cfg)
    print("\nDone!")
