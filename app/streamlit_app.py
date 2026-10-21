"""Streamlit app for interactive wildfire risk visualization.

Features:
- Interactive map showing fire risk by grid cell (Folium).
- Date filter to view risk on different days.
- Summary statistics and charts.
"""

import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

import folium
import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(
    page_title="🔥 Brazil Wildfire Risk Forecast",
    page_icon="🔥",
    layout="wide",
)


@st.cache_data
def load_data(horizon: int = 7):
    """Load the features dataset with predictions for chosen horizon."""
    feat_path = _PROJECT_ROOT / "data" / "processed" / "features.parquet"
    is_sample = False
    if not feat_path.exists():
        feat_path = _PROJECT_ROOT / "data" / "sample" / "features_sample.parquet"
        is_sample = True
    if not feat_path.exists():
        return None, False

    df = pd.read_parquet(feat_path)
    df["date"] = pd.to_datetime(df["date"])

    # Load model and calibrator for chosen horizon
    if horizon == 1 and (_PROJECT_ROOT / "models" / "lightgbm_1d.joblib").exists():
        model_path = _PROJECT_ROOT / "models" / "lightgbm_1d.joblib"
        calibrator_path = _PROJECT_ROOT / "models" / "platt_calibrator_1d.joblib"
    elif horizon == 3 and (_PROJECT_ROOT / "models" / "lightgbm_3d.joblib").exists():
        model_path = _PROJECT_ROOT / "models" / "lightgbm_3d.joblib"
        calibrator_path = _PROJECT_ROOT / "models" / "platt_calibrator_3d.joblib"
    else:
        model_path = _PROJECT_ROOT / "models" / "lightgbm_model.joblib"
        calibrator_path = _PROJECT_ROOT / "models" / "platt_calibrator.joblib"

    feature_cols_path = _PROJECT_ROOT / "models" / "feature_cols.joblib"

    if model_path.exists() and feature_cols_path.exists():
        model = joblib.load(model_path)
        feature_cols = joblib.load(feature_cols_path)
        X = df[feature_cols].values.astype(np.float32)
        X = np.nan_to_num(X, nan=0.0)
        raw_probs = model.predict_proba(X)[:, 1]

        if calibrator_path.exists():
            from scipy.special import logit
            calibrator = joblib.load(calibrator_path)
            raw_logit = logit(np.clip(raw_probs, 1e-6, 1 - 1e-6)).reshape(-1, 1)
            df["probability"] = calibrator.predict_proba(raw_logit)[:, 1]
        else:
            df["probability"] = raw_probs

        df["risk_level"] = df["probability"].apply(
            lambda p: "High" if p >= 0.5 else ("Medium" if p >= 0.2 else "Low")
        )
    return df, is_sample


@st.cache_data
def load_metrics():
    """Load model comparison results."""
    path = _PROJECT_ROOT / "reports" / "model_comparison.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


