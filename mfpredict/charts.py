import io
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.artist
import seaborn as sns
from matplotlib.figure import Figure

from .config import CAT_COLORS, SEQ_COLOR, INCLUDE_CONTROL_IN_HEATMAP

# Configure matplotlib for web use
sns.set(style="whitegrid")
matplotlib.rcParams["figure.facecolor"] = "white"
matplotlib.rcParams["axes.facecolor"] = "white"


@dataclass
class ChartImage:
    key: str
    title: str
    png: bytes


def error_heatmap(score) -> Figure:
    """Prediction Error Heatmap (APE + bias direction) - Visualization 1."""
    avg_bias = score.signed_error_df.mean(axis=1)
    avg_ape = score.results_df["Average_APE"]

    plot_data = score.signed_error_df.copy()
    plot_data["Average APE"] = avg_ape * np.sign(avg_bias)

    annot_data = score.signed_error_df.copy()
    annot_data["Average APE"] = avg_ape

    cols = ["Average APE"] + list(score.signed_error_df.columns)
    plot_data = plot_data[cols]
    annot_data = annot_data[cols]

    n_people = len(plot_data)
    fig_height = max(10, 0.3 * n_people + 5)

    fig = Figure(figsize=(14, fig_height))
    ax = fig.add_subplot(111)

    sns.heatmap(
        plot_data, annot=annot_data, fmt=".1%", cmap="RdBu_r", center=0,
        vmin=-0.5, vmax=0.5,
        cbar_kws={"label": "Error Direction (Red=Over, Blue=Under) | Average Col shows APE magnitude"},
        linewidths=0.5, annot_kws={"size": 8},
        ax=ax,
    )
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    matplotlib.artist.setp(ax.get_xticklabels(), rotation=35, ha="left", rotation_mode="anchor")
    ax.set_title(
        "Prediction Error Heatmap: How Far Off Was Everyone?\n"
        "(First Col: Text = Avg APE, Color = Bias Direction)",
        fontsize=16, pad=55,
    )
    ax.set_xlabel("Asset")
    ax.set_ylabel("Participant")
    fig.tight_layout()

    return fig


def rank_heatmap(score, include_control: bool = INCLUDE_CONTROL_IN_HEATMAP) -> Figure:
    """Ranking Heatmap sorted by standings - Visualization 2."""
    use_full_field = include_control and "CONTROL" in score.results_df.index
    heatmap_rankings_df = (score.full_rankings_df if use_full_field else score.rankings_df).copy()

    heatmap_rankings_df["Sum_Ranks"] = heatmap_rankings_df.sum(axis=1)
    heatmap_rankings_df.sort_values("Sum_Ranks", ascending=True, inplace=True)

    AGG_COL = "Avg Rank / Signed Err"
    rankings_plot = heatmap_rankings_df.drop(columns=["Sum_Ranks"])
    rankings_plot[AGG_COL] = rankings_plot.mean(axis=1)
    annot_cols = [AGG_COL] + [c for c in rankings_plot.columns if c != AGG_COL]
    rankings_plot = rankings_plot[annot_cols]

    sorted_error_df = score.signed_error_df.reindex(heatmap_rankings_df.index)
    sorted_error_df[AGG_COL] = sorted_error_df.mean(axis=1)
    sorted_error_df = sorted_error_df[annot_cols]

    fig_height = max(12, 0.4 * len(heatmap_rankings_df) + 5)

    fig = Figure(figsize=(12, fig_height))
    ax = fig.add_subplot(111)

    sns.heatmap(
        sorted_error_df, annot=rankings_plot, fmt=".0f", cmap="RdBu_r",
        vmin=-0.2, vmax=0.2,
        cbar_kws={"label": "Signed Percentage Error (Color)", "shrink": 0.5},
        linewidths=1, linecolor="white", annot_kws={"size": 10},
        ax=ax,
    )
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    matplotlib.artist.setp(ax.get_xticklabels(), rotation=35, ha="left", rotation_mode="anchor")

    # Intentionally differs from notebook: removed reference to "STEP 6's Total_Rank_Score"
    # to make the explanation self-contained for web app users
    subtitle = "(Color = Error Direction, Text = Rank #; leftmost col = Avg Rank (text) / Avg Signed Error (color), not Avg APE)"
    if use_full_field:
        subtitle += "\nCONTROL (benchmark) included for reference -- ranks here are full-field, so they may differ by up to 1 from standings"
    elif score.n_competitors < len(score.results_df):
        subtitle += "\nCONTROL (benchmark) excluded from this view"

    ax.set_title(
        f"Prediction Analysis Heatmap (Sorted by Standings)\n{subtitle}",
        fontsize=16, pad=70,
    )
    ax.set_xlabel("Asset", fontsize=12)
    ax.set_ylabel("Participant (Ordered by Total Score)", fontsize=12)
    ax.tick_params(axis="y", rotation=0)
    fig.tight_layout()

    return fig


