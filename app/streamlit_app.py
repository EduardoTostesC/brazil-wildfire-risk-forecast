"""Streamlit dashboard — Brazil Wildfire Risk Forecast (Block D).

Multi-tab interactive dashboard featuring:
- Tab 1: Interactive Folium risk map with horizon selector and date picker.
- Tab 2: Top-N risk cell ranking table with per-cell trend sparklines.
- Tab 3: Local SHAP explanation for any cell or map click.
- Tab 4: Drift & Model Health monitoring panel.
- Tab 5: About — data sources, methodology, and model performance.
"""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Add project root to path
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

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="🔥 Brazil Wildfire Risk Forecast",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast",
        "Report a bug": "https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/issues",
        "About": "Brazil Wildfire Risk Forecast — ML pipeline by Eduardo Tostes",
    },
)

from src.data.build_grid import build_grid
from src.models.inference import calibrated_probabilities, feature_matrix
from src.models.risk_tiers import DEFAULT_RISK_CONFIG

# ── Theme constants ───────────────────────────────────────────────────────────

RISK_COLORS = {
    "Low": DEFAULT_RISK_CONFIG.color_low,
    "Medium": DEFAULT_RISK_CONFIG.color_medium,
    "High": DEFAULT_RISK_CONFIG.color_high,
}
RISK_THRESHOLDS = {
    "Low": DEFAULT_RISK_CONFIG.low_cutoff,
    "Medium": DEFAULT_RISK_CONFIG.high_cutoff,
}

# ── Cached loaders ────────────────────────────────────────────────────────────


@st.cache_resource(show_spinner="Loading model artifacts…")
def _load_models():
    """Load LightGBM models, Platt calibrators, and feature list once."""
    models, calibrators = {}, {}
    for h in [1, 3, 7]:
        m_file = f"lightgbm_{h}d.joblib" if h != 7 else "lightgbm_model.joblib"
        c_file = f"platt_calibrator_{h}d.joblib" if h != 7 else "platt_calibrator.joblib"
        mp = _PROJECT_ROOT / "models" / m_file
        cp = _PROJECT_ROOT / "models" / c_file
        if mp.exists():
            models[h] = joblib.load(mp)
        if cp.exists():
            calibrators[h] = joblib.load(cp)
    fc_path = _PROJECT_ROOT / "models" / "feature_cols.joblib"
    feature_cols = joblib.load(fc_path) if fc_path.exists() else []
    return models, calibrators, feature_cols


@st.cache_data(show_spinner="Loading dataset…")
def _load_dataframe():
    """Load the feature dataset (full or sample fallback)."""
    full = _PROJECT_ROOT / "data" / "processed" / "features.parquet"
    sample = _PROJECT_ROOT / "data" / "sample" / "features_sample.parquet"
    is_sample = not full.exists()
    path = sample if is_sample else full
    if not path.exists():
        return None, is_sample
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    grid = build_grid()
    valid = grid.loc[grid.state_status != "outside", "grid_id"]
    df = df[df.grid_id.isin(valid)]
    df = df[df.date >= "2024-01-01"]
    return df, is_sample


def _add_predictions(df: pd.DataFrame, models, calibrators, feature_cols, horizon: int) -> pd.DataFrame:
    """Add probability and risk_level columns for a given forecast horizon."""
    model = models.get(horizon)
    calibrator = calibrators.get(horizon)
    prob = calibrated_probabilities(model, calibrator, feature_matrix(df, feature_cols))

    df = df.copy()
    df["probability"] = prob
    df["risk_level"] = np.where(
        prob >= DEFAULT_RISK_CONFIG.high_cutoff, "High",
        np.where(prob >= DEFAULT_RISK_CONFIG.low_cutoff, "Medium", "Low"),
    )
    return df


@st.cache_data(show_spinner=False)
def _load_drift_report():
    """Load drift_report.json if available."""
    import json
    path = _PROJECT_ROOT / "reports" / "drift_report.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


@st.cache_data(show_spinner=False)
def _load_comparison_csv(name: str) -> pd.DataFrame | None:
    path = _PROJECT_ROOT / "reports" / name
    if path.exists():
        return pd.read_csv(path)
    return None


# ── Map builder ───────────────────────────────────────────────────────────────