def create_risk_map(df_day: pd.DataFrame) -> folium.Map:
    """Create a Folium map with risk-colored grid cells."""
    center_lat = df_day["lat_center"].mean()
    center_lon = df_day["lon_center"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="OpenStreetMap")

    color_map = {"Low": "green", "Medium": "orange", "High": "red"}

    for _, row in df_day.iterrows():
        color = color_map.get(row.get("risk_level", "Low"), "gray")
        prob = row.get("probability", 0)

        folium.CircleMarker(
            location=[row["lat_center"], row["lon_center"]],
            radius=6,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.6,
            popup=f"Grid: {row['grid_id']}<br>Risk: {row.get('risk_level', 'N/A')}<br>Prob: {prob:.1%}",
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
                background: white; padding: 10px; border-radius: 5px;
                border: 1px solid grey; font-size: 14px;">
        <b>Fire Risk</b><br>
        🟢 Low (&lt;30%)<br>
        🟠 Medium (30-60%)<br>
        🔴 High (&gt;60%)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    st.title("🔥 Brazil Wildfire Risk Forecast")
    st.markdown(
        "Interactive wildfire risk map for **Mato Grosso, Brazil**. "
        "Predictions use a LightGBM model trained on INPE fire data and NASA POWER climate data."
    )

    # Sidebar
    st.sidebar.header("Forecast Horizon & Filters")

    horizon = st.sidebar.radio(
        "Forecast Horizon",
        options=[7, 3, 1],
        format_func=lambda h: f"{h} days ({'Tactical Weekly' if h==7 else ('72h Short-Term' if h==3 else '24h Immediate')})",
        index=0,
    )

    df, is_sample = load_data(horizon=horizon)
    if df is None:
        st.error("No data found. Please run the data pipeline first (`make all`).")
        return

    if is_sample:
        st.info("💡 Running in demo mode with sample data (`data/sample/`). For the full 10-year dataset, execute `make all`.")

    available_dates = sorted(df["date"].dt.date.unique())
    # Default to a date in fire season
    default_idx = len(available_dates) * 3 // 4  # roughly Sep of last year
    selected_date = st.sidebar.date_input(
        "Select date",
        value=available_dates[min(default_idx, len(available_dates) - 1)],
        min_value=available_dates[0],
        max_value=available_dates[-1],
    )

    risk_filter = st.sidebar.multiselect(
        "Risk levels",
        ["Low", "Medium", "High"],
        default=["Low", "Medium", "High"],
    )

    # Filter data
    df_day = df[df["date"].dt.date == selected_date].copy()
    if "risk_level" in df_day.columns:
        df_day = df_day[df_day["risk_level"].isin(risk_filter)]

    # Main content
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Cells", len(df_day))
    with col2:
        high_risk = len(df_day[df_day.get("risk_level", pd.Series()) == "High"]) if "risk_level" in df_day.columns else 0
        st.metric("High Risk Cells", high_risk)
    with col3:
        medium_risk = len(df_day[df_day.get("risk_level", pd.Series()) == "Medium"]) if "risk_level" in df_day.columns else 0
        st.metric("Medium Risk Cells", medium_risk)
    with col4:
        if "probability" in df_day.columns:
            st.metric("Avg Probability", f"{df_day['probability'].mean():.1%}")

    # Map
    st.subheader(f"Risk Map — {selected_date}")
    if len(df_day) > 0:
        risk_map = create_risk_map(df_day)
        st_folium(risk_map, width=900, height=500)
    else:
        st.warning("No data for selected date and filters.")

    # Charts
    st.subheader("Risk Distribution")
    if "probability" in df_day.columns and len(df_day) > 0:
        fig = px.histogram(
            df_day, x="probability", nbins=30,
            labels={"probability": "Fire Probability"},
            title=f"Probability Distribution — {selected_date}",
            color_discrete_sequence=["#e74c3c"],
        )
        st.plotly_chart(fig, use_container_width=True)

    # Monthly trend
    st.subheader("Monthly Fire Risk Trend")
    if "probability" in df.columns:
        monthly = df.groupby(df["date"].dt.to_period("M")).agg(
            avg_prob=("probability", "mean"),
            high_risk_cells=("risk_level", lambda x: (x == "High").sum()),
        ).reset_index()
        monthly["date"] = monthly["date"].dt.to_timestamp()

        fig2 = px.line(
            monthly, x="date", y="avg_prob",
            labels={"date": "Month", "avg_prob": "Avg Probability"},
            title="Average Fire Risk Over Time",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Model comparison
    st.subheader("Model Comparison")
    metrics_df = load_metrics()
    if metrics_df is not None:
        st.dataframe(metrics_df, use_container_width=True)
    else:
        st.info("No model comparison data available yet.")

    # Footer
    st.markdown("---")
    st.markdown(
        "**Data sources:** INPE Programa Queimadas (fire hotspots) • NASA POWER (climate) | "
        "**Author:** [Eduardo Tostes](https://github.com/EduardoTostesC)"
    )


if __name__ == "__main__":
    main()

