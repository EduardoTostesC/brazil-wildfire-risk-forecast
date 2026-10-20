"""FastAPI endpoint for wildfire risk prediction.

Receives latitude, longitude, and date, and returns the predicted probability
of at least one fire hotspot in that grid cell within the next 7 days,
along with a risk level (low/medium/high).
"""

import datetime as dt
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Brazil Wildfire Risk Forecast API",
    description=(
        "Predict the probability of fire hotspots in a geographic grid cell "
        "within the next 7 days. Based on INPE fire data and NASA POWER climate data."
    ),
    version="1.0.0",
)

# ── Load model and metadata at startup ────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MODELS_DIR = _PROJECT_ROOT / "models"

try:
    if (_MODELS_DIR / "lightgbm_model.joblib").exists():
        _model = joblib.load(_MODELS_DIR / "lightgbm_model.joblib")
    elif (_MODELS_DIR / "lightgbm_calibrated.joblib").exists():
        _model = joblib.load(_MODELS_DIR / "lightgbm_calibrated.joblib")
    else:
        _model = None
    _feature_cols = joblib.load(_MODELS_DIR / "feature_cols.joblib")
    _scaler = None
    _model_loaded = True if _model is not None else False
except Exception:
    _model_loaded = False
    _model = None
    _feature_cols = []


# ── Schemas ───────────────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    """Request schema for wildfire risk prediction."""
    latitude: float = Field(..., ge=-33.0, le=5.5, description="Latitude (decimal degrees)")
    longitude: float = Field(..., ge=-74.0, le=-34.0, description="Longitude (decimal degrees)")
    date: dt.date = Field(..., description="Prediction date (YYYY-MM-DD)")

    model_config = {"json_schema_extra": {
        "examples": [{"latitude": -12.5, "longitude": -55.0, "date": "2024-08-15"}]
    }}


class PredictionResponse(BaseModel):
    """Response schema for wildfire risk prediction."""
    latitude: float
    longitude: float
    date: str
    probability: float = Field(..., description="Probability of fire in next 7 days (0-1)")
    risk_level: str = Field(..., description="Risk level: low, medium, or high")
    grid_id: str = Field(..., description="Grid cell identifier")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool


# ── Helper functions ──────────────────────────────────────────────────────────

def _classify_risk(probability: float) -> str:
    """Convert probability to risk level."""
    if probability < 0.3:
        return "low"
    elif probability < 0.6:
        return "medium"
    else:
        return "high"


_cached_grid = None
_cached_df = None


def _get_cached_data():
    """Load and cache grid lookup for ultra-fast API inference."""
    global _cached_grid, _cached_df
    if _cached_df is None:
        feat_path = _PROJECT_ROOT / "data" / "processed" / "features.parquet"
        sample_path = _PROJECT_ROOT / "data" / "sample" / "features_sample.parquet"
        target_path = feat_path if feat_path.exists() else sample_path
        if target_path.exists():
            try:
                # Load only required columns and the most recent 1 year for fast lookup
                df = pd.read_parquet(target_path)
                df["date"] = pd.to_datetime(df["date"])
                _cached_df = df
                _cached_grid = df[["grid_id", "lat_center", "lon_center"]].drop_duplicates().reset_index(drop=True)
            except Exception:
                pass
    return _cached_grid, _cached_df


def _build_features(lat: float, lon: float, pred_date: dt.date) -> np.ndarray:
    """Build a feature vector for a single prediction.

    In production, this queries live fire and climate stream data.
    For local serving, queries cached nearest grid cell data.
    """
    dt_obj = dt.datetime.combine(pred_date, dt.time.min)
    day_of_year = dt_obj.timetuple().tm_yday
    month = dt_obj.month

    # Create feature dict with defaults
    features: dict[str, float] = {}
    for col in _feature_cols:
        if col == "lat_center":
            features[col] = lat
        elif col == "lon_center":
            features[col] = lon
        elif col == "month_sin":
            features[col] = np.sin(2 * np.pi * month / 12)
        elif col == "month_cos":
            features[col] = np.cos(2 * np.pi * month / 12)
        elif col == "doy_sin":
            features[col] = np.sin(2 * np.pi * day_of_year / 365)
        elif col == "doy_cos":
            features[col] = np.cos(2 * np.pi * day_of_year / 365)
        else:
            features[col] = 0.0

    # Query cached history for nearest cell
    grid_lookup, full_df = _get_cached_data()
    if grid_lookup is not None and full_df is not None:
        try:
            dists = (grid_lookup["lat_center"] - lat) ** 2 + (grid_lookup["lon_center"] - lon) ** 2
            nearest_grid = grid_lookup.loc[dists.idxmin(), "grid_id"]

            cell_data = full_df[full_df["grid_id"] == nearest_grid]
            if not cell_data.empty:
                # Match by same day-of-year across available historical years
                target_doy = day_of_year
                cell_doy = cell_data["date"].dt.dayofyear
                closest_idx = (cell_doy - target_doy).abs().idxmin()
                row = cell_data.loc[closest_idx]

                for col in _feature_cols:
                    if col in row.index and pd.notna(row[col]):
                        features[col] = float(row[col])
        except Exception:
            pass

    return np.array([[features[col] for col in _feature_cols]], dtype=np.float32)

    return np.array([[features[col] for col in _feature_cols]], dtype=np.float32)


def _get_grid_id(lat: float, lon: float) -> str:
    """Compute grid ID from coordinates."""
    try:
        import yaml
        with open(_PROJECT_ROOT / "config.yaml") as f:
            cfg = yaml.safe_load(f)
        res = cfg["grid"]["resolution_deg"]
        lat_min = cfg["region"]["lat_min"]
        lon_min = cfg["region"]["lon_min"]
        row = int((lat - lat_min) / res)
        col = int((lon - lon_min) / res)
        return f"{row:03d}_{col:03d}"
    except Exception:
        return "unknown"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Check if the API is running and the model is loaded."""
    return HealthResponse(
        status="ok" if _model_loaded else "degraded",
        model_loaded=_model_loaded,
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    """Predict wildfire risk for a given location and date.

    Returns the probability of at least one fire hotspot within 7 days
    in the grid cell containing the specified coordinates.

    **Example request:**
    ```json
    {"latitude": -12.5, "longitude": -55.0, "date": "2024-08-15"}
    ```

    **Risk levels:**
    - **low**: probability < 30%
    - **medium**: probability 30-60%
    - **high**: probability > 60%
    """
    if not _model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Run training first.",
        )

    X = _build_features(request.latitude, request.longitude, request.date)
    probability = float(_model.predict_proba(X)[0, 1])
    probability = round(min(max(probability, 0.0), 1.0), 4)

    return PredictionResponse(
        latitude=request.latitude,
        longitude=request.longitude,
        date=str(request.date),
        probability=probability,
        risk_level=_classify_risk(probability),
        grid_id=_get_grid_id(request.latitude, request.longitude),
    )


@app.get("/")
def root():
    """API root — redirect to docs."""
    return {
        "message": "Brazil Wildfire Risk Forecast API",
        "docs": "/docs",
        "health": "/health",
    }

