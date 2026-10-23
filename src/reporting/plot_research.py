"""Export scientific figures from current result CSVs, without retraining."""

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import get_project_root


def main():
    root = get_project_root()
    folder = root / "reports/research"
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    selected = pd.read_csv(folder / "no_recent_fire.csv")
    selected = selected[(selected["group"] == "all") & (selected.subset == "no_local_30d") & selected.model.isin(["LightGBM", "Climatology", "Simple logistic (Platt)"])]
    axes[0].bar(["LightGBM", "Climatology", "Logistic"], selected.AP, color=["#c74c3c", "#316b9c", "#5b8c68"])
    axes[0].set_title("No local detections in 30 days")
    axes[0].axhline(selected.prevalence.iloc[0], color="black", linestyle="--", label="Prevalence")
    axes[0].set_ylabel("Average Precision")
    axes[0].legend()
    spatial = pd.read_csv(folder / "spatial_generalization.csv")
    table = spatial[spatial.model.isin(["LightGBM", "Simple logistic (Platt)"])].pivot(index="held_region", columns="model", values="AP")
    table.plot.bar(ax=axes[1], rot=0)
    axes[1].set_title("Entire region held out, with buffer")
    axes[1].set_ylabel("Average Precision")
    axes[1].set_xlabel("Held region")
    ablation = pd.read_csv(folder / "oracle.csv")
    axes[2].bar(["Observed to D", "No weather", "ORACLE\nnon-operational"], ablation.AP, color=["#c74c3c", "#316b9c", "#a47b28"])
    axes[2].set_title("Perfect future weather experiment")
    axes[2].set_ylabel("Average Precision")
    for ax in axes:
        ax.set_ylim(0, .75)
        ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    for extension in ("png", "svg"):
        fig.savefig(root / f"reports/figures/research_summary.{extension}", dpi=160)
    plt.close(fig)
    matched = pd.read_csv(folder / "matched_lstm.csv")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(matched.model, matched.AP, color=["#9b59b6", "#8e44ad", "#3498db", "#2471a3"])
    ax.set_ylim(0, .75)
    ax.set_ylabel("Average Precision")
    ax.set_title(f"Matched retrospective comparison: {int(matched.n.iloc[0]):,} cell-days")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(root / "reports/figures/lstm_vs_lgbm.png", dpi=160)
    plt.close(fig)
    print("Current research figures exported")


if __name__ == "__main__":
    main()
