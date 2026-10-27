"""Isolated model/data load timings, optionally exercising the minimal dashboard."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard-check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    started = time.perf_counter()
    import joblib
    import pandas as pd
    imports = time.perf_counter() - started
    started = time.perf_counter()
    models, calibrators = {}, {}
    columns = joblib.load(root / "models/feature_cols.joblib")
    for h in (1, 3, 7):
        models[h] = joblib.load(root / "models" / (f"lightgbm_{h}d.joblib" if h != 7 else "lightgbm_model.joblib"))
        calibrators[h] = joblib.load(root / "models" / (f"platt_calibrator_{h}d.joblib" if h != 7 else "platt_calibrator.joblib"))
        assert getattr(calibrators[h], "is_fitted_", False)
    load = time.perf_counter() - started
    sample = root / "data/sample/features_sample.parquet"
    started = time.perf_counter()
    frame = pd.read_parquet(sample)
    read = time.perf_counter() - started
    result = {"initial_joblib_pandas_import_seconds": imports, "model_pair_and_schema_load_seconds": load,
              "sample_read_seconds": read, "sample_rows": len(frame), "sample_cells": frame.grid_id.nunique(),
              "sample_dates": frame.date.nunique(), "sample_sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
              "feature_count": len(columns), "available_horizons": sorted(models),
              "libraries": {name: importlib.metadata.version(name) for name in ["numpy", "pandas", "pyarrow", "scikit-learn", "lightgbm", "streamlit"]}}
    if args.dashboard_check:
        from streamlit.testing.v1 import AppTest
        os.environ["WILDFIRE_USE_SAMPLE"] = "1"
        checks = []
        for language in ["pt-BR", "en"]:
            app = AppTest.from_file(str(root / "app/streamlit_app.py"), default_timeout=60)
            app.session_state["language"] = language
            app.run()
            assert not app.exception and not app.error and len(app.tabs) == 5
            checks.append({"language": language, "tabs": 5, "exceptions": 0, "errors": 0})
        result["dashboard_checks"] = checks
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
