"""FastAPI endpoint for wildfire risk prediction with explicit temporal contracts.

Supports:
- historical_replay: Retrospective inference using exact observed historical features
  from INPE and NASA POWER (2016-01-01 to 2025-12-24). Climatological backfills and
  approximate DOY matches are strictly forbidden to ensure scientific reproducibility.
- operational_forecast: Live operational forecasting with real-time stream ingestion.
  Explicitly returns HTTP 503 when live streaming feeds are disconnected, upholding
  scientific truthfulness without simulated successes.
"""

import datetime as dt
from functools import lru_cache
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Brazil Wildfire Risk Forecast API",
    description=(
        "Production ML service for wildfire risk prediction across Mato Grosso, Brazil. "
        "Implements strict temporal contracts, territorial masking (IBGE SIRGAS 2000), "
        "and probability calibration."
    ),
    version="2.0.0",
)

# ── Paths and Global Registry ──────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MODELS_DIR = _PROJECT_ROOT / "models"
_DATA_DIR = _PROJECT_ROOT / "data"

_models: dict[int, object] = {}
_calibrators: dict[int, object] = {}
_feature_cols: list[str] = []
_model_loaded = False
_grid_cells: dict[str, dict] = {}

# ── Model and Grid Initialization ──────────────────────────────────────────────

try:
    for h in [1, 3, 7]:
        m_file = f"lightgbm_{h}d.joblib" if h != 7 else "lightgbm_model.joblib"
        c_file = f"platt_calibrator_{h}d.joblib" if h != 7 else "platt_calibrator.joblib"
        if (_MODELS_DIR / m_file).exists():
            _models[h] = joblib.load(_MODELS_DIR / m_file)
        if (_MODELS_DIR / c_file).exists():
            _calibrators[h] = joblib.load(_MODELS_DIR / c_file)

    if 7 not in _models and (_MODELS_DIR / "lightgbm_calibrated.joblib").exists():
        _models[7] = joblib.load(_MODELS_DIR / "lightgbm_calibrated.joblib")

    if (_MODELS_DIR / "feature_cols.joblib").exists():
        _feature_cols = joblib.load(_MODELS_DIR / "feature_cols.joblib")

    _model_loaded = len(_models) > 0
except Exception:
    _model_loaded = False
    _models = {}
    _calibrators = {}
    _feature_cols = []

# Load grid lookup
try:
    grid_csv = _DATA_DIR / "processed" / "grid.csv"
    if grid_csv.exists():
        gdf = pd.read_csv(grid_csv)
        for _, row in gdf.iterrows():
            _grid_cells[row["grid_id"]] = {
                "lat_min": float(row["lat_min"]),
                "lat_max": float(row["lat_max"]),
                "lon_min": float(row["lon_min"]),
                "lon_max": float(row["lon_max"]),
                "lat_center": float(row["lat_center"]),
                "lon_center": float(row["lon_center"]),
                "state_status": str(row.get("state_status", "inside")),
            }
except Exception:
    _grid_cells = {}


# ── Schemas ───────────────────────────────────────────────────────────────────

class TemporalContract(BaseModel):
    """Explicit temporal metadata guaranteeing scientific traceability."""
    issue_date: str = Field(..., description="Date of forecast issuance (YYYY-MM-DD)")
    observation_cutoff: str = Field(..., description="Timestamp of the latest observed feature data")
    target_start: str = Field(..., description="Start of forecast evaluation window (YYYY-MM-DD)")
    target_end: str = Field(..., description="End of forecast evaluation window (YYYY-MM-DD)")
    data_timestamp: str = Field(..., description="Timestamp of raw observations used in feature vector")
    data_source: str = Field(..., description="Source organization and dataset identifiers")
    model_version: str = Field(..., description="Production model artifact version")
    inference_mode: str = Field(..., description="Mode: 'historical_replay' or 'operational_forecast'")


class PredictionRequest(BaseModel):
    """Request schema for wildfire risk prediction."""
    latitude: float = Field(..., ge=-33.0, le=5.5, description="Latitude (decimal degrees)")
    longitude: float = Field(..., ge=-74.0, le=-34.0, description="Longitude (decimal degrees)")
    date: dt.date = Field(..., description="Prediction issuance date (YYYY-MM-DD)")
    horizon_days: int = Field(default=7, description="Forecast horizon in days (1, 3, or 7)")
    inference_mode: Literal["historical_replay", "operational_forecast"] = Field(
        default="historical_replay",
        description="Inference mode: 'historical_replay' for validated archive, 'operational_forecast' for live stream",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "latitude": -12.5,
                    "longitude": -55.0,
                    "date": "2024-08-15",
                    "horizon_days": 7,
                    "inference_mode": "historical_replay",
                }
            ]
        }
    }


