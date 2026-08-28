"""
Post-extraction analysis: stratified sampling, SEM paths, mediation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

from config import (
    FIGURES_DIR,
    N_TARGET_POINTS,
    OUTPUT_DIR,
    POINTS_RAW_CSV,
    POINTS_STRATIFIED_CSV,
    RANDOM_SEED,
    SEM_RESULTS_CSV,
    TRAITS,
)


@dataclass
class MediationResult:
    exposure: str
    mediator: str
    outcome: str
    path_a: float
    path_a_p: float
    path_b: float
    path_b_p: float
    direct_effect: float
    direct_p: float
    indirect_effect: float
    total_effect: float
    prop_mediated: float


def load_and_clean(csv_path: str = POINTS_RAW_CSV) -> pd.DataFrame:
    """Load GEE export and apply quality filters."""
    df = pd.read_csv(csv_path)

    # Rename trait columns to friendly names
    rename_map = {k: v for k, v in TRAITS.items()}
    df = df.rename(columns=rename_map)

    trait_cols = list(TRAITS.values())
    aoa_cols = [f"{k}_aoa" for k in TRAITS]

    # Keep points with valid AGB stability and traits inside model domain (aoa == 1)
    required = ["stability_mu_sigma", "agb_mean", "vpd_p95", "soil_deficit"] + trait_cols
    df = df.dropna(subset=required)
    for aoa in aoa_cols:
        if aoa in df.columns:
            df = df[df[aoa] == 1]

    df = df[df["stability_mu_sigma"] > 0]
    df = df[df["agb_mean"] >= 50]
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=required)
    return df.reset_index(drop=True)


def stratified_sample(
    df: pd.DataFrame,
    n: int = N_TARGET_POINTS,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    Stratify by climate stress (vpd_p95 x soil_deficit) and stability tertiles.
    ~equal points per stratum, then cap at n.
    """
    rng = np.random.default_rng(seed)
    work = df.copy()

    work["stress_tertile"] = pd.qcut(
        work["vpd_p95"].rank(method="first"), q=3, labels=["low", "mid", "high"]
    )
    work["stability_tertile"] = pd.qcut(
        work["stability_mu_sigma"].rank(method="first"), q=3, labels=["low", "mid", "high"]
    )
    work["stratum"] = work["stress_tertile"].astype(str) + "_" + work["stability_tertile"].astype(str)

    per_stratum = max(1, n // work["stratum"].nunique())
    parts = []
    for _, group in work.groupby("stratum"):
        k = min(len(group), per_stratum)
        parts.append(group.sample(n=k, random_state=rng.integers(1e9)))

    out = pd.concat(parts, ignore_index=True)
    if len(out) > n:
        out = out.sample(n=n, random_state=seed)
    return out.reset_index(drop=True)


def zscore(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std(ddof=0)


def build_water_stress_index(df: pd.DataFrame) -> pd.Series:
    """Compound climate stress: standardized VPD + soil deficit + water deficit."""
    components = []
    for col in ["vpd_p95", "soil_deficit", "def_mean"]:
        if col in df.columns:
            components.append(zscore(df[col]))
    if not components:
        raise ValueError("No climate columns found for water stress index")
    return sum(components) / len(components)


def run_mediation(
    df: pd.DataFrame,
    exposure: str,
    mediator: str,
    outcome: str = "stability_mu_sigma",
    covariates: Iterable[str] | None = None,
) -> MediationResult:
    """
    Simple mediation via OLS paths (Baron & Kenny / Sobel-style).
    exposure -> mediator -> outcome
    """
    covariates = list(covariates or [])
    sub = df[[exposure, mediator, outcome, *covariates]].dropna()
    n = len(sub)

    # Path a: exposure -> mediator
    Xa = sm.add_constant(sub[[exposure, *covariates]])
    ma = sm.OLS(sub[mediator], Xa).fit()

    # Path b + direct: exposure + mediator -> outcome
    Xb = sm.add_constant(sub[[exposure, mediator, *covariates]])
    mb = sm.OLS(sub[outcome], Xb).fit()

    # Total effect: exposure -> outcome
    Xc = sm.add_constant(sub[[exposure, *covariates]])
    mc = sm.OLS(sub[outcome], Xc).fit()

    a = ma.params[exposure]
    b = mb.params[mediator]
    c_prime = mb.params[exposure]
    c_total = mc.params[exposure]
    indirect = a * b
    prop = indirect / c_total if c_total != 0 else np.nan

    return MediationResult(
        exposure=exposure,
        mediator=mediator,
        outcome=outcome,
        path_a=a,
        path_a_p=ma.pvalues[exposure],
        path_b=b,
        path_b_p=mb.pvalues[mediator],
        direct_effect=c_prime,
        direct_p=mb.pvalues[exposure],
        indirect_effect=indirect,
        total_effect=c_total,
        prop_mediated=prop,
    )


def run_all_mediations(df: pd.DataFrame) -> pd.DataFrame:
    """Test each trait as mediator of water stress -> stability."""
    df = df.copy()
    df["water_stress"] = build_water_stress_index(df)
    covariates = ["pr_cv"] if "pr_cv" in df.columns else []

    trait_cols = list(TRAITS.values())
    results = []
    for trait in trait_cols:
        try:
            res = run_mediation(
                df,
                exposure="water_stress",
                mediator=trait,
                outcome="stability_mu_sigma",
                covariates=covariates,
            )
            results.append(res.__dict__)
        except Exception as exc:
            results.append(
                {
                    "exposure": "water_stress",
                    "mediator": trait,
                    "outcome": "stability_mu_sigma",
                    "error": str(exc),
                }
            )
    return pd.DataFrame(results)


def plot_mediation_summary(results: pd.DataFrame, out_path: str) -> None:
    """Bar plot of indirect effects by trait mediator."""
    ok = results.dropna(subset=["indirect_effect"])
    if ok.empty:
        return
    ok = ok.sort_values("indirect_effect")
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#d73027" if x < 0 else "#1a9850" for x in ok["indirect_effect"]]
    ax.barh(ok["mediator"], ok["indirect_effect"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Indirect effect (water stress -> trait -> stability)")
    ax.set_title("Trait mediation of climate stress on forest carbon stability")
    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_scatter_panel(df: pd.DataFrame, out_path: str) -> None:
    """Quick diagnostic scatter panel."""
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    df["water_stress"] = build_water_stress_index(df)

    axes[0, 0].scatter(df["water_stress"], df["stability_mu_sigma"], s=8, alpha=0.4)
    axes[0, 0].set_xlabel("Water stress index")
    axes[0, 0].set_ylabel("Stability (mean/std AGB)")

    if "ssd_g_cm3" in df.columns:
        axes[0, 1].scatter(df["water_stress"], df["ssd_g_cm3"], s=8, alpha=0.4)
        axes[0, 1].set_xlabel("Water stress index")
        axes[0, 1].set_ylabel("Wood density (SSD)")

    if "rooting_depth_m" in df.columns:
        axes[1, 0].scatter(df["vpd_p95"], df["rooting_depth_m"], s=8, alpha=0.4)
        axes[1, 0].set_xlabel("VPD p95 (kPa)")
        axes[1, 0].set_ylabel("Rooting depth (m)")

    axes[1, 1].scatter(df["soil_deficit"], df["stability_mu_sigma"], s=8, alpha=0.4)
    axes[1, 1].set_xlabel("Soil moisture deficit")
    axes[1, 1].set_ylabel("Stability (mean/std AGB)")

    fig.suptitle("Tropical moist forest: climate, traits, and carbon stability")
    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def run_full_analysis(
    raw_csv: str = POINTS_RAW_CSV,
    stratified_csv: str = POINTS_STRATIFIED_CSV,
    sem_csv: str = SEM_RESULTS_CSV,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """End-to-end analysis from raw GEE export."""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(FIGURES_DIR).mkdir(parents=True, exist_ok=True)

    df = load_and_clean(raw_csv)
    sampled = stratified_sample(df, n=N_TARGET_POINTS)
    sampled.to_csv(stratified_csv, index=False)

    results = run_all_mediations(sampled)
    results.to_csv(sem_csv, index=False)

    plot_mediation_summary(results, f"{FIGURES_DIR}/mediation_indirect_effects.png")
    plot_scatter_panel(sampled, f"{FIGURES_DIR}/diagnostic_scatter.png")

    print(f"Cleaned points: {len(df)}")
    print(f"Stratified sample: {len(sampled)} -> {stratified_csv}")
    print(f"Mediation results -> {sem_csv}")
    return sampled, results


if __name__ == "__main__":
    run_full_analysis()
