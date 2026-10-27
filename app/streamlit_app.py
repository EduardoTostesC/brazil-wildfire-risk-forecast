"""Bilingual retrospective replay; no live forecast or emergency decision support."""

import hashlib
import json
import os
import pickle
import sys
from datetime import timedelta
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

import folium
import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from app.i18n import LANGUAGES, horizon_label, translate
from src.data.build_grid import _load_ibge_polygon, build_grid
from src.models.inference import calibrated_probabilities, feature_matrix
from src.models.risk_tiers import DEFAULT_RISK_CONFIG

st.set_page_config(page_title="Brazil Wildfire Risk Forecast", page_icon="🔥",
                   layout="wide", initial_sidebar_state="auto")
COLORS = {"Low": DEFAULT_RISK_CONFIG.color_low, "Medium": DEFAULT_RISK_CONFIG.color_medium,
          "High": DEFAULT_RISK_CONFIG.color_high}


def tr(key, **values):
    return translate(key, st.session_state.get("language", "pt-BR"), **values)


def level_label(level):
    return tr(level.lower())


@st.cache_resource(show_spinner=False)
def _load_models():
    models, calibrators, versions = {}, {}, {}
    columns = joblib.load(_PROJECT_ROOT / "models/feature_cols.joblib")
    if not isinstance(columns, list) or not columns or len(set(columns)) != len(columns):
        raise ValueError("Invalid feature schema")
    for h in (1, 3, 7):
        model_path = _PROJECT_ROOT / "models" / (f"lightgbm_{h}d.joblib" if h != 7 else "lightgbm_model.joblib")
        cal_path = _PROJECT_ROOT / "models" / (f"platt_calibrator_{h}d.joblib" if h != 7 else "platt_calibrator.joblib")
        models[h], calibrators[h] = joblib.load(model_path), joblib.load(cal_path)
        if not getattr(calibrators[h], "is_fitted_", False) or models[h].n_features_in_ != len(columns):
            raise ValueError("Invalid model/calibrator pair")
        versions[h] = "sha256:" + hashlib.sha256(model_path.read_bytes() + cal_path.read_bytes()).hexdigest()
    return models, calibrators, columns, versions


@st.cache_data(show_spinner=False)
def _load_dataframe():
    full = _PROJECT_ROOT / "data/processed/features.parquet"
    sample = _PROJECT_ROOT / "data/sample/features_sample.parquet"
    is_sample = os.environ.get("WILDFIRE_USE_SAMPLE") == "1" or not full.exists()
    frame = pd.read_parquet(sample if is_sample else full)
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    if frame.duplicated(["grid_id", "date"]).any():
        raise ValueError("Duplicate historical keys")
    grid = build_grid()
    valid = grid.loc[grid.state_status != "outside", "grid_id"]
    frame = frame[frame.grid_id.isin(valid) & (frame.date >= "2024-01-01")].copy()
    return frame, is_sample


@st.cache_data(show_spinner=False, max_entries=12)
def _probabilities(frame, horizon, version, _models, _calibrators, columns):
    # Immutable artifact digest participates in the cache key; resources do not.
    return calibrated_probabilities(_models[horizon], _calibrators[horizon], feature_matrix(frame, columns))


def _add_predictions(frame, models, calibrators, columns, horizon, version):
    result = frame.copy()
    result["probability"] = _probabilities(frame, horizon, version, models, calibrators, columns)
    result["risk_level"] = np.where(result.probability >= DEFAULT_RISK_CONFIG.high_cutoff, "High",
                                    np.where(result.probability >= DEFAULT_RISK_CONFIG.low_cutoff, "Medium", "Low"))
    return result


def chart(figure):
    figure.update_layout(height=figure.layout.height or 420,
                         separators=",." if st.session_state.language == "pt-BR" else ".,",
                         font=dict(family="sans-serif", size=13), margin=dict(l=12, r=12, t=65, b=35))
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False, "responsive": True})


@st.cache_data(show_spinner=False)
def _load_csv(name):
    path = _PROJECT_ROOT / "reports" / name
    return pd.read_csv(path) if path.is_file() else None