def _build_risk_map(df_day: pd.DataFrame, selected_grid: str | None = None) -> folium.Map:
    """Build a Folium choropleth-style circle marker map."""
    if df_day.empty:
        return folium.Map(location=[-12.5, -56.0], zoom_start=6)

    clat = df_day["lat_center"].mean()
    clon = df_day["lon_center"].mean()
    m = folium.Map(location=[clat, clon], zoom_start=6, tiles="CartoDB positron")

    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)

    for _, row in df_day.iterrows():
        prob = float(row.get("probability", 0))
        level = str(row.get("risk_level", "Low"))
        color = RISK_COLORS.get(level, "#95a5a6")
        is_selected = (selected_grid is not None and row["grid_id"] == selected_grid)
        radius = 9 if is_selected else 6
        weight = 3 if is_selected else 1

        folium.CircleMarker(
            location=[row["lat_center"], row["lon_center"]],
            radius=radius,
            color="#2c3e50" if is_selected else color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            weight=weight,
            tooltip=(
                f"<b>Cell {row['grid_id']}</b><br>"
                f"Risk: <b style='color:{color}'>{level}</b><br>"
                f"Probability: <b>{prob:.1%}</b><br>"
                f"Click to inspect ↗"
            ),
            popup=folium.Popup(
                f"<b>Grid:</b> {row['grid_id']}<br>"
                f"<b>Lat/Lon:</b> {row['lat_center']:.2f}°, {row['lon_center']:.2f}°<br>"
                f"<b>Risk Level:</b> {level}<br>"
                f"<b>Probability:</b> {prob:.1%}",
                max_width=220,
            ),
        ).add_to(m)

    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:12px 16px;border-radius:8px;
                border:1px solid #ccc;font-size:13px;line-height:1.6;">
        <b>🔥 Fire Risk</b><br>
        <span style="color:#27ae60">●</span> Low (&lt;{DEFAULT_RISK_CONFIG.low_cutoff:.0%})<br>
        <span style="color:#f39c12">●</span> Medium ({DEFAULT_RISK_CONFIG.low_cutoff:.0%}–{DEFAULT_RISK_CONFIG.high_cutoff:.0%})<br>
        <span style="color:#e74c3c">●</span> High (≥{DEFAULT_RISK_CONFIG.high_cutoff:.0%})
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    return m


# ── Tab 1: Risk Map ───────────────────────────────────────────────────────────


