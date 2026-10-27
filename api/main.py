"""Retrospective hotspot risk API. Live forecasting is not implemented."""

import datetime as dt
import hashlib
import json
import logging
import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from shapely.geometry import Point

from src.data.build_grid import _load_ibge_polygon, assign_to_grid, build_grid
from src.models.inference import calibrated_probabilities, feature_matrix
from src.models.risk_tiers import classify_risk

logger = logging.getLogger(__name__)
app = FastAPI(title="Brazil Wildfire Risk Forecast API", version="2.1.0",
              description="Historical replay of satellite hotspot detection risk in Mato Grosso.")
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MODELS_DIR = _PROJECT_ROOT / "models"
_DATA_DIR = _PROJECT_ROOT / "data"
_models: dict[int, object] = {}
_calibrators: dict[int, object] = {}
_model_versions: dict[int, str] = {}
_feature_cols: list[str] = []
_grid_cells: dict[str, dict] = {}
_polygon = None

for _h in (1, 3, 7):
    _mp = _MODELS_DIR / (f"lightgbm_{_h}d.joblib" if _h != 7 else "lightgbm_model.joblib")
    _cp = _MODELS_DIR / (f"platt_calibrator_{_h}d.joblib" if _h != 7 else "platt_calibrator.joblib")
    try:
        _models[_h] = joblib.load(_mp)
        _calibrators[_h] = joblib.load(_cp)
        _model_versions[_h] = "sha256:" + hashlib.sha256(_mp.read_bytes() + _cp.read_bytes()).hexdigest()
    except (OSError, ValueError, TypeError, ImportError, AttributeError, EOFError, pickle.UnpicklingError):
        logger.exception("Unable to load artifact pair for horizon %s", _h)
        _models.pop(_h, None)
        _calibrators.pop(_h, None)
try:
    _feature_cols = joblib.load(_MODELS_DIR / "feature_cols.joblib")
    _polygon = _load_ibge_polygon(_PROJECT_ROOT)
    _grid = build_grid()
    _grid_cells = _grid.set_index("grid_id").to_dict("index")
except (OSError, ValueError, TypeError, ImportError, AttributeError):
    logger.exception("Unable to initialize feature or geographic registry")
_model_loaded = bool(_models and _feature_cols)


class PredictionRequest(BaseModel):
    latitude: float = Field(..., ge=-33.0, le=5.5, allow_inf_nan=False)
    longitude: float = Field(..., ge=-74.0, le=-34.0, allow_inf_nan=False)
    date: dt.date
    horizon_days: int = 7
    inference_mode: Literal["historical_replay", "operational_forecast"] = "historical_replay"


class PredictionResponse(BaseModel):
    latitude: float
    longitude: float
    date: str
    horizon_days: int
    probability: float = Field(..., ge=0, le=1, description="Calibrated probability of >=1 reference-sensor hotspot in the cell/window")
    risk_level: str
    grid_id: str
    issue_date: str
    observation_cutoff: str
    target_start: str
    target_end: str
    data_timestamp: str | None = Field(default=None, description="Historical source availability is unknown")
    availability_timestamp: str | None = None
    processed_at: str
    data_source: str
    archive_scope: str
    model_version: str
    inference_mode: str


ExplainRequest = PredictionRequest


