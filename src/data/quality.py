"""Source quality checks; successful HTTP responses are not completeness checks."""

import numpy as np
import pandas as pd

CLIMATE_LIMITS = {"T2M_MAX": (-50, 65), "T2M_MIN": (-60, 60), "RH2M": (0, 100),
                  "PRECTOTCORR": (0, 2000), "WS10M": (0, 100)}


def climate_quality(df: pd.DataFrame, start, end, grid_id: str | None = None) -> dict:
    required = {"date", "grid_id", *CLIMATE_LIMITS}
    missing_columns = sorted(required - set(df.columns))
    if missing_columns:
        return {"valid": False, "missing_columns": missing_columns}
    dates = pd.to_datetime(df.date, errors="coerce")
    expected = pd.date_range(start, end, freq="D")
    issues = {"invalid_dates": int(dates.isna().sum()), "duplicate_days": int(dates.duplicated().sum()),
              "missing_days": int(len(expected.difference(dates))),
              "unexpected_days": int(len(pd.DatetimeIndex(dates.dropna()).difference(expected))),
              "wrong_grid": int((df.grid_id != grid_id).sum()) if grid_id else int(df.grid_id.nunique() != 1)}
    missing, invalid = {}, {}
    for column, (low, high) in CLIMATE_LIMITS.items():
        values = pd.to_numeric(df[column], errors="coerce")
        missing[column] = int(values.isna().sum())
        invalid[column] = int((~np.isfinite(values) | (values < low) | (values > high)).sum())
    issues["inverted_temperature"] = int((df.T2M_MAX < df.T2M_MIN).sum())
    return {"valid": not any(issues.values()) and not any(missing.values()) and not any(invalid.values()),
            "rows": len(df), "expected_days": len(expected), "date_min": str(dates.min()),
            "date_max": str(dates.max()), "issues": issues, "missing": missing, "invalid": invalid}


def fire_quality(df: pd.DataFrame, year: int | None = None, satellite: str = "AQUA_M-T") -> dict:
    required = {"lat", "lon", "data_hora_gmt", "estado"}
    missing_columns = sorted(required - set(df.columns))
    if missing_columns:
        return {"valid": False, "missing_columns": missing_columns}
    dates = pd.to_datetime(df.data_hora_gmt, errors="coerce", utc=True)
    issues = {"invalid_dates": int(dates.isna().sum()),
              "invalid_coordinates": int((~np.isfinite(df.lat) | ~np.isfinite(df.lon) | ~df.lat.between(-90, 90) | ~df.lon.between(-180, 180)).sum()),
              "wrong_satellite": int((df.satelite.astype(str).str.upper().str.strip() != satellite.upper()).sum()) if "satelite" in df else 0,
              "wrong_state": int((df.estado.astype(str).str.upper().str.strip() != "MATO GROSSO").sum()),
              "wrong_year": int((dates.dt.year != year).sum()) if year else 0,
              "duplicates": int(df.duplicated(["lat", "lon", "data_hora_gmt"]).sum())}
    return {"valid": len(df) > 0 and not any(issues.values()), "rows": len(df), "issues": issues,
            "satellite_verification": "row_column" if "satelite" in df else "reference_product_URL_only; no per-row satellite column",
            "date_min": str(dates.min()), "date_max": str(dates.max()),
            "detected_days": int(dates.dt.normalize().nunique()),
            "coverage_note": "Detection dates cannot establish full sensor coverage or prove physical absence of fire."}