def prediction_distributions(score, assets: list[str], actual_prices: dict[str, float]) -> Figure:
    """Distribution histograms of predictions vs actual - Visualization 3."""
    n_assets = len(assets)
    n_cols = 2
    n_rows = math.ceil(n_assets / n_cols)

    fig = Figure(figsize=(15, 5 * n_rows))
    axes = fig.subplots(n_rows, n_cols)
    axes = np.atleast_1d(axes).flatten()

    results_df = score.results_df

    for i, asset in enumerate(assets):
        ax = axes[i]
        actual_price = actual_prices.get(asset)
        pred_col = f"{asset}_Pred"

        if actual_price is not None and pred_col in results_df.columns:
            sns.histplot(results_df[pred_col], kde=True, ax=ax, color=SEQ_COLOR, edgecolor="black")
            ax.axvline(actual_price, color="#e34948", linestyle="-", linewidth=2, label=f"Actual: {actual_price:,.2f}")
            avg_pred = results_df[pred_col].mean()
            ax.axvline(avg_pred, color="#1baf7a", linestyle="--", linewidth=2, label=f"Avg Pred: {avg_pred:,.2f}")
            ax.set_title(f"{asset} Predictions vs Actual", fontsize=14)
            ax.set_xlabel("Price / Rate")
            ax.set_ylabel("Frequency")
            ax.legend()
        else:
            ax.text(0.5, 0.5, "Data Not Available", ha="center", va="center")
            ax.set_title(asset)

    for j in range(n_assets, len(axes)):
        axes[j].axis("off")

    fig.subplots_adjust(hspace=0.4, wspace=0.3)

    return fig


def winner_vs_control(score, assets: list[str], actual_prices: dict[str, float]) -> Figure:
    """Winner vs CONTROL vs Actual bar charts - Visualization 4."""
    results_df = score.results_df
    winner_name = score.ape_winner
    has_control = "CONTROL" in results_df.index

    winner_preds, control_preds = [], []
    for asset in assets:
        pred_col = f"{asset}_Pred"
        winner_preds.append(results_df.loc[winner_name, pred_col])
        control_preds.append(results_df.loc["CONTROL", pred_col] if has_control else np.nan)

    n_assets = len(assets)
    n_cols = min(4, n_assets)
    n_rows = math.ceil(n_assets / n_cols)

    fig = Figure(figsize=(5 * n_cols, 5 * n_rows))
    axes = fig.subplots(n_rows, n_cols)
    axes = np.atleast_1d(axes).flatten()

    labels = [f"{winner_name}\n(Winner)", "CONTROL", "Actual"]

    for i, asset in enumerate(assets):
        ax = axes[i]
        actual_price = actual_prices.get(asset)

        if actual_price is None:
            ax.text(0.5, 0.5, "Data Not Available", ha="center", va="center")
            ax.set_title(f"{asset} Predictions", fontsize=14, pad=10)
            continue

        values = [winner_preds[i], control_preds[i], actual_price]
        bars = ax.bar(labels, values, color=CAT_COLORS, edgecolor="black", alpha=0.9)
        ax.set_title(f"{asset} Predictions", fontsize=14, pad=10)

        for bar in bars:
            height = bar.get_height()
            if np.isnan(height):
                continue
            text_val = f"{height:,.0f}" if height > 1000 else f"{height:,.1f}" if height > 100 else f"{height:,.2f}"
            ax.text(bar.get_x() + bar.get_width() / 2.0, height, text_val,
                    ha="center", va="bottom", fontsize=11, fontweight="bold")

    for j in range(n_assets, len(axes)):
        axes[j].axis("off")

    fig.suptitle(f"Accuracy Comparison: Leader ({winner_name}) vs CONTROL vs Actual", fontsize=18, y=1.02)
    fig.tight_layout()

    return fig


def figure_to_png(fig: Figure, dpi: int = 150) -> bytes:
    """Convert a Figure to PNG bytes."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight")
    buffer.seek(0)
    return buffer.getvalue()


def render_all_charts(score, assets: list[str], actual_prices: dict[str, float]) -> list[ChartImage]:
    """Render all 4 charts in notebook order (VIS 1, 2, 3, 4)."""
    charts = [
        ("prediction_error_heatmap", "Prediction Error Heatmap", error_heatmap(score)),
        ("rank_heatmap", "Prediction Analysis Heatmap", rank_heatmap(score)),
        ("prediction_distributions", "Prediction Distributions", prediction_distributions(score, assets, actual_prices)),
        ("winner_vs_control_vs_actual", "Winner vs CONTROL vs Actual", winner_vs_control(score, assets, actual_prices)),
    ]

    return [
        ChartImage(key=key, title=title, png=figure_to_png(fig))
        for key, title, fig in charts
    ]
