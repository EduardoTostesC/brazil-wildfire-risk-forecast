"""National registry must never masquerade as model coverage or pilot inference."""

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api.national import app, national_boundaries
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
        assert row["geometry_available"] is True
        assert row["grid_created"] is True and row["spatial_units"] > 0
        for field in ("valid_fire_data", "valid_climate_data",
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


@pytest.mark.parametrize("latitude,longitude", [(-12.5, -55), (-15.8, -47.9)])
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
    assert response.json()["detail"]["territory_verified"] is True
    assert "probability" not in response.text


@pytest.mark.parametrize("latitude,longitude", [(0, 0), (-25, -30)])
def test_real_geography_rejects_ocean_and_other_territory(latitude, longitude):
    response = TestClient(app).post("/locate", json=dict(latitude=latitude, longitude=longitude))
    assert response.status_code == 422


def test_real_df_location_is_separate_from_model_availability():
    response = TestClient(app).post("/locate", json=dict(latitude=-15.8, longitude=-47.9))
    assert response.status_code == 200
    assert response.json()["uf_code"] == "53"
    assert response.json()["national_inference_available"] is False


@pytest.mark.parametrize("uf", UF_REGISTRY)
def test_real_27_uf_territorial_lookup(uf):
    point = national_boundaries()[uf.uf_code].representative_point()
    response = TestClient(app).post("/locate", json=dict(latitude=point.y, longitude=point.x))
    assert response.status_code == 200
    result = response.json()
    assert result["uf_code"] == uf.uf_code
    assert result["geometry_version"] == "ibge-2024"
    assert result["spatial_unit_id"].endswith(f":uf{uf.uf_code}")


def test_missing_national_geography_is_not_replaced_by_pilot(monkeypatch):
    import api.national as national

    def missing():
        raise FileNotFoundError("national geometry missing")
    monkeypatch.setattr(national, "national_boundaries", missing)
    response = TestClient(app).post("/locate", json=dict(latitude=-12.5, longitude=-55))
    assert response.status_code == 503
    assert TestClient(app).get("/coverage/51").json()["geometry_available"] is False


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
    dashboard.checkbox(key="national_show_map").check().run()
    assert not dashboard.exception
    dashboard.sidebar.selectbox(key="national_region").set_value("5").run()
    assert not dashboard.exception
    assert len(dashboard.sidebar.selectbox(key="national_uf").options) == 4
    assert dashboard.warning and dashboard.info