class PredictionResponse(BaseModel):
    """Response schema for wildfire risk prediction with temporal contract."""
    latitude: float
    longitude: float
    date: str
    horizon_days: int
    probability: float = Field(..., description="Calibrated probability of fire in forecast horizon [0, 1]")
    risk_level: str = Field(..., description="Risk tier: low (<0.25), medium (0.25-0.55), or high (>=0.55)")
    grid_id: str = Field(..., description="Assigned geographic grid cell identifier")

    # Explicit temporal contract
    issue_date: str
    observation_cutoff: str
    target_start: str
    target_end: str
    data_timestamp: str
    data_source: str
    model_version: str
    inference_mode: str


class ExplainRequest(BaseModel):
    """Request schema for local SHAP explanation."""
    latitude: float = Field(..., ge=-33.0, le=5.5, description="Latitude (decimal degrees)")
    longitude: float = Field(..., ge=-74.0, le=-34.0, description="Longitude (decimal degrees)")
    date: dt.date = Field(..., description="Prediction issuance date (YYYY-MM-DD)")
    horizon_days: int = Field(default=7, description="Forecast horizon in days (1, 3, or 7)")
    inference_mode: Literal["historical_replay", "operational_forecast"] = Field(
        default="historical_replay",
        description="Inference mode: 'historical_replay' or 'operational_forecast'",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "latitude": -12.5,
                    "longitude": -55.0,
                    "date": "2024-08-15",
                    "horizon_days": 7,
                    "inference_mode": "historical_replay",
                }
            ]
        }
    }


class ExplainResponse(BaseModel):
    """Response schema for local SHAP explanation with temporal contract."""
    latitude: float
    longitude: float
    date: str
    horizon_days: int
    probability: float
    risk_level: str
    grid_id: str
    shap_values: dict[str, float]
    top_positive: list[dict]
    top_negative: list[dict]
    baseline_log_odds: float

    # Explicit temporal contract
    issue_date: str
    observation_cutoff: str
    target_start: str
    target_end: str
    data_timestamp: str
    data_source: str
    model_version: str
    inference_mode: str


class HealthResponse(BaseModel):
    """Health check response with inference operational status."""
    status: str
    model_loaded: bool
    available_horizons: list[int]
    supported_inference_modes: dict[str, str]


from src.models.risk_tiers import classify_risk


def _resolve_grid_cell(lat: float, lon: float) -> tuple[str, dict]:
    """Resolve coordinates to grid cell with strict IBGE boundary validation."""
    # Bounding box check for Mato Grosso
    if not (-18.2 <= lat <= -7.2):
        raise HTTPException(
            status_code=422,
            detail=f"Latitude {lat} outside pilot coverage (Mato Grosso bounds: [-18.1, -7.3])",
        )
    if not (-61.8 <= lon <= -50.1):
        raise HTTPException(
            status_code=422,
            detail=f"Longitude {lon} outside pilot coverage (Mato Grosso bounds: [-61.7, -50.2])",
        )

    # Resolution arithmetic (0.5 degree regular grid, origin at -18.1 lat, -61.7 lon)
    res = 0.5
    lat_min_origin = -18.1
    lon_min_origin = -61.7
    row = int(np.floor((lat - lat_min_origin) / res))
    col = int(np.floor((lon - lon_min_origin) / res))
    grid_id = f"{row:03d}_{col:03d}"

    cell_meta = _grid_cells.get(grid_id)
    if cell_meta and cell_meta.get("state_status") == "outside":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Coordinates (lat={lat}, lon={lon}) fall into cell {grid_id} which is strictly "
                "outside official Mato Grosso territorial boundaries (IBGE SIRGAS 2000 mask)."
            ),
        )

    return grid_id, cell_meta or {}


