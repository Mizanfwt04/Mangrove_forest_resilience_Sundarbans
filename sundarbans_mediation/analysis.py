"""
Mediation analysis for Sundarbans mangrove forest resilience.

Replicates the path logic from the published SEM (lavaan): climate and disturbance
effects on λVAR / λAC1 operating through biotic traits, structural diversity,
and sediment physicochemistry.

The original study used mean annual precipitation (MAP) and mean annual
temperature (MAT). This module also supports extreme-climate exposures once
merged from gee_extreme_climate.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from config import (
    BIOTIC_MEDIATORS,
    COMPARISON_CSV,
    DATA_SHEET,
    DATA_XLSX,
    DISTURBANCE,
    EXTREME_CLIMATE,
    FIGURES_DIR,
    MEAN_CLIMATE,
    MEDIATION_CSV,
    OUTCOME_DEFAULT,
    OUTPUT_DIR,
    SOIL_MEDIATORS,
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
    total_p: float
    prop_mediated: float


def load_plot_data(
    xlsx: str = DATA_XLSX,
    sheet: str = DATA_SHEET,
) -> pd.DataFrame:
    df = pd.read_excel(xlsx, sheet_name=sheet)
    if "Plot" in df.columns:
        df = df.rename(columns={"Plot": "plot"})
    return df


def run_mediation(
    df: pd.DataFrame,
    exposure: str,
    mediator: str,
    outcome: str = OUTCOME_DEFAULT,
    covariates: Iterable[str] | None = None,
) -> MediationResult:
    """Baron & Kenny OLS mediation: exposure → mediator → outcome."""
    covariates = list(covariates or [])
    cols = [exposure, mediator, outcome, *covariates]
    sub = df[cols].dropna()
    if len(sub) < 10:
        raise ValueError(f"Too few rows ({len(sub)}) for {exposure} → {mediator} → {outcome}")

    Xa = sm.add_constant(sub[[exposure, *covariates]])
    ma = sm.OLS(sub[mediator], Xa).fit()

    Xb = sm.add_constant(sub[[exposure, mediator, *covariates]])
    mb = sm.OLS(sub[outcome], Xb).fit()

    Xc = sm.add_constant(sub[[exposure, *covariates]])
    mc = sm.OLS(sub[outcome], Xc).fit()

    a = ma.params[exposure]
    b = mb.params[mediator]
    c_prime = mb.params[exposure]
    c_total = mc.params[exposure]
    indirect = a * b

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
        total_p=mc.pvalues[exposure],
        prop_mediated=indirect / c_total if c_total != 0 else np.nan,
    )


def run_mediation_grid(
    df: pd.DataFrame,
    exposures: list[str],
    mediators: list[str],
    outcome: str = OUTCOME_DEFAULT,
    covariates: Iterable[str] | None = None,
) -> pd.DataFrame:
    rows = []
    for exp in exposures:
        if exp not in df.columns:
            continue
        for med in mediators:
            if med not in df.columns:
                continue
            try:
                r = run_mediation(df, exp, med, outcome, covariates)
                rows.append(r.__dict__)
            except (ValueError, KeyError) as exc:
                rows.append(
                    {
                        "exposure": exp,
                        "mediator": med,
                        "outcome": outcome,
                        "error": str(exc),
                    }
                )
    return pd.DataFrame(rows)


def summarize_total_vs_direct(
    df: pd.DataFrame,
    predictors: list[str],
    outcome: str = OUTCOME_DEFAULT,
) -> pd.DataFrame:
    """Bivariate total effect (matches SEM 'total association' concept)."""
    rows = []
    for pred in predictors:
        if pred not in df.columns:
            continue
        sub = df[[pred, outcome]].dropna()
        X = sm.add_constant(sub[pred])
        m = sm.OLS(sub[outcome], X).fit()
        rows.append(
            {
                "predictor": pred,
                "outcome": outcome,
                "total_effect": m.params[pred],
                "total_p": m.pvalues[pred],
                "r_squared": m.rsquared,
            }
        )
    return pd.DataFrame(rows)


def compare_mean_vs_extreme_climate(
    df: pd.DataFrame,
    outcome: str = OUTCOME_DEFAULT,
    mediators: list[str] | None = None,
) -> pd.DataFrame:
    """
    Compare mediation strength for mean (MAP, MAT) vs extreme climate exposures.
    Extreme columns must be present in df (from GEE extraction).
    """
    mediators = mediators or list(BIOTIC_MEDIATORS) + list(SOIL_MEDIATORS) + [DISTURBANCE]
    mean_exp = [c for c in MEAN_CLIMATE if c in df.columns]
    extreme_exp = [c for c in EXTREME_CLIMATE if c in df.columns]
    if not extreme_exp:
        return pd.DataFrame()

    rows = []
    for exp in mean_exp + extreme_exp:
        for med in mediators:
            if med not in df.columns:
                continue
            try:
                r = run_mediation(df, exp, med, outcome)
                rows.append(
                    {
                        "climate_type": "mean" if exp in mean_exp else "extreme",
                        "exposure": exp,
                        "mediator": med,
                        "indirect_effect": r.indirect_effect,
                        "direct_effect": r.direct_effect,
                        "total_effect": r.total_effect,
                        "path_a_p": r.path_a_p,
                        "path_b_p": r.path_b_p,
                        "prop_mediated": r.prop_mediated,
                    }
                )
            except ValueError:
                pass
    return pd.DataFrame(rows)


def plot_indirect_effects(
    results: pd.DataFrame,
    title: str,
    out_path: str,
    exposure_filter: str | None = None,
) -> None:
    ok = results.dropna(subset=["indirect_effect"]).copy()
    if exposure_filter:
        ok = ok[ok["exposure"] == exposure_filter]
    if ok.empty:
        return

    ok["label"] = ok["exposure"] + " → " + ok["mediator"]
    ok = ok.sort_values("indirect_effect")
    colors = ["#d73027" if x < 0 else "#1a9850" for x in ok["indirect_effect"]]

    fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * len(ok))))
    ax.barh(ok["label"], ok["indirect_effect"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Indirect effect on resilience (λ)")
    ax.set_title(title)
    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def run_published_pathways(
    df: pd.DataFrame | None = None,
    outcome: str = OUTCOME_DEFAULT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Re-run the key mediation paths reported in the Sundarbans SEM (Fig. 6).

    Original study findings:
    - MAP: no direct effect; total β≈0.44 via MCH (+), SLA (−), salinity, PF
    - MAT: no direct effect; total β≈−0.20 via MCH (−), SLA (+), salinity chain
    - PF: direct negative β≈−0.29
    - P, pH: direct negative on resilience
    - MCH, SLA, structural diversity: direct positive on resilience
    """
    if df is None:
        df = load_plot_data()

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(FIGURES_DIR).mkdir(parents=True, exist_ok=True)

    climate = list(MEAN_CLIMATE.keys())
    mediators = list(BIOTIC_MEDIATORS.keys()) + list(SOIL_MEDIATORS.keys()) + [DISTURBANCE]

    mediation = run_mediation_grid(df, climate, mediators, outcome)
    mediation.to_csv(MEDIATION_CSV, index=False)

    totals = summarize_total_vs_direct(
        df,
        climate + [DISTURBANCE] + list(BIOTIC_MEDIATORS.keys()) + ["P", "PH", "DBHvar"],
        outcome,
    )

    for exp in climate:
        sub = mediation[mediation["exposure"] == exp]
        plot_indirect_effects(
            sub,
            f"Indirect pathways: {exp} → mediator → {outcome}",
            f"{FIGURES_DIR}/indirect_{exp}_{outcome}.png",
        )

    comparison = compare_mean_vs_extreme_climate(df, outcome)
    if not comparison.empty:
        comparison.to_csv(COMPARISON_CSV, index=False)

    print(f"Loaded {len(df)} plots from {DATA_XLSX}")
    print(f"Mediation results → {MEDIATION_CSV}")
    print("\nTotal effects (bivariate, z-scored):")
    print(totals.to_string(index=False))
    return mediation, totals


if __name__ == "__main__":
    run_published_pathways()
