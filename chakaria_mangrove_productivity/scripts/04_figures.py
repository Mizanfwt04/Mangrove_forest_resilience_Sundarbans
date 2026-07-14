"""
Publication-style figures for Chakaria mangrove uGPP analysis.

Figure 1 — Mean annual uGPP trajectories by group (2000–2024)
Figure 2 — Temporal stability (Mean/SD) boxplots
Figure 3 — Sen slope boxplots
Figure 4 — Kendall Tau boxplots

Usage (from chakaria_mangrove_productivity/):
  python scripts/04_figures.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (  # noqa: E402
    ANNUAL_UGPP_CSV,
    FIGURE_DPI,
    FIGURES_DIR,
    GROUP_COLORS,
    GROUPS,
    SITE_METRICS_CSV,
)


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 9,
            "figure.dpi": 150,
        }
    )


def fig1_trajectories(ts: pd.DataFrame, out: Path) -> None:
    g = (
        ts.dropna(subset=["uGPP"])
        .groupby(["Group", "Year"], as_index=False)["uGPP"]
        .agg(mean="mean", sd="std", n="count")
    )
    g["se"] = g["sd"] / np.sqrt(g["n"].clip(lower=1))

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for group in GROUPS:
        sub = g.loc[g["Group"] == group].sort_values("Year")
        color = GROUP_COLORS[group]
        ax.plot(sub["Year"], sub["mean"], color=color, lw=2.2, label=group)
        ax.fill_between(
            sub["Year"],
            sub["mean"] - sub["se"],
            sub["mean"] + sub["se"],
            color=color,
            alpha=0.18,
            linewidth=0,
        )

    ax.set_xlabel("Year")
    ax.set_ylabel(r"Mean annual uGPP (gC m$^{-2}$ yr$^{-1}$)")
    ax.set_title("Ecosystem function: productivity trajectories")
    ax.legend(frameon=False, title="Group")
    fig.tight_layout()
    fig.savefig(out, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)


def _boxplot_metric(
    metrics: pd.DataFrame,
    col: str,
    ylabel: str,
    title: str,
    out: Path,
) -> None:
    data = [metrics.loc[metrics["Group"] == g, col].dropna().to_numpy() for g in GROUPS]
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    try:
        bp = ax.boxplot(
            data,
            tick_labels=list(GROUPS),
            patch_artist=True,
            widths=0.55,
            medianprops={"color": "#222222", "linewidth": 1.4},
            whiskerprops={"color": "#444444"},
            capprops={"color": "#444444"},
            flierprops={"marker": "o", "markersize": 4, "alpha": 0.7},
        )
    except TypeError:
        bp = ax.boxplot(
            data,
            labels=list(GROUPS),
            patch_artist=True,
            widths=0.55,
            medianprops={"color": "#222222", "linewidth": 1.4},
            whiskerprops={"color": "#444444"},
            capprops={"color": "#444444"},
            flierprops={"marker": "o", "markersize": 4, "alpha": 0.7},
        )
    for patch, group in zip(bp["boxes"], GROUPS):
        patch.set_facecolor(GROUP_COLORS[group])
        patch.set_alpha(0.75)
        patch.set_edgecolor("#222222")

    # overlay points
    rng = np.random.default_rng(0)
    for i, (group, vals) in enumerate(zip(GROUPS, data), start=1):
        if vals.size == 0:
            continue
        jitter = rng.normal(0, 0.04, size=vals.size)
        ax.scatter(
            np.full(vals.size, i) + jitter,
            vals,
            s=22,
            color="#111111",
            alpha=0.55,
            zorder=3,
        )

    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Make Chakaria uGPP figures")
    parser.add_argument("--timeseries", type=Path, default=ANNUAL_UGPP_CSV)
    parser.add_argument("--metrics", type=Path, default=SITE_METRICS_CSV)
    args = parser.parse_args()

    if not args.timeseries.exists() or not args.metrics.exists():
        raise FileNotFoundError(
            "Need annual_ugpp.csv and site_metrics.csv. "
            "Run make_demo_data.py or 01/02 scripts first."
        )

    _style()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    ts = pd.read_csv(args.timeseries)
    metrics = pd.read_csv(args.metrics)

    fig1_trajectories(ts, FIGURES_DIR / "Figure1_Productivity_Trajectories.png")
    _boxplot_metric(
        metrics,
        "Temporal_Stability",
        r"Temporal stability ($\mu$/$\sigma$)",
        "Ecosystem stability",
        FIGURES_DIR / "Figure2_Temporal_Stability.png",
    )
    _boxplot_metric(
        metrics,
        "Sen_Slope",
        r"Sen slope (gC m$^{-2}$ yr$^{-2}$)",
        "Ecosystem trajectory (Sen slope)",
        FIGURES_DIR / "Figure3_Sen_Slope.png",
    )
    _boxplot_metric(
        metrics,
        "Kendall_Tau",
        "Kendall Tau",
        "Ecosystem trajectory (Mann–Kendall)",
        FIGURES_DIR / "Figure4_Kendall_Tau.png",
    )

    print(f"Wrote figures → {FIGURES_DIR}")


if __name__ == "__main__":
    main()