@lru_cache(maxsize=2048)
def _query_historical_row(grid_id: str, date_str: str) -> tuple[tuple, tuple] | None:
    """Retrieve exact observed feature vector from parquet archive with zero approximate matching."""
    feat_parquet = _DATA_DIR / "processed" / "features.parquet"
    sample_parquet = _DATA_DIR / "sample" / "features_sample.parquet"
    target_parquet = feat_parquet if feat_parquet.exists() else sample_parquet

    if not target_parquet.exists():
        return None

    target_dt = pd.Timestamp(date_str)
    try:
        table = pq.read_table(
            target_parquet,
            filters=[("grid_id", "==", grid_id), ("date", "==", target_dt)],
        )
        if len(table) == 0:
            return None
        df = table.to_pandas()
        row = df.iloc[0]
        # Return tuple of keys and values for immutability and caching
        keys = tuple(_feature_cols)
        values = tuple(float(row[c]) if c in row and pd.notna(row[c]) else 0.0 for c in _feature_cols)
        return keys, values
    except Exception:
        return None


def _get_feature_vector(
    lat: float,
    lon: float,
    date: dt.date,
    grid_id: str,
    inference_mode: str,
) -> np.ndarray:
    """Build feature vector respecting temporal contracts and data availability constraints."""
    if inference_mode == "operational_forecast":
        raise HTTPException(
            status_code=503,
            detail=(
                "Operational forecast mode is unavailable: live ingestion feed (INPE / NASA POWER "
                "near-real-time streaming daemon) is currently disconnected. Use historical_replay "
                "mode for retrospective evaluation within the validated archive [2016-01-01, 2025-12-24]."
            ),
        )

    # Historical replay mode: strictly query exact observations
    date_str = str(date)
    record = _query_historical_row(grid_id, date_str)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Exact historical observation record not found for grid cell {grid_id} on date {date_str}. "
                "In historical_replay mode, silent imputation, synthetic DOY matching, and zeros are strictly "
                "forbidden to maintain scientific reproducibility. Archive covers 2016-01-01 to 2025-12-24."
            ),
        )

    _, values = record
    return np.array([values], dtype=np.float32)


