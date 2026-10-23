"""Build read-only notebooks against the current verified experiment artifacts."""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]


def main():
    imports = """from pathlib import Path
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Image
ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(ROOT))
"""
    eda = nbf.v4.new_notebook(cells=[
        nbf.v4.new_markdown_cell("# Dados retrospectivos de focos detectáveis\n\nNotebook regenerado na auditoria de 23/10/2026. Não estima incêndios independentes, área queimada ou disponibilidade operacional. Resultados antigos continuam no histórico Git. POWER legada LST e focos UTC exigem revisão de alinhamento."),
        nbf.v4.new_code_cell(imports),
        nbf.v4.new_code_cell("""grid = pd.read_csv(ROOT / 'data/processed/grid.csv')
df = pd.read_parquet(ROOT / 'data/processed/dataset.parquet')
df = df[df.grid_id.isin(grid.loc[grid.state_status != 'outside', 'grid_id'])].copy()
print('Dimensions:', df.shape, 'Cells:', df.grid_id.nunique())
print('Observed date range:', df.date.min(), df.date.max())
display(df.head())
display(df[['target_1d','target_3d','target_7d']].mean().rename('positive_cell_day_rate'))
"""),
        nbf.v4.new_markdown_cell("## Cobertura e ausência\n\nA cauda dos rótulos é truncada por exigir horizonte futuro completo. As contagens abaixo não descrevem dias descartados. Ausência de detecção não comprova ausência física de fogo."),
        nbf.v4.new_code_cell("display(df.isna().sum().rename('missing')); display(grid.groupby('state_status').size().rename('cells'))"),
        nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(13, 4))
df.groupby(df.date.dt.year).fire_count.sum().plot.bar(ax=axes[0], title='Detected hotspots in eligible date interval')
df.groupby(df.date.dt.month).fire_count.sum().plot.bar(ax=axes[1], title='Seasonal detection totals')
plt.tight_layout(); plt.show()
"""),
        nbf.v4.new_code_cell("""weather = ['T2M_MAX','T2M_MIN','RH2M','PRECTOTCORR','WS10M']
display(df.groupby('target')[weather].mean())
display(grid[['cell_area_km2','state_area_km2','state_fraction_geodesic']].describe())
"""),
        nbf.v4.new_markdown_cell("Comparações climáticas por alvo são associações. Resolução da fonte, dependência espacial, cobertura do satélite e prevalência impedem interpretação causal automática. Consulte reports/REPRODUCIBILIDADE.md e reports/CLIMA_E_ABLACAO.md.")])
    modeling = nbf.v4.new_notebook(cells=[
        nbf.v4.new_markdown_cell("# Avaliação retrospectiva e comparações verificadas\n\nNotebook somente de leitura. O ajuste ocorre nos módulos src/models. Metadados/CSVs são conferidos antes da apresentação; não há seleção de modelos usando resultados de teste. Resultados históricos estão arquivados."),
        nbf.v4.new_code_cell(imports + "from src.reporting.generate_readme_metrics import validated_tables\nmeta, frames = validated_tables(ROOT)\nprint(meta['train_period'], meta['calibration_period'], meta['test_period'])\ndisplay(frames['model_comparison.csv'])"),
        nbf.v4.new_markdown_cell("AP e PR-AUC trapezoidal são diferentes. Recall@P50 da curva é descritivo; limiares de decisão foram escolhidos em 2023. Brier não mede apenas calibração. Nenhum p-valor é inferido da fração de diferenças bootstrap não positivas."),
        nbf.v4.new_code_cell("display(frames['multi_horizon_comparison.csv']); display(frames['operational_decision_metrics.csv'])"),
        nbf.v4.new_code_cell("""yearly = pd.read_csv(ROOT / 'reports/research/yearly_prevalence.csv')
display(yearly)
display(pd.read_csv(ROOT / 'reports/walk_forward_metrics.csv'))
"""),
        nbf.v4.new_code_cell("""subsets = pd.read_csv(ROOT / 'reports/research/no_recent_fire.csv')
display(subsets[(subsets['group'] == 'all') & (subsets.subset == 'no_local_30d')])
display(pd.read_csv(ROOT / 'reports/research/spatial_generalization.csv'))
"""),
        nbf.v4.new_markdown_cell("Sem focos locais recentes, climatologia pode superar LightGBM. Uma regressão simples pode vencer em região retida. Esses resultados negativos limitam a generalização da vantagem agregada."),
        nbf.v4.new_code_cell("display(pd.read_csv(ROOT / 'reports/research/ablation.csv')); display(pd.read_csv(ROOT / 'reports/research/oracle.csv'))"),
        nbf.v4.new_markdown_cell("ORACLE utiliza meteorologia futura realmente observada e é NÃO OPERACIONAL. Não avalia a qualidade de uma previsão meteorológica arquivada. A ablação corrigida remove também precip_sum_* da configuração sem clima."),
        nbf.v4.new_code_cell("""display(pd.read_csv(ROOT / 'reports/research/matched_lstm.csv'))
details = json.loads((ROOT / 'reports/research/matched_lstm_metadata.json').read_text())
print('Matched keys and labels:', details['same_labels_and_keys_verified'])
print('Training/calibration/test:', details['training_rows'], details['calibration_rows'], details['test_rows'])
print('Paired delta AP interval:', details['paired_AP_difference']['delta_AP_95CI'])
"""),
        nbf.v4.new_code_cell("""for filename in ['calibration_curve.png', 'shap_summary.png', 'research_summary.png']:
    display(Image(filename=str(ROOT / 'reports/figures' / filename)))
"""),
        nbf.v4.new_markdown_cell("SHAP descreve contribuições à margem bruta; não decompõe a probabilidade calibrada nem identifica causalidade. Esta é uma análise retrospectiva com limitações de horários de publicação e alinhamento LST/UTC, não um sistema operacional validado.")])
    for name, notebook in [("01_eda", eda), ("02_modeling", modeling)]:
        notebook.metadata.kernelspec = {"display_name": "Wildfire audit", "language": "python", "name": "wildfire-audit"}
        nbf.write(notebook, ROOT / f"notebooks/{name}.ipynb")
        print("Refreshed", name)


if __name__ == "__main__":
    main()