def _build_risk_map(frame):
    m = folium.Map(location=[frame.lat_center.mean(), frame.lon_center.mean()], zoom_start=6,
                   tiles="OpenStreetMap", control_scale=True)
    folium.GeoJson(_load_ibge_polygon(_PROJECT_ROOT).__geo_interface__, name=tr("boundary"),
                   style_function=lambda _: {"color": "#34495e", "weight": 2, "fillOpacity": 0}).add_to(m)
    for row in frame.itertuples():
        color = COLORS[row.risk_level]
        tooltip = (f"<b>{tr('cell')} {row.grid_id}</b><br>{tr('probability')}: {row.probability:.1%}"
                   f"<br>{tr('risk')}: {level_label(row.risk_level)}<br>{row.lat_center:.2f}°, {row.lon_center:.2f}°")
        folium.CircleMarker(location=[row.lat_center, row.lon_center], radius=6, color=color,
                            fill=True, fill_opacity=.8, tooltip=tooltip, popup=tooltip).add_to(m)
    legend = f'<div style="position:fixed;bottom:25px;left:12px;z-index:1000;background:white;padding:9px;border:1px solid #aaa;font-size:12px"><b>{tr("legend")}</b><br>'
    low, high = DEFAULT_RISK_CONFIG.low_cutoff, DEFAULT_RISK_CONFIG.high_cutoff
    for level, limits in [("Low", f"&lt;{low:.0%}"), ("Medium", f"{low:.0%}–{high:.0%}"), ("High", f"≥{high:.0%}")]:
        legend += f'<span style="color:{COLORS[level]}">●</span> {level_label(level)} ({limits})<br>'
    m.get_root().html.add_child(folium.Element(legend + "</div>"))
    return m