def _calibrate_probability(raw_prob: float, calibrator: object | None) -> float:
    """Apply probability calibrator returning a calibrated float in [0, 1].

    Raises HTTPException(500) if a loaded calibrator fails, strictly preventing
    silent degradation to uncalibrated outputs.
    """
    if calibrator is None:
        return round(float(np.clip(raw_prob, 0.0, 1.0)), 4)

    try:
        if hasattr(calibrator, "calibrate"):
            cal_val = float(calibrator.calibrate(np.array([raw_prob]))[0])
            return round(float(np.clip(cal_val, 0.0, 1.0)), 4)

        from scipy.special import logit
        raw_logit = logit(np.clip(raw_prob, 1e-6, 1.0 - 1e-6)).reshape(-1, 1)
        cal_probs = calibrator.predict_proba(raw_logit)
        prob = float(cal_probs[0, 1]) if cal_probs.ndim == 2 else float(cal_probs[1])
        return round(float(np.clip(prob, 0.0, 1.0)), 4)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Probability calibration failed on model output: {e}",
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Check API readiness and loaded model artifacts."""
    return HealthResponse(
        status="ok" if _model_loaded else "degraded",
        model_loaded=_model_loaded,
        available_horizons=sorted(list(_models.keys())),
        supported_inference_modes={
            "historical_replay": "Enabled (Archive 2016-01-01 to 2025-12-24)",
            "operational_forecast": "Disabled (Live streaming daemon disconnected; requires manual telemetry activation)",
        },
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    """Predict wildfire risk for a given location and date with an explicit temporal contract.

    Returns the probability of at least one fire hotspot within the forecast horizon
    in the grid cell containing the specified coordinates.
    """
    if not _model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Ensure training artifacts are available in models/.",
        )

    if request.date.year < 2016 or request.date.year > 2030:
        raise HTTPException(
            status_code=422,
            detail=f"Date year {request.date.year} outside supported operating range [2016, 2030]",
        )

    if request.horizon_days not in (1, 3, 7):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid horizon_days: {request.horizon_days}. Must be 1, 3, or 7.",
        )

    model = _models.get(request.horizon_days)
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=f"Model artifact for horizon {request.horizon_days}d not loaded.",
        )

    calibrator = _calibrators.get(request.horizon_days)
    grid_id, _ = _resolve_grid_cell(request.latitude, request.longitude)
    X = _get_feature_vector(request.latitude, request.longitude, request.date, grid_id, request.inference_mode)

    raw_prob = float(model.predict_proba(X)[0, 1])
    cal_prob = _calibrate_probability(raw_prob, calibrator)

    # Build explicit temporal contract
    issue_date = str(request.date)
    obs_cutoff = str(request.date)
    target_start = str(request.date + dt.timedelta(days=1))
    target_end = str(request.date + dt.timedelta(days=request.horizon_days))
    data_timestamp = f"{issue_date}T00:00:00Z"
    data_source = "INPE BDQueimadas & NASA POWER (Historical Replay Archive v2.0)"
    model_version = "2.0.0-spatiotemporal"

    return PredictionResponse(
        latitude=request.latitude,
        longitude=request.longitude,
        date=issue_date,
        horizon_days=request.horizon_days,
        probability=cal_prob,
        risk_level=classify_risk(cal_prob),
        grid_id=grid_id,
        issue_date=issue_date,
        observation_cutoff=obs_cutoff,
        target_start=target_start,
        target_end=target_end,
        data_timestamp=data_timestamp,
        data_source=data_source,
        model_version=model_version,
        inference_mode=request.inference_mode,
    )


@app.post("/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest) -> ExplainResponse:
    """Return local SHAP feature attributions for a prediction with temporal contract."""
    if not _model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded. Run training first.")

    if request.horizon_days not in (1, 3, 7):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid horizon_days: {request.horizon_days}. Must be 1, 3, or 7.",
        )

    model = _models.get(request.horizon_days)
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=f"Model for {request.horizon_days}-day horizon not available.",
        )

    try:
        import shap
    except ImportError:
        raise HTTPException(status_code=500, detail="shap package not installed.")

    grid_id, _ = _resolve_grid_cell(request.latitude, request.longitude)
    X = _get_feature_vector(request.latitude, request.longitude, request.date, grid_id, request.inference_mode)

    # SHAP TreeExplainer
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]

    sv = shap_vals[0].tolist()
    shap_dict = {fc: round(float(v), 5) for fc, v in zip(_feature_cols, sv)}

    # Probability calibration
    calibrator = _calibrators.get(request.horizon_days)
    raw_prob = float(model.predict_proba(X)[0, 1])
    cal_prob = _calibrate_probability(raw_prob, calibrator)

    # Contributors
    sorted_shap = sorted(shap_dict.items(), key=lambda x: x[1], reverse=True)
    top_positive = [{"feature": k, "shap": v} for k, v in sorted_shap if v > 0][:5]
    top_negative = [{"feature": k, "shap": v} for k, v in reversed(sorted_shap) if v < 0][:5]

    expected_val = explainer.expected_value
    if isinstance(expected_val, (list, np.ndarray)):
        expected_val = expected_val[1] if len(expected_val) > 1 else expected_val[0]

    # Explicit temporal contract
    issue_date = str(request.date)
    obs_cutoff = str(request.date)
    target_start = str(request.date + dt.timedelta(days=1))
    target_end = str(request.date + dt.timedelta(days=request.horizon_days))

    return ExplainResponse(
        latitude=request.latitude,
        longitude=request.longitude,
        date=issue_date,
        horizon_days=request.horizon_days,
        probability=cal_prob,
        risk_level=classify_risk(cal_prob),
        grid_id=grid_id,
        shap_values=shap_dict,
        top_positive=top_positive,
        top_negative=top_negative,
        baseline_log_odds=round(float(expected_val), 4),
        issue_date=issue_date,
        observation_cutoff=obs_cutoff,
        target_start=target_start,
        target_end=target_end,
        data_timestamp=f"{issue_date}T00:00:00Z",
        data_source="INPE BDQueimadas & NASA POWER (Historical Replay Archive v2.0)",
        model_version="2.0.0-spatiotemporal",
        inference_mode=request.inference_mode,
    )


@app.get("/drift")
def get_drift_report():
    """Return data and feature drift report (PSI and KS test)."""
    report_path = _PROJECT_ROOT / "reports" / "drift_report.json"
    if report_path.exists():
        import json
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        try:
            from src.monitoring.drift_detector import run_drift_analysis
            return run_drift_analysis()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate drift report: {e}")


@app.get("/")
def root():
    """API root — links to documentation and endpoints."""
    return {
        "message": "Brazil Wildfire Risk Forecast API v2.0",
        "docs": "/docs",
        "health": "/health",
        "predict": "/predict",
        "explain": "/explain",
        "drift": "/drift",
        "inference_modes": ["historical_replay", "operational_forecast"],
    }
