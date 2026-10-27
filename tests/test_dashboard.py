"""Exercise bilingual UI state, exact sample inference and loading failures."""

import string

import joblib
import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app.i18n import CATALOGS, translate
from src.models.inference import calibrated_probabilities, feature_matrix


def test_translation_catalogs_have_matching_keys_and_placeholders():
    assert set(CATALOGS["pt-BR"]) == set(CATALOGS["en"])
    formatter = string.Formatter()
    def fields(text):
        return {name for _, name, _, _ in formatter.parse(text) if name is not None}
    for key in CATALOGS["en"]:
        first, second = CATALOGS["en"][key], CATALOGS["pt-BR"][key]
        assert first.strip() and second.strip()
        assert fields(first) == fields(second), key
    with pytest.raises(ValueError, match="Unsupported"):
        translate("warning", "fr")
    assert "não é um sistema operacional" in translate("warning", "pt-BR")
    assert "not an operational" in translate("warning", "en")
    assert "causalidade" in translate("shap_desc", "pt-BR")
    assert "causality" in translate("shap_desc", "en")
    assert "Regressão logística" == translate("logistic", "pt-BR")
    assert "células" in translate("ranking_map", "pt-BR")


@pytest.mark.parametrize("language", ["pt-BR", "en"])
def test_dashboard_all_tabs_languages_and_horizon_inference(monkeypatch, language):
    monkeypatch.setenv("WILDFIRE_USE_SAMPLE", "1")
    app = AppTest.from_file("app/streamlit_app.py", default_timeout=60)
    app.session_state["language"] = language
    app.run()
    assert not app.exception and not app.error
    assert len(app.tabs) == 5
    assert app.warning[0].value == translate("warning", language)
    assert app.tabs[3].label == translate("drift_tab", language)
    frame = pd.read_parquet("data/sample/features_sample.parquet")
    columns = joblib.load("models/feature_cols.joblib")
    for horizon in (1, 3, 7):
        app.sidebar.radio(key="map_horizon").set_value(horizon).run()
        assert not app.exception and not app.error
        date = app.sidebar.date_input(key="map_date").value
        rows = frame[frame.date.dt.date == date]
        model = joblib.load(f"models/lightgbm_{horizon}d.joblib" if horizon != 7 else "models/lightgbm_model.joblib")
        cal = joblib.load(f"models/platt_calibrator_{horizon}d.joblib" if horizon != 7 else "models/platt_calibrator.joblib")
        expected = calibrated_probabilities(model, cal, feature_matrix(rows, columns))
        assert app.metric[0].value == str(len(rows))
        assert app.metric[1].value == f"{np.mean(expected):.1%}"
    other = "en" if language == "pt-BR" else "pt-BR"
    app.sidebar.selectbox(key="language").set_value(other).run()
    assert not app.exception and not app.error
    assert app.tabs[0].label == translate("map_tab", other)
    app.sidebar.multiselect(key="map_bands").set_value([]).run()
    assert translate("no_rows", other) in [item.value for item in app.warning]


@pytest.mark.parametrize("language", ["pt-BR", "en"])
def test_dashboard_loading_failure_is_localized_without_exception(monkeypatch, language):
    st.cache_data.clear()
    monkeypatch.setenv("WILDFIRE_USE_SAMPLE", "1")
    def unreadable(*args, **kwargs):
        raise OSError("Synthetic unavailable archive")
    monkeypatch.setattr(pd, "read_parquet", unreadable)
    app = AppTest.from_file("app/streamlit_app.py", default_timeout=60)
    app.session_state["language"] = language
    app.run()
    assert not app.exception
    assert app.error[0].value == translate("unavailable", language)
    st.cache_data.clear()


def test_native_dashboard_shap_matches_previous_tree_explainer():
    import shap
    model = joblib.load("models/lightgbm_model.joblib")
    columns = joblib.load("models/feature_cols.joblib")
    frame = pd.read_parquet("data/sample/features_sample.parquet").iloc[[0, 351, 1000]]
    values = feature_matrix(frame, columns)
    old = shap.TreeExplainer(model).shap_values(values)
    if isinstance(old, list):
        old = old[1]
    native = np.asarray(model.predict(values, pred_contrib=True))
    np.testing.assert_allclose(native[:, :-1], old, rtol=0, atol=1e-9)
    np.testing.assert_allclose(native.sum(axis=1), model.predict(values, raw_score=True), rtol=0, atol=1e-6)