def tab_risk_map(df: pd.DataFrame, is_sample: bool, models, calibrators, feature_cols):
    st.markdown("### 🗺️ Wildfire Risk Map — Mato Grosso")
    if is_sample:
        st.info(
            "💡 **Demo mode** — running on sample data (`data/sample/`). "
            "For the full 10-year dataset, run `make all` in the project root."
        )

    # Sidebar controls
    horizon = st.sidebar.radio(
        "⏱ Forecast Horizon",
        options=[7, 3, 1],
        format_func=lambda h: {7: "7-day (Weekly)", 3: "3-day (72h)", 1: "1-day (24h)"}[h],
        index=0,
    )

    available_dates = sorted(df["date"].dt.date.unique())
    default_idx = min(len(available_dates) * 3 // 4, len(available_dates) - 1)
    selected_date = st.sidebar.date_input(
        "📅 Date",
        value=available_dates[default_idx],
        min_value=available_dates[0],
        max_value=available_dates[-1],
    )

    risk_filter = st.sidebar.multiselect(
        "🎯 Risk Levels",
        ["Low", "Medium", "High"],
        default=["Low", "Medium", "High"],
    )

    df_day = _add_predictions(df[df["date"].dt.date == selected_date], models, calibrators, feature_cols, horizon)
    if risk_filter and "risk_level" in df_day.columns:
        df_day = df_day[df_day["risk_level"].isin(risk_filter)]

    # KPI row
    total = len(df_day)
    n_high = int((df_day["risk_level"] == "High").sum()) if "risk_level" in df_day.columns else 0
    n_med = int((df_day["risk_level"] == "Medium").sum()) if "risk_level" in df_day.columns else 0
    avg_prob = float(df_day["probability"].mean()) if "probability" in df_day.columns else 0.0
    max_prob = float(df_day["probability"].max()) if "probability" in df_day.columns else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📍 Cells Shown", f"{total:,}")
    c2.metric("🔴 High Risk", f"{n_high:,}", delta=None)
    c3.metric("🟠 Medium Risk", f"{n_med:,}")
    c4.metric("📊 Avg Probability", f"{avg_prob:.1%}")
    c5.metric("⚠️ Max Probability", f"{max_prob:.1%}")

    # Map
    st.markdown(f"**Horizon:** `{horizon}-day` | **Date:** `{selected_date}`")
    if not df_day.empty:
        risk_map = _build_risk_map(df_day)
        map_data = st_folium(risk_map, width="100%", height=500, key=f"map_{horizon}_{selected_date}")
        # Show clicked cell info
        if map_data and map_data.get("last_object_clicked_tooltip"):
            with st.expander("📌 Last clicked cell info", expanded=True):
                st.markdown(map_data["last_object_clicked_tooltip"], unsafe_allow_html=True)
    else:
        st.warning("No data for the selected date and risk filters.")

    # Probability distribution histogram
    if "probability" in df_day.columns and not df_day.empty:
        with st.expander("📊 Probability Distribution", expanded=False):
            fig = px.histogram(
                df_day, x="probability", nbins=40,
                color="risk_level",
                color_discrete_map=RISK_COLORS,
                category_orders={"risk_level": ["Low", "Medium", "High"]},
                labels={"probability": "Fire Probability", "risk_level": "Risk Level"},
                title=f"Cell Probability Distribution — {selected_date}",
                opacity=0.85,
            )
            fig.update_layout(bargap=0.05, legend_title_text="Risk Level")
            st.plotly_chart(fig, use_container_width=True)


# ── Tab 2: Risk Ranking ───────────────────────────────────────────────────────


def tab_ranking(df: pd.DataFrame, models, calibrators, feature_cols):
    st.markdown("### 🏆 Highest-Risk Cell Ranking")
    st.markdown(
        "Top cells by mean fire probability across the **test period (2024–2025)**. "
        "Cells ranked highest signal persistent structural risk (vegetation, chronic drought, ignition history)."
    )

    horizon = st.selectbox(
        "Forecast Horizon", [7, 3, 1],
        format_func=lambda h: {7: "7-day", 3: "3-day", 1: "1-day"}[h],
        key="ranking_horizon",
    )
    top_n = st.slider("Top N cells", 10, 50, 20, 5, key="ranking_n")

    df_pred = _add_predictions(df, models, calibrators, feature_cols, horizon)

    # Aggregate: mean prob and % high-risk days per cell
    agg = (
        df_pred.groupby("grid_id")
        .agg(
            lat=("lat_center", "first"),
            lon=("lon_center", "first"),
            mean_prob=("probability", "mean"),
            max_prob=("probability", "max"),
            pct_high=("risk_level", lambda x: (x == "High").mean() * 100),
            pct_medium=("risk_level", lambda x: (x == "Medium").mean() * 100),
            n_obs=("probability", "count"),
        )
        .sort_values("mean_prob", ascending=False)
        .reset_index()
        .head(top_n)
    )
    agg["rank"] = range(1, len(agg) + 1)

    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown("#### 📋 Ranking Table")
        display = agg[["rank", "grid_id", "lat", "lon", "mean_prob", "max_prob", "pct_high", "pct_medium"]].copy()
        display.columns = ["Rank", "Cell ID", "Lat", "Lon", "Mean Prob", "Max Prob", "% High-Risk Days", "% Medium-Risk Days"]
        display["Mean Prob"] = display["Mean Prob"].map("{:.1%}".format)
        display["Max Prob"] = display["Max Prob"].map("{:.1%}".format)
        display["% High-Risk Days"] = display["% High-Risk Days"].map("{:.1f}%".format)
        display["% Medium-Risk Days"] = display["% Medium-Risk Days"].map("{:.1f}%".format)
        display["Lat"] = display["Lat"].map("{:.2f}°".format)
        display["Lon"] = display["Lon"].map("{:.2f}°".format)
        st.dataframe(display, use_container_width=True, height=min(450, top_n * 38))

    with c2:
        st.markdown("#### 📍 Top Cells on Map")
        m = folium.Map(
            location=[agg["lat"].mean(), agg["lon"].mean()],
            zoom_start=6, tiles="CartoDB positron",
        )
        for i, row in agg.iterrows():
            prob = float(row["mean_prob"])
            level = "High" if prob >= RISK_THRESHOLDS["Medium"] else "Medium" if prob >= RISK_THRESHOLDS["Low"] else "Low"
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=8,
                color=RISK_COLORS[level],
                fill=True,
                fill_color=RISK_COLORS[level],
                fill_opacity=0.8,
                tooltip=f"<b>#{row['rank']} {row['grid_id']}</b><br>Mean: {prob:.1%}",
            ).add_to(m)
        st_folium(m, width="100%", height=380, key="ranking_map")

    # Bar chart
    st.markdown("#### 📊 Mean Probability by Rank")
    agg_plot = agg.copy()
    agg_plot["color"] = agg_plot["mean_prob"].apply(
        lambda p: "High" if p >= RISK_THRESHOLDS["Medium"] else "Medium" if p >= RISK_THRESHOLDS["Low"] else "Low"
    )
    fig = px.bar(
        agg_plot, x="grid_id", y="mean_prob",
        color="color",
        color_discrete_map=RISK_COLORS,
        category_orders={"color": ["High", "Medium", "Low"]},
        labels={"grid_id": "Cell ID", "mean_prob": "Mean Fire Probability", "color": "Risk"},
        title=f"Top {top_n} Cells by Mean Fire Probability ({horizon}-Day Horizon)",
    )
    fig.update_layout(xaxis_tickangle=-45, showlegend=True)
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

    # Monthly trend for top cell
    top_cell = agg.iloc[0]["grid_id"]
    st.markdown(f"#### 📈 Monthly Risk Trend — Top Cell `{top_cell}`")
    df_cell = df_pred[df_pred["grid_id"] == top_cell].copy()
    if not df_cell.empty:
        monthly = (
            df_cell.set_index("date")
            .resample("ME")["probability"]
            .mean()
            .reset_index()
        )
        monthly.columns = ["Month", "Avg Probability"]
        fig2 = px.line(
            monthly, x="Month", y="Avg Probability",
            markers=True,
            title=f"Monthly Average Risk — Cell {top_cell}",
            color_discrete_sequence=["#e74c3c"],
        )
        fig2.update_yaxes(tickformat=".0%")
        fig2.add_hrect(y0=RISK_THRESHOLDS["Medium"], y1=1.0, fillcolor="#e74c3c", opacity=0.07, line_width=0)
        fig2.add_hrect(y0=RISK_THRESHOLDS["Low"], y1=RISK_THRESHOLDS["Medium"], fillcolor="#f39c12", opacity=0.07, line_width=0)
        st.plotly_chart(fig2, use_container_width=True)


