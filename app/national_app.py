"""Bilingual readiness explorer, distinct from the preserved MT replay dashboard."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from api.national import coverage, national_boundaries, state_readiness
from src.geo.uf_registry import UF_BY_CODE

TEXT = {
    "pt-BR": {
        "title": "Brasil · Expansão nacional de pesquisa",
        "warning": "Em desenvolvimento: ainda não há modelo, probabilidades ou métricas nacionais validados. Não é um sistema operacional de alerta.",
        "scope": "O cadastro de 27 UFs não comprova cobertura geográfica nem capacidade preditiva. O piloto histórico de Mato Grosso permanece separado.",
        "region": "Macrorregião", "all": "Todas", "state": "UF",
        "stages": "Evidências disponíveis por UF", "registered": "Cadastro oficial",
        "geometry_available": "Geometria verificada", "grid_created": "Grade criada",
        "valid_fire_data": "Dados de focos válidos", "valid_climate_data": "Clima válido",
        "features_computed": "Features calculadas", "model_applicable": "Modelo aplicável",
        "metrics_calculated": "Métricas calculadas", "yes": "Disponível", "no": "Pendente",
        "missing": "Período, células, probabilidade e desempenho nacionais: indisponíveis. Dados reais e validação científica ainda são necessários.",
        "resolution": "Resoluções em estudo: 0,5° e 0,25°. Uma grade mais fina não torna a meteorologia mais precisa; não há alegação de previsão intraurbana no DF.",
        "code": "Código IBGE", "name": "Nome oficial", "abbr": "Sigla",
        "map": "Mostrar limite oficial da UF",
        "map_caption": "Malha IBGE 2024; simplificação somente para exibição. Este mapa mostra geografia, sem probabilidades ou modelo nacional.",
    },
    "en": {
        "title": "Brazil · National Research Expansion",
        "warning": "In development: no validated national model, probabilities or metrics are available. This is not an operational warning system.",
        "scope": "A registry of 27 federative units does not establish geographic or predictive coverage. The historical Mato Grosso pilot remains separate.",
        "region": "Macroregion", "all": "All", "state": "Federative unit",
        "stages": "Available evidence by federative unit", "registered": "Official registry",
        "geometry_available": "Verified geometry", "grid_created": "Grid created",
        "valid_fire_data": "Valid hotspot data", "valid_climate_data": "Valid climate data",
        "features_computed": "Features computed", "model_applicable": "Applicable model",
        "metrics_calculated": "Metrics calculated", "yes": "Available", "no": "Pending",
        "missing": "National period, spatial units, probability and performance: unavailable. Real data and scientific validation remain necessary.",
        "resolution": "Resolutions under study: 0.5° and 0.25°. A finer grid does not improve meteorological resolution; there is no claim of intraurban prediction for DF.",
        "code": "IBGE code", "name": "Official name", "abbr": "Abbreviation",
        "map": "Show official state boundary",
        "map_caption": "IBGE 2024 boundaries; simplified for display only. This map shows geography, without national probabilities or a model.",
    },
}


def main():
    st.set_page_config(page_title="Brazil National Research Expansion", layout="wide")
    if "national_language" not in st.session_state:
        requested = st.query_params.get("lang", "pt-BR")
        st.session_state.national_language = requested if requested in TEXT else "pt-BR"
    language = st.sidebar.selectbox("Idioma / Language", list(TEXT), key="national_language")
    text = TEXT[language]
    st.title(text["title"])
    st.warning(text["warning"])
    st.write(text["scope"])
    states = coverage()["states"]
    regions = {row["region_code"]: row["region_name"] for row in states}
    region = st.sidebar.selectbox(text["region"], ["all", *sorted(regions)],
                                  format_func=lambda value: text["all"] if value == "all" else regions[value],
                                  key="national_region")
    eligible = [row for row in states if region == "all" or row["region_code"] == region]
    code = st.sidebar.selectbox(text["state"], [row["uf_code"] for row in eligible],
                                format_func=lambda value: f"{UF_BY_CODE[value].abbreviation} · {UF_BY_CODE[value].name}",
                                key="national_uf")
    selected = state_readiness(code)
    st.subheader(f"{selected['abbreviation']} · {selected['uf_name']} ({code})")
    st.info(text["missing"])
    st.caption(text["resolution"])
    if selected["geometry_available"] and st.checkbox(text["map"], key="national_show_map"):
        import folium

        polygon = national_boundaries()[code].simplify(0.025, preserve_topology=True)
        point = polygon.representative_point()
        state_map = folium.Map(location=[point.y, point.x], zoom_start=6, tiles=None)
        folium.GeoJson(polygon.__geo_interface__, name=selected["uf_name"]).add_to(state_map)
        west, south, east, north = polygon.bounds
        state_map.fit_bounds([[south, west], [north, east]])
        st_folium(state_map, height=420, use_container_width=True, returned_objects=[],
                  key=f"national_geography_{code}")
        st.caption(text["map_caption"])
    stages = ["registered", "geometry_available", "grid_created", "valid_fire_data",
              "valid_climate_data", "features_computed", "model_applicable", "metrics_calculated"]
    table = pd.DataFrame([{text["code"]: row["uf_code"], text["abbr"]: row["abbreviation"],
                           text["name"]: row["uf_name"],
                           **{text[key]: text["yes"] if row[key] else text["no"] for key in stages}}
                          for row in eligible])
    st.subheader(text["stages"])
    st.dataframe(table, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
