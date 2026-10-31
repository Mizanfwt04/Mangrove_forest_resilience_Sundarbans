"""
Publication-style figures for Chakaria mangrove uGPP analysis.

Figure 0 — Study-area boundary + sites by group
Figure 1 — Mean annual uGPP trajectories by group (2000–2024)
Figure 2 — Temporal stability (Mean/SD) boxplots
Figure 3 — Sen slope boxplots
Figure 4 — Kendall Tau boxplots

Usage (from chakaria_mangrove_productivity/):
  python scripts/04_figures.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon as MplPolygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402
    ANNUAL_UGPP_CSV,
    BOUNDARY_GEOJSON,
    FIGURE_DPI,
    FIGURES_DIR,
    GROUP_COLORS,
    GROUPS,
    SITE_METRICS_CSV,
    SITES_CSV,
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


def _boundary_rings(path: Path) -> list[list[tuple[float, float]]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    def rings_from_geom(geom: dict) -> list[list[tuple[float, float]]]:
        gtype = geom["type"]
        coords = geom["coordinates"]
        if gtype == "Polygon":
            return [[(float(x), float(y)) for x, y, *_ in ring] for ring in coords]
        if gtype == "MultiPolygon":
            out: list[list[tuple[float, float]]] = []
            for poly in coords:
                out.extend([(float(x), float(y)) for x, y, *_ in ring] for ring in poly)
            return out
        raise ValueError(f"Unsupported geometry: {gtype}")

    if data["type"] == "FeatureCollection":
        rings: list[list[tuple[float, float]]] = []
        for ft in data["features"]:
            rings.extend(rings_from_geom(ft["geometry"]))
        return rings
    if data["type"] == "Feature":
        return rings_from_geom(data["geometry"])
    return rings_from_geom(data)


def fig0_study_area(
    sites: pd.DataFrame,
    boundary_path: Path,
    out: Path,
) -> None:
    rings = _boundary_rings(boundary_path)
    fig, ax = plt.subplots(figsize=(6.2, 6.4))

    for i, ring in enumerate(rings):
        xs, ys = zip(*ring)
        ax.plot(
            xs,
            ys,
            color="#222222",
            lw=1.6,
            zorder=2,
            label="Study area" if i == 0 else None,
        )
        ax.add_patch(
            MplPolygon(
                list(zip(xs, ys)),
                closed=True,
                facecolor="#c7e9c0",
                edgecolor="none",
                alpha=0.35,
                zorder=1,
            )
        )

    for group in GROUPS:
        sub = sites.loc[sites["Group"] == group]
        ax.scatter(
            sub["Longitude"],
            sub["Latitude"],
            s=42,
            color=GROUP_COLORS[group],
            edgecolors="#111111",
            linewidths=0.4,
            label=group,
            zorder=3,
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Chakaria study area and sample sites")
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(frameon=False, loc="best")
    fig.tight_layout()
    fig.savefig(out, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)


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

    rng = np.random.default_rng(0)
    for i, vals in enumerate(data, start=1):
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
    parser.add_argument(
        "--boundary",
        type=Path,
        default=BOUNDARY_GEOJSON,
        help=(
            "Study-area GeoJSON (default data/chakaria_boundary.geojson; "
            r"copy from D:\A_letter_to_Science\chakaria_boundary.geojson)"
        ),
    )
    parser.add_argument("--sites", type=Path, default=SITES_CSV)
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

    if args.boundary.exists() and args.sites.exists():
        sites = pd.read_csv(args.sites)
        fig0_study_area(sites, args.boundary, FIGURES_DIR / "Figure0_Study_Area.png")
    else:
        print(f"Skipping Figure 0 — boundary not found at {args.boundary}")

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
