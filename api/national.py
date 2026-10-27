"""National research readiness API; no national model is available yet.

Run separately from the preserved MT pilot with ``uvicorn api.national:app``.
This scaffold deliberately does not import any pilot model or inference code.
"""

import datetime as dt
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.geo.uf_registry import UF_BY_CODE, UF_REGISTRY

SCOPE = "brazil_national_v1"
app = FastAPI(title="Brazil National Research Expansion — readiness", version="0.1.0",
              description="Registry and pending capabilities; national inference is unavailable.")


def state_readiness(uf_code: str) -> dict:
    """Report implemented registration separately from unexecuted scientific stages.

    These are conservative capabilities of this scaffold, not filesystem guesses.
    A future validated national artifact registry must replace the pending stages.
    """
    uf = UF_BY_CODE[uf_code]
    return dict(uf_code=uf.uf_code, abbreviation=uf.abbreviation, uf_name=uf.name,
                region_code=uf.region_code, region_name=uf.region_name,
                registered=True, geometry_available=False, grid_created=False,
                valid_fire_data=False, valid_climate_data=False, features_computed=False,
                model_applicable=False, metrics_calculated=False,
                performance_estimable=None, available_period=None, spatial_units=None,
                model_version=None, data_version=None, geometry_version=None,
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
    latitude: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(..., ge=-180, le=180, allow_inf_nan=False)
    date: dt.date
    horizon_days: Literal[1, 3, 7] = 7
    inference_mode: Literal["historical_replay", "operational_forecast"] = "historical_replay"


@app.post("/predict")
def unavailable_prediction(request: NationalRequest):
    # Without real national geometry, even UF/territorial location is unknown.
    # Do not use an approximate bounding box as proof of Brazilian territory.
    raise HTTPException(503, dict(code="NATIONAL_INFERENCE_UNAVAILABLE", scope=SCOPE,
                                 message="National geometry, data and validated model are not available; no Mato Grosso fallback.",
                                 territory_verified=False, inference_mode=request.inference_mode))
