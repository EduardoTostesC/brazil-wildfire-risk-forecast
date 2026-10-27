"""National registry must never masquerade as model coverage or pilot inference."""

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api.national import app
from src.geo.uf_registry import UF_REGISTRY


def test_registry_separates_every_national_capability():
    response = TestClient(app).get("/coverage")
    assert response.status_code == 200
    result = response.json()
    assert result["registry_is_predictive_coverage"] is False
    assert result["national_inference_available"] is False
    assert len(result["states"]) == 27
    assert len({row["uf_code"] for row in result["states"]}) == 27
    for row in result["states"]:
        assert row["registered"] is True
        for field in ("geometry_available", "grid_created", "valid_fire_data", "valid_climate_data",
                      "features_computed", "model_applicable", "metrics_calculated"):
            assert row[field] is False
        assert row["metrics"] is None and row["performance_estimable"] is None


@pytest.mark.parametrize("uf", UF_REGISTRY)
def test_each_uf_has_honest_individual_status(uf):
    result = TestClient(app).get(f"/coverage/{uf.uf_code}")
    assert result.status_code == 200
    assert result.json()["abbreviation"] == uf.abbreviation
    assert result.json()["model_version"] is None


def test_unknown_code_is_not_registered():
    assert TestClient(app).get("/coverage/99").status_code == 404


@pytest.mark.parametrize("latitude,longitude", [(-12.5, -55), (-15.8, -47.9), (0, 0), (-25, -30)])
@pytest.mark.parametrize("horizon", [1, 3, 7])
def test_no_pilot_fallback_or_false_territory_claim(latitude, longitude, horizon, monkeypatch):
    import joblib

    def forbidden_load(*args, **kwargs):
        raise AssertionError("National scaffold must not load pilot artifacts")
    monkeypatch.setattr(joblib, "load", forbidden_load)
    response = TestClient(app).post("/predict", json=dict(latitude=latitude, longitude=longitude,
                                                        date="2024-08-15", horizon_days=horizon))
    assert response.status_code == 503
    assert response.json()["detail"]["scope"] == "brazil_national_v1"
    assert response.json()["detail"]["territory_verified"] is False
    assert "probability" not in response.text


@pytest.mark.parametrize("change", [{"latitude": 91}, {"longitude": -181}, {"date": "2024-02-30"},
                                    {"horizon_days": 2}, {"inference_mode": "anything"}])
def test_national_invalid_requests_are_422(change):
    payload = dict(latitude=-15.8, longitude=-47.9, date="2024-02-29")
    payload.update(change)
    assert TestClient(app).post("/predict", json=payload).status_code == 422


@pytest.mark.parametrize("language", ["pt-BR", "en"])
def test_national_dashboard_all_states_df_and_languages(language):
    dashboard = AppTest.from_file("app/national_app.py", default_timeout=30)
    dashboard.session_state["national_language"] = language
    dashboard.run()
    assert not dashboard.exception
    assert len(dashboard.sidebar.selectbox(key="national_uf").options) == 27
    dashboard.sidebar.selectbox(key="national_uf").set_value("53").run()
    assert not dashboard.exception
    assert "Distrito Federal" in dashboard.subheader[0].value
    assert len(dashboard.dataframe[0].value) == 27
    dashboard.sidebar.selectbox(key="national_region").set_value("5").run()
    assert not dashboard.exception
    assert len(dashboard.sidebar.selectbox(key="national_uf").options) == 4
    assert dashboard.warning and dashboard.info
