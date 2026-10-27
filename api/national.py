"""National research readiness API; no national model is available yet.

Run separately from the preserved MT pilot with ``uvicorn api.national:app``.
This scaffold deliberately does not import any pilot model or inference code.
"""

import datetime as dt
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.geo.boundaries import GEOMETRY_VERSION, load_boundaries
from src.geo.national_grid import assign_point, grid_version
from src.geo.uf_registry import UF_BY_CODE, UF_REGISTRY

SCOPE = "brazil_national_v1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="Brazil National Research Expansion — readiness", version="0.1.0",
              description="Registry and pending capabilities; national inference is unavailable.")


@lru_cache(maxsize=1)
def national_boundaries():
    """Load only the separately archived national geometry; never the MT polygon."""
    root = PROJECT_ROOT / "data/geo/national/ibge-2024"
    return load_boundaries(root / "BR_UF_2024.geojson.gz", root / "receipt.json")


def geometry_available():
    try:
        return len(national_boundaries()) == 27
    except (OSError, ValueError, KeyError, TypeError):
        return False


@lru_cache(maxsize=1)
def grid_inventory():
    """Use measured grid counts only when bound to the current archived geometry."""
    try:
        source = PROJECT_ROOT / "data/geo/national/ibge-2024"
        evidence = json.loads((PROJECT_ROOT / "reports/national/real-grid-evidence.json").read_text())
        for field, name in [("geometry_gzip_sha256", "BR_UF_2024.geojson.gz"),
                            ("receipt_sha256", "receipt.json")]:
            if evidence[field] != hashlib.sha256((source / name).read_bytes()).hexdigest():
                return {}
        result = next(item for item in evidence["results"] if item["resolution_deg"] == 0.5)
        states = result["per_uf"]
        if (set(states) != set(UF_BY_CODE)
                or any(not isinstance(row["spatial_units"], int) or row["spatial_units"] < 1 for row in states.values())
                or sum(row["spatial_units"] for row in states.values()) != result["spatial_units"]):
            return {}
        return states
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return {}


def state_readiness(uf_code: str) -> dict:
    """Report implemented registration separately from unexecuted scientific stages.

    Geography is verified from the archived receipt; later scientific stages
    remain unavailable until a validated artifact registry provides evidence.
    """
    uf = UF_BY_CODE[uf_code]
    geography = geometry_available()
    grid = grid_inventory().get(uf_code) if geography else None
    return dict(uf_code=uf.uf_code, abbreviation=uf.abbreviation, uf_name=uf.name,
                region_code=uf.region_code, region_name=uf.region_name,
                registered=True, geometry_available=geography, grid_created=grid is not None,
                valid_fire_data=False, valid_climate_data=False, features_computed=False,
                model_applicable=False, metrics_calculated=False,
                performance_estimable=None, available_period=None,
                spatial_units=grid["spatial_units"] if grid else None,
                grid_version=grid_version() if grid else None,
                model_version=None, data_version=None,
                geometry_version=GEOMETRY_VERSION if geography else None,
                metrics=None, status="pending_national_evidence")


@app.get("/coverage")
def coverage():
    return dict(scope=SCOPE, status="development", national_inference_available=False,
                registry_is_predictive_coverage=False,
                states=[state_readiness(uf.uf_code) for uf in UF_REGISTRY])


@app.get("/coverage/{uf_code}")
def state_coverage(uf_code: str):
    if uf_code not in UF_BY_CODE:
        raise HTTPException(404, "Unknown IBGE UF code")
    return dict(scope=SCOPE, **state_readiness(uf_code))


class NationalRequest(BaseModel):
    latitude: float = Field(..., ge=-90, lt=90, allow_inf_nan=False)
    longitude: float = Field(..., ge=-180, lt=180, allow_inf_nan=False)
    date: dt.date
    horizon_days: Literal[1, 3, 7] = 7
    inference_mode: Literal["historical_replay", "operational_forecast"] = "historical_replay"


class LocationRequest(BaseModel):
    latitude: float = Field(..., ge=-90, lt=90, allow_inf_nan=False)
    longitude: float = Field(..., ge=-180, lt=180, allow_inf_nan=False)


def locate(request):
    try:
        boundaries = national_boundaries()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, "National territorial validation unavailable") from exc
    result = assign_point(request.latitude, request.longitude, boundaries)
    if result is None:
        raise HTTPException(422, "Point outside covered Brazilian territorial units")
    uf = UF_BY_CODE[result["uf_code"]]
    return dict(scope=SCOPE, **result, uf_name=uf.name, region_code=uf.region_code,
                geometry_version=GEOMETRY_VERSION, grid_version=grid_version(),
                territory_verified=True, national_inference_available=False)


@app.post("/locate")
def locate_point(request: LocationRequest):
    """Geographic lookup only; a covered coordinate is not a trained model."""
    return locate(request)


@app.post("/predict")
def unavailable_prediction(request: NationalRequest):
    location = locate(LocationRequest(latitude=request.latitude, longitude=request.longitude))
    raise HTTPException(503, dict(code="NATIONAL_INFERENCE_UNAVAILABLE", scope=SCOPE,
                                 message="National data and validated model are not available; no Mato Grosso fallback.",
                                 location=location, territory_verified=True,
                                 inference_mode=request.inference_mode))