class ExplainResponse(PredictionResponse):
    shap_values: dict[str, float]
    top_positive: list[dict]
    top_negative: list[dict]
    baseline_log_odds: float
    raw_log_odds: float
    explanation_scale: str = "raw_model_log_odds_before_calibration"


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    available_horizons: list[int]
    supported_inference_modes: dict[str, str]


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error("Unexpected inference failure at %s", request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal inference error; consult server logs."})


def _resolve_grid_cell(lat: float, lon: float) -> tuple[str, dict]:
    if not (-18.1 <= lat <= -7.1 and -61.7 <= lon <= -50.2):
        raise HTTPException(422, "Coordinates outside pilot coverage (Mato Grosso)")
    if _polygon is None or not _grid_cells:
        raise HTTPException(503, "Official territorial validation unavailable")
    if not _polygon.covers(Point(lon, lat)):
        raise HTTPException(422, "Point outside official Mato Grosso territory")
    row, col = assign_to_grid(lat, lon)
    grid_id = f"{int(row):03d}_{int(col):03d}"
    cell = _grid_cells.get(grid_id)
    if cell is None or cell.get("state_status") == "outside":
        raise HTTPException(422, "Point has no covered grid cell")
    return grid_id, cell


def _archive_path() -> Path:
    full = _DATA_DIR / "processed/features.parquet"
    return full if full.exists() and os.environ.get("WILDFIRE_USE_SAMPLE") != "1" else _DATA_DIR / "sample/features_sample.parquet"


@lru_cache(maxsize=2048)
def _query_historical_row(grid_id: str, date_str: str, archive_key: tuple | None = None):
    """Exact lookup; IO/schema failure is distinct from an absent record."""
    path = _archive_path()
    if not path.exists():
        raise HTTPException(503, "Historical feature archive unavailable")
    try:
        table = pq.read_table(path, filters=[("grid_id", "==", grid_id), ("date", "==", pd.Timestamp(date_str))])
        if len(table) == 0:
            return None
        if len(table) != 1:
            raise ValueError("Duplicate cell/date records in historical archive")
        values = feature_matrix(table.to_pandas(), _feature_cols)[0]
        return tuple(_feature_cols), tuple(values)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        logger.exception("Cannot read historical archive %s", path)
        raise HTTPException(503, "Historical feature archive unreadable or invalid") from exc


def _get_feature_vector(lat, lon, date, grid_id, inference_mode):
    if inference_mode == "operational_forecast":
        raise HTTPException(503, "Operational forecast mode is unavailable: live acquisition and historical publication-time validation are not implemented.")
    path = _archive_path()
    key = (str(path), path.stat().st_mtime_ns, path.stat().st_size, tuple(_feature_cols)) if path.exists() else None
    record = _query_historical_row(grid_id, str(date), key)
    if record is None:
        raise HTTPException(404, f"Exact historical record not found: {grid_id} on {date}")
    return np.asarray([record[1]], dtype=np.float32)


def _prepare(request):
    if request.horizon_days not in (1, 3, 7):
        raise HTTPException(422, "Invalid horizon_days: must be 1, 3, or 7")
    if request.date.year < 2016 or request.date.year > 2030:
        raise HTTPException(422, "Date outside supported query range [2016, 2030]")
    if (not _model_loaded or request.horizon_days not in _models or request.horizon_days not in _calibrators
            or not getattr(_calibrators.get(request.horizon_days), "is_fitted_", False)):
        raise HTTPException(503, "Required model/calibrator pair unavailable for requested horizon")
    grid_id, _ = _resolve_grid_cell(request.latitude, request.longitude)
    values = _get_feature_vector(request.latitude, request.longitude, request.date, grid_id, request.inference_mode)
    model, calibrator = _models[request.horizon_days], _calibrators[request.horizon_days]
    probability = float(calibrated_probabilities(model, calibrator, values)[0])
    return model, values, dict(
        latitude=request.latitude, longitude=request.longitude, date=str(request.date),
        horizon_days=request.horizon_days, probability=probability, risk_level=classify_risk(probability),
        grid_id=grid_id, issue_date=str(request.date), observation_cutoff=str(request.date),
        target_start=str(request.date + dt.timedelta(days=1)),
        target_end=str(request.date + dt.timedelta(days=request.horizon_days)),
        data_timestamp=None, availability_timestamp=None, processed_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        data_source="INPE BDQueimadas + NASA POWER; " + _archive_path().relative_to(_DATA_DIR).as_posix(),
        archive_scope="full_local_archive" if _archive_path().parent.name == "processed" else "demonstration_sample",
        model_version=_model_versions.get(request.horizon_days, "fixture"), inference_mode=request.inference_mode,
    )


@app.get("/health", response_model=HealthResponse)
def health_check():
    ready = sorted(h for h in _models if _model_loaded and h in _calibrators and _feature_cols
                   and getattr(_calibrators[h], "is_fitted_", False))
    return HealthResponse(status="ok" if len(ready) == 3 and _polygon is not None and _grid_cells and _archive_path().exists() else "degraded",
                          model_loaded=bool(ready), available_horizons=ready,
                          supported_inference_modes={"historical_replay": "Exact cell/date lookup; publication time unknown",
                                                     "operational_forecast": "Unavailable; not implemented"})


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    _, _, response = _prepare(request)
    return PredictionResponse(**response)


@app.post("/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest):
    model, values, response = _prepare(request)
    # Native LightGBM TreeSHAP: raw-margin contributions followed by the baseline.
    contributions = np.asarray(model.predict(values, pred_contrib=True))[0]
    raw_margin = float(model.predict(values, raw_score=True)[0])
    if not np.isclose(contributions.sum(), raw_margin, atol=1e-6):
        raise ValueError("SHAP additivity verification failed")
    shap_values = dict(zip(_feature_cols, map(float, contributions[:-1])))
    ordered = sorted(shap_values.items(), key=lambda item: item[1], reverse=True)
    return ExplainResponse(**response, shap_values=shap_values,
                           top_positive=[{"feature": k, "shap": v} for k, v in ordered if v > 0][:5],
                           top_negative=[{"feature": k, "shap": v} for k, v in reversed(ordered) if v < 0][:5],
                           baseline_log_odds=float(contributions[-1]), raw_log_odds=raw_margin)


@app.get("/drift")
def drift_report():
    path = _PROJECT_ROOT / "reports/drift_report.json"
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(report, dict) or report.get("report_type") != "historical_drift_analysis"
                or report.get("monitoring_mode") != "retrospective_evaluation"
                or not isinstance(report.get("summary"), dict) or not isinstance(report.get("features"), list)
                or report["summary"].get("total_monitored") != len(report["features"])
                or report.get("continuous_monitoring", False) is not False):
            raise ValueError("Invalid historical covariate report schema")
        return report
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(503, "Historical drift report unavailable or invalid") from exc


@app.get("/")
def root():
    return {"message": "Brazil Wildfire Risk Forecast: historical replay", "docs": "/docs",
            "health": "/health", "predict": "/predict", "explain": "/explain", "drift": "/drift"}