# ── Tab 3: Local SHAP Explanation ────────────────────────────────────────────


def tab_shap(df: pd.DataFrame, models, calibrators, feature_cols):
    import shap

    st.markdown("### 🔍 Local SHAP Explanation — Why this cell is at risk?")
    st.markdown(
        "Select any grid cell to see which variables are **pushing the fire probability up or down** "
        "for a specific date. SHAP (SHapley Additive exPlanations) distributes the model's output "
        "fairly among all features using cooperative game theory."
    )

    model = models.get(7)
    if model is None:
        st.error("7-day model not found. Run `make train` first.")
        return

    # Controls
    col1, col2 = st.columns(2)
    with col1:
        available_cells = sorted(df["grid_id"].unique())
        sel_cell = st.selectbox("📍 Grid Cell", available_cells, index=0, key="shap_cell")
    with col2:
        available_dates = sorted(df["date"].dt.date.unique())
        default_idx = min(len(available_dates) * 3 // 4, len(available_dates) - 1)
        sel_date = st.date_input(
            "📅 Date", value=available_dates[default_idx],
            min_value=available_dates[0], max_value=available_dates[-1],
            key="shap_date",
        )

    mask = (df["grid_id"] == sel_cell) & (df["date"].dt.date == sel_date)
    row_df = df[mask]

    if row_df.empty:
        st.warning(f"No exact historical record for {sel_cell} on {sel_date}.")
        return

    # Feature vector for this row
    X_row = feature_matrix(row_df, feature_cols)

    with st.spinner("Computing SHAP values…"):
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_row)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]  # positive class for LightGBM
        sv = shap_vals[0]  # shape (n_features,)

    calibrator = calibrators.get(7)
    prob = float(calibrated_probabilities(model, calibrator, X_row)[0])
    st.caption("SHAP explains raw model log-odds before Platt calibration. It does not decompose the calibrated probability or establish causality.")
    level = "High" if prob >= RISK_THRESHOLDS["Medium"] else "Medium" if prob >= RISK_THRESHOLDS["Low"] else "Low"

    # Summary metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("🔥 Fire Probability", f"{prob:.1%}")
    c2.metric("📊 Risk Level", level, delta=None)
    c3.metric("📍 Cell", sel_cell)

    # SHAP waterfall chart (plotly — no matplotlib dependency in Streamlit)
    shap_df = pd.DataFrame({"feature": feature_cols, "shap_value": sv, "feature_value": X_row[0]})
    shap_df["abs_shap"] = shap_df["shap_value"].abs()
    shap_df = shap_df.sort_values("abs_shap", ascending=False).head(15)
    shap_df["direction"] = shap_df["shap_value"].apply(lambda v: "↑ Increases Risk" if v > 0 else "↓ Reduces Risk")
    shap_df["color"] = shap_df["shap_value"].apply(lambda v: "#e74c3c" if v > 0 else "#2980b9")
    shap_df["label"] = shap_df.apply(
        lambda r: f"{r['feature']}<br><small>val={r['feature_value']:.2f}</small>", axis=1
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=shap_df["label"].tolist()[::-1],
        x=shap_df["shap_value"].tolist()[::-1],
        orientation="h",
        marker_color=shap_df["color"].tolist()[::-1],
        text=[f"{v:+.3f}" for v in shap_df["shap_value"].tolist()[::-1]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>SHAP: %{x:+.4f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="#7f8c8d", line_width=1)
    fig.update_layout(
        title=f"Top 15 SHAP Feature Contributions<br><sup>Cell {sel_cell} — Probability: {prob:.1%} ({level})</sup>",
        xaxis_title="SHAP Value (impact on log-odds)",
        yaxis_title="",
        height=500,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_size=12,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Feature value table for context
    with st.expander("📋 Full Feature Values for This Cell/Date", expanded=False):
        feat_table = pd.DataFrame({
            "Feature": feature_cols,
            "Value": X_row[0],
            "SHAP": sv,
        }).sort_values("SHAP", key=abs, ascending=False)
        feat_table["SHAP"] = feat_table["SHAP"].map("{:+.4f}".format)
        feat_table["Value"] = feat_table["Value"].map("{:.4f}".format)
        st.dataframe(feat_table, use_container_width=True)

    # SHAP interpretation guide
    with st.expander("ℹ️ How to read SHAP values"):
        st.markdown("""
**SHAP (SHapley Additive exPlanations)** fairly allocates each feature's contribution to the model output.

| SHAP value | Meaning |
|---|---|
| **Positive** 🔴 | This feature value **increases** the predicted fire probability for this cell/date |
| **Negative** 🔵 | This feature value **decreases** the predicted fire probability for this cell/date |
| **Magnitude** | Larger absolute value = stronger influence |

**Example:** if `dry_days = 25` has SHAP = +0.15, it means the long dry spell is pushing
the probability up by approximately +0.15 log-odds relative to the model baseline.
        """)


# ── Tab 4: Drift & Health ─────────────────────────────────────────────────────


def tab_drift():
    st.markdown("### 🩺 Model & Data Health Dashboard")
    st.markdown(
        "Monitors whether the climatological input distributions in the **operational period (2024–2025)** "
        "have shifted relative to the **training baseline (2016–2023)**. "
        "Significant drift signals that retraining may be needed."
    )

    drift = _load_drift_report()

    if drift is None:
        st.warning("Drift report not found. Run `python -m src.monitoring.drift_detector` to generate it.")
        return

    summary = drift.get("summary", {})
    features = drift.get("features", [])

    # Health KPIs
    total = summary.get("total_monitored", 0)
    stable = summary.get("stable_count", 0)
    moderate = summary.get("moderate_drift_count", 0)
    critical = summary.get("critical_drift_count", 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔵 Features Monitored", total)
    c2.metric("✅ Stable", stable, delta=None)
    c3.metric("⚠️ Moderate Drift", moderate)
    c4.metric("🚨 Critical Drift", critical, delta=None)

    if critical > 0:
        st.error(f"🚨 {critical} feature(s) with critical drift detected. Retraining is recommended.")
    elif moderate > 0:
        st.warning(f"⚠️ {moderate} feature(s) with moderate drift. Monitor closely and consider retraining.")
    else:
        st.success("✅ All monitored features are within stable distribution bounds.")

    # Comparison metadata
    st.markdown(
        f"**Baseline:** `{drift.get('baseline_period', '2016–2023')}` "
        f"— {drift.get('baseline_samples', 0):,} samples  \n"
        f"**Operational:** `{drift.get('current_period', '2024–2025')}` "
        f"— {drift.get('current_samples', 0):,} samples"
    )

    # PSI bar chart
    feat_df = pd.DataFrame(features)
    if not feat_df.empty:
        feat_df["color"] = feat_df["status"].map({
            "STABLE": "#27ae60",
            "MODERATE_DRIFT": "#f39c12",
            "CRITICAL_DRIFT": "#e74c3c",
        }).fillna("#95a5a6")

        fig = px.bar(
            feat_df.sort_values("PSI", ascending=False),
            x="feature", y="PSI",
            color="status",
            color_discrete_map={
                "STABLE": "#27ae60",
                "MODERATE_DRIFT": "#f39c12",
                "CRITICAL_DRIFT": "#e74c3c",
            },
            text="PSI",
            labels={"feature": "Feature", "PSI": "Population Stability Index (PSI)", "status": "Status"},
            title="Feature Distribution Drift — Population Stability Index (PSI)",
        )
        fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
        fig.add_hline(y=0.10, line_dash="dot", line_color="#f39c12", annotation_text="Moderate drift (0.10)")
        fig.add_hline(y=0.25, line_dash="dash", line_color="#e74c3c", annotation_text="Critical drift (0.25)")
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

        # Mean comparison table
        st.markdown("#### 📊 Feature Mean Shift (Training → Operational)")
        shift_df = feat_df[["feature", "baseline_mean", "current_mean", "PSI", "KS_statistic", "KS_pvalue", "status"]].copy()
        shift_df["mean_delta"] = shift_df["current_mean"] - shift_df["baseline_mean"]
        shift_df["mean_delta_pct"] = (shift_df["mean_delta"] / shift_df["baseline_mean"].abs().replace(0, 1)) * 100
        shift_df.columns = ["Feature", "Baseline Mean", "Operational Mean", "PSI", "KS Stat", "KS p-value", "Status", "Δ Mean", "Δ %"]
        st.dataframe(
            shift_df.style.format({
                "Baseline Mean": "{:.3f}", "Operational Mean": "{:.3f}",
                "PSI": "{:.4f}", "KS Stat": "{:.4f}", "KS p-value": "{:.2e}",
                "Δ Mean": "{:+.3f}", "Δ %": "{:+.1f}%",
            }),
            use_container_width=True,
        )

    # Walk-forward validation stability
    wf = _load_comparison_csv("walk_forward_metrics.csv")
    if wf is not None:
        st.markdown("#### 📈 Model Stability — Walk-Forward Expanding Window")
        st.markdown(
            "Each year is used as the test set, with all prior years for training. "
            "Stable PR-AUC across years indicates the model generalises well over time."
        )
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=wf["test_year"], y=wf["PR-AUC"],
            mode="lines+markers", name="PR-AUC",
            line=dict(color="#e74c3c", width=2),
            marker=dict(size=8),
        ))
        fig2.add_trace(go.Scatter(
            x=wf["test_year"], y=wf["ROC-AUC"],
            mode="lines+markers", name="ROC-AUC",
            line=dict(color="#3498db", width=2),
            marker=dict(size=8),
        ))
        fig2.update_layout(
            title="Walk-Forward Temporal Validation (Expanding Window)",
            xaxis_title="Test Year",
            yaxis_title="Metric",
            yaxis_range=[0.4, 1.0],
            legend_title="Metric",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Drift figure
    drift_fig_path = _PROJECT_ROOT / "reports" / "figures" / "drift_summary.png"
    if drift_fig_path.exists():
        with st.expander("🖼️ Drift Summary Chart", expanded=False):
            st.image(str(drift_fig_path), caption="Feature Distribution Drift (PSI + KS Test)", use_container_width=True)


# ── Tab 5: About ──────────────────────────────────────────────────────────────


def tab_about():
    st.markdown("### ℹ️ About This Project")

    # Model performance
    comp = _load_comparison_csv("model_comparison.csv")
    horizon_comp = _load_comparison_csv("multi_horizon_comparison.csv")

    st.markdown("#### Model benchmark — retrospective evaluation; consult run metadata for dates and sample counts")
    if comp is not None:
        comp_display = comp.copy()
        for col in ["PR-AUC", "ROC-AUC", "Brier", "Recall@P50"]:
            if col in comp_display.columns:
                comp_display[col] = comp_display[col].map("{:.4f}".format)
        st.dataframe(comp_display, use_container_width=True, hide_index=True)
    else:
        st.info("Run `make train` to generate the model comparison report.")

    if horizon_comp is not None:
        st.markdown("#### ⏱️ Multi-Horizon Performance")
        st.dataframe(horizon_comp, use_container_width=True, hide_index=True)

    # Figures
    st.markdown("#### 📈 Evaluation Charts")
    fig_cols = st.columns(2)
    figs = [
        ("calibration_curve.png", "Probability Calibration (Reliability Diagram)"),
        ("error_analysis_breakdown.png", "Retrospective evaluation by month, year and region"),
        ("shap_bar.png", "SHAP Global Feature Importance"),
        ("shap_summary.png", "SHAP Beeswarm Summary"),
    ]
    for i, (fname, caption) in enumerate(figs):
        path = _PROJECT_ROOT / "reports" / "figures" / fname
        if path.exists():
            with fig_cols[i % 2]:
                st.image(str(path), caption=caption, use_container_width=True)

    # Data sources
    st.markdown("#### 📂 Data Sources")
    st.markdown("""
| Source | Variable | Period | License |
|--------|----------|--------|---------|
| **INPE Queimadas** (AQUA_M-T satellite) | Fire hotspots | 2016–2025 | Brazilian Open Government Data |
| **NASA POWER** (MERRA-2 reanalysis) | T2M_MAX, T2M_MIN, RH2M, PRECTOTCORR, WS10M | 2016–2025 | NASA Open Data Policy |
    """)

    st.markdown("#### ⚠️ Limitations")
    st.markdown("""
1. **Cloud cover**: MODIS cannot detect fires under dense clouds.
2. **Orbital frequency**: AQUA observes each cell once/day (~1:30 PM local time).
3. **Spatial granularity**: A 0.5° cell (~56 km) indicates aggregate area risk, not a precise ignition point.
4. **Pilot scope**: Currently limited to Mato Grosso state; generalisation to other biomes requires retraining.
    """)

    st.markdown("#### 🤝 Responsible Use")
    st.warning(
        "This is an academic decision-support tool. "
        "**Do not use as a substitute for official emergency warnings** from INPE, CENSIPAM, IBAMA, or ICMBio."
    )

    st.markdown("---")
    st.markdown(
        "**Author:** [Eduardo Tostes](https://github.com/EduardoTostesC) · "
        "Information Systems undergraduate · "
        "[Repository](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast) · "
        "Distributed under [MIT License](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/blob/main/LICENSE)"
    )


# ── Main entry point ──────────────────────────────────────────────────────────


def main():
    # Custom CSS
    st.markdown("""
    <style>
    .main .block-container { padding-top: 1.5rem; }
    div[data-testid="metric-container"] > div { border-left: 3px solid #e74c3c; padding-left: 8px; }
    </style>
    """, unsafe_allow_html=True)

    st.title("🔥 Brazil Wildfire Risk Forecast")
    st.caption(
        "LightGBM + Platt Calibration · INPE fire data (2016–2025) · NASA POWER climate reanalysis · "
        "Mato Grosso · Historical replay / Análise retrospectiva"
    )

    # Load shared resources
    models, calibrators, feature_cols = _load_models()
    df, is_sample = _load_dataframe()
    st.info("Historical replay / Replay histórico: observed daily data; historical publication times are unknown. Operational forecasts are unavailable. Visual risk tiers are conventions, not validated action thresholds.")
    if set(models) != {1, 3, 7} or set(calibrators) != {1, 3, 7} or not feature_cols:
        st.error("Required model/calibrator pairs are unavailable.")
        return

    if df is None:
        st.error("❌ No data found. Please run: `make all` to download and process the full dataset.")
        st.code("make all  # or: make data && make features && make train")
        return

    # Tab layout
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Risk Map",
        "🏆 Cell Ranking",
        "🔍 SHAP Explanation",
        "🩺 Model Health",
        "ℹ️ About",
    ])

    with tab1:
        tab_risk_map(df, is_sample, models, calibrators, feature_cols)

    with tab2:
        tab_ranking(df, models, calibrators, feature_cols)

    with tab3:
        tab_shap(df, models, calibrators, feature_cols)

    with tab4:
        tab_drift()

    with tab5:
        tab_about()


if __name__ == "__main__":
    main()