def tab_map(frame, models, calibrators, columns, versions):
    st.subheader(tr("map_title"))
    language = st.session_state.language
    h = st.sidebar.radio(tr("horizon"), [7, 3, 1], format_func=lambda value: horizon_label(value, language), key="map_horizon")
    dates = sorted(frame.date.dt.date.unique())
    date = st.sidebar.date_input(tr("date"), value=dates[len(dates) * 3 // 4], min_value=dates[0], max_value=dates[-1], key="map_date")
    bands = st.sidebar.multiselect(tr("levels"), list(COLORS), default=list(COLORS), format_func=lambda level: translate(level.lower(), language), key="map_bands")
    day = frame[frame.date.dt.date == date]
    st.caption(tr("window", date=date, start=date + timedelta(days=1), end=date + timedelta(days=h), h=h))
    st.caption(tr("model_version", version=versions[h][:23] + "…"))
    if day.empty or not bands:
        st.warning(tr("no_rows"))
        return
    day = _add_predictions(day, models, calibrators, columns, h, versions[h])
    day = day[day.risk_level.isin(bands)]
    if day.empty:
        st.warning(tr("no_rows"))
        return
    metrics = [("shown", str(len(day))), ("mean", f"{day.probability.mean():.1%}"),
               ("maximum", f"{day.probability.max():.1%}"), ("high_count", str((day.risk_level == "High").sum()))]
    for column, (label, value) in zip(st.columns(4), metrics):
        column.metric(tr(label), value)
    # No component return values are used: suppress click/resize-triggered reruns.
    st_folium(_build_risk_map(day), use_container_width=True, height=480,
              returned_objects=[], key=f"risk_map_{h}_{date}_{st.session_state.language}")
    with st.expander(tr("histogram")):
        plot = day.assign(band=day.risk_level.map(level_label))
        figure = px.histogram(plot, x="probability", color="band", nbins=30,
                           color_discrete_map={level_label(k): v for k, v in COLORS.items()},
                           labels={"probability": tr("probability"), "band": tr("risk")})
        figure.update_yaxes(title=tr("count"))
        figure.update_xaxes(range=[0, 1], tickformat=".0%")
        chart(figure)


def tab_ranking(frame, models, calibrators, columns, versions):
    st.subheader(tr("rank_title"))
    st.write(tr("rank_desc"))
    language = st.session_state.language
    h = st.selectbox(tr("horizon"), [7, 3, 1], format_func=lambda value: horizon_label(value, language), key="ranking_horizon")
    n = st.slider(tr("top_n"), 10, 50, 20, 5)
    prediction = _add_predictions(frame, models, calibrators, columns, h, versions[h])
    ranking = prediction.groupby("grid_id").agg(lat=("lat_center", "first"), lon=("lon_center", "first"),
        mean_prob=("probability", "mean"), max_prob=("probability", "max"),
        pct_high=("risk_level", lambda x: (x == "High").mean() * 100),
        pct_medium=("risk_level", lambda x: (x == "Medium").mean() * 100)).sort_values("mean_prob", ascending=False).head(n).reset_index()
    display = ranking.rename(columns={"grid_id": tr("cell"), **{key: tr(key) for key in ["lat", "lon", "mean_prob", "max_prob", "pct_high", "pct_medium"]}})
    st.dataframe(display, hide_index=True, use_container_width=True)
    with st.expander(tr("ranking_map")):
        map_frame = ranking.rename(columns={"lat": "lat_center", "lon": "lon_center", "mean_prob": "probability"}).copy()
        map_frame["risk_level"] = np.where(map_frame.probability >= DEFAULT_RISK_CONFIG.high_cutoff, "High",
            np.where(map_frame.probability >= DEFAULT_RISK_CONFIG.low_cutoff, "Medium", "Low"))
        st_folium(_build_risk_map(map_frame), use_container_width=True, height=380,
                  returned_objects=[], key=f"ranking_map_{h}_{language}")
    figure = px.bar(ranking, x="grid_id", y="mean_prob", title=tr("ranking_chart", h=h),
                   labels={"grid_id": tr("cell"), "mean_prob": tr("probability")}, color_discrete_sequence=["#b73e28"])
    figure.update_yaxes(range=[0, 1], tickformat=".0%")
    chart(figure)
    top = ranking.iloc[0].grid_id
    monthly = prediction[prediction.grid_id == top].set_index("date").probability.resample("ME").mean().reset_index()
    figure = px.line(monthly, x="date", y="probability", markers=True, title=tr("trend", cell=top),
                     labels={"date": tr("month"), "probability": tr("probability")})
    figure.update_yaxes(range=[0, 1], tickformat=".0%")
    chart(figure)


def tab_shap(frame, models, calibrators, columns):
    st.subheader(tr("shap_title"))
    st.write(tr("shap_desc"))
    c1, c2 = st.columns(2)
    cell = c1.selectbox(tr("cell"), sorted(frame.grid_id.unique()), key="shap_cell")
    dates = sorted(frame.date.dt.date.unique())
    date = c2.date_input(tr("date"), value=dates[len(dates) * 3 // 4], min_value=dates[0], max_value=dates[-1], key="shap_date")
    row = frame[(frame.grid_id == cell) & (frame.date.dt.date == date)]
    if len(row) != 1:
        st.warning(tr("no_rows"))
        return
    values = feature_matrix(row, columns)
    contributions = np.asarray(models[7].predict(values, pred_contrib=True))[0]
    raw = float(models[7].predict(values, raw_score=True)[0])
    if not np.isclose(contributions.sum(), raw, atol=1e-6):
        st.error(tr("shap_error"))
        return
    probability = calibrated_probabilities(models[7], calibrators[7], values)[0]
    st.metric(tr("probability"), f"{probability:.1%}")
    table = pd.DataFrame({tr("feature"): columns, tr("value"): values[0], "SHAP": contributions[:-1]})
    table = table.sort_values("SHAP", key=abs, ascending=False)
    top = table.head(15).iloc[::-1]
    fig = go.Figure(go.Bar(y=top[tr("feature")], x=top.SHAP, orientation="h",
                           marker_color=np.where(top.SHAP > 0, "#b73e28", "#2166ac")))
    fig.update_layout(title=tr("shap_chart"), xaxis_title=tr("shap_axis"), height=550)
    chart(fig)
    st.caption(tr("shap_caption"))
    with st.expander(tr("shap_all")):
        st.dataframe(table, hide_index=True, use_container_width=True)


def tab_drift():
    st.subheader(tr("drift_title"))
    st.write(tr("drift_desc"))
    try:
        report = json.loads((_PROJECT_ROOT / "reports/drift_report.json").read_text(encoding="utf-8"))
        if report.get("report_type") != "historical_drift_analysis" or report.get("continuous_monitoring") is not False:
            raise ValueError("Unexpected report scope")
        features = pd.DataFrame(report["features"])
        if features.empty or not {"feature", "PSI", "status", "baseline_mean", "current_mean", "KS_pvalue"}.issubset(features.columns):
            raise ValueError("Invalid drift schema")
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        st.warning(tr("drift_missing"))
        return
    for column, (key, count) in zip(st.columns(4), [("features_compared", len(features)),
        ("stable", (features.PSI < .10).sum()), ("moderate", features.PSI.between(.10, .25, inclusive="left").sum()),
        ("critical", (features.PSI >= .25).sum())]):
        column.metric(tr(key), str(count))
    categories = {"STABLE": tr("stable"), "MODERATE_DRIFT": tr("moderate"), "CRITICAL_DRIFT": tr("critical")}
    features["category"] = features.status.map(categories)
    chart(px.bar(features.sort_values("PSI", ascending=False), x="feature", y="PSI", color="category",
                 title=tr("psi_chart"), labels={"feature": tr("feature"), "category": tr("status")},
                 color_discrete_map={tr("stable"): "#278250", tr("moderate"): "#b67b00", tr("critical"): "#b73e28"}))
    st.caption(tr("psi_caption"))
    st.dataframe(features[["feature", "baseline_mean", "current_mean", "PSI", "KS_pvalue"]].rename(
        columns={"feature": tr("feature"), "baseline_mean": tr("baseline_mean"), "current_mean": tr("comparison_mean"), "KS_pvalue": tr("ks_reference")}),
        hide_index=True, use_container_width=True)
    walk = _load_csv("walk_forward_metrics.csv")
    if walk is not None:
        st.subheader(tr("walk_title"))
        st.write(tr("walk_desc"))
        chart(px.line(walk, x="test_year", y=["PR-AUC", "ROC-AUC"], markers=True,
                      labels={"test_year": tr("year"), "value": tr("metric"), "variable": tr("metric")}))


def tab_about(versions):
    st.subheader(tr("about_title"))
    st.write(tr("method"))
    comparison = _load_csv("model_comparison.csv")
    st.markdown("#### " + tr("benchmark"))
    if comparison is not None:
        display = comparison[["model", "AP", "ROC-AUC", "Brier", "ECE"]].rename(columns={"model": tr("model")})
        names = {"Persistence (Empirical)": "persistence", "Climatology": "climatology",
                 "LogisticRegression": "logistic", "LogisticRegression (Platt Calibrated)": "logistic_platt",
                 "LightGBM (Raw)": "lgb_raw", "LightGBM (Platt Calibrated)": "lgb_platt",
                 "LightGBM (Isotonic Calibrated)": "lgb_isotonic"}
        display[tr("model")] = display[tr("model")].map(lambda name: tr(names[name]) if name in names else name)
        st.dataframe(display, hide_index=True, use_container_width=True)
        st.download_button(tr("download"), comparison.to_csv(index=False), file_name="model_comparison.csv", mime="text/csv")
    else:
        st.info(tr("metrics_missing"))
    horizons = _load_csv("multi_horizon_comparison.csv")
    if horizons is not None:
        st.markdown("#### " + tr("horizons"))
        plot = horizons.assign(H=[int(str(value).split("-")[0]) for value in horizons.horizon])
        chart(px.bar(plot, x="H", y="PR-AUC", labels={"H": tr("horizon"), "PR-AUC": "AP"}))
    with st.expander(tr("model_identity")):
        for h, version in versions.items():
            st.caption(tr("horizon_value", h=h))
            st.code(version, language=None)
    st.markdown("#### " + tr("source_title"))
    st.write(tr("sources"))
    st.markdown("#### " + tr("limitations"))
    st.write(tr("limits"))
    st.markdown(f"[{tr('author')}](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast)")


def main():
    if "language" not in st.session_state:
        requested = st.query_params.get("lang", "pt-BR")
        st.session_state.language = requested if requested in LANGUAGES else "pt-BR"
    st.sidebar.selectbox(translate("language"), list(LANGUAGES), format_func=LANGUAGES.get, key="language")
    st.title("🔥 " + tr("title"))
    st.caption(tr("subtitle"))
    st.warning(tr("warning"))
    with st.expander(tr("meaning")):
        st.write(tr("science"))
        st.write(tr("bands"))
        st.caption(tr("units"))
    try:
        with st.spinner(tr("loading")):
            models, calibrators, columns, versions = _load_models()
            frame, sample = _load_dataframe()
            feature_matrix(frame, columns)
        if frame.empty:
            st.error(tr("empty"))
            return
    except (OSError, ValueError, TypeError, ImportError, AttributeError, KeyError, EOFError, pickle.UnpicklingError):
        st.error(tr("unavailable"))
        return
    st.info(tr("sample", days=frame.date.nunique(), cells=frame.grid_id.nunique()) if sample else tr("full", days=frame.date.nunique()))
    tabs = st.tabs([tr(key) for key in ["map_tab", "rank_tab", "shap_tab", "drift_tab", "about_tab"]])
    try:
        with tabs[0]:
            tab_map(frame, models, calibrators, columns, versions)
        with tabs[1]:
            tab_ranking(frame, models, calibrators, columns, versions)
        with tabs[2]:
            tab_shap(frame, models, calibrators, columns)
        with tabs[3]:
            tab_drift()
        with tabs[4]:
            tab_about(versions)
    except (ValueError, TypeError, KeyError):
        st.error(tr("data_error"))


if __name__ == "__main__":
    main()
