"""
Compound climate stress analysis for Sundarbans mangrove plots.

Examines how humid-heat conditions and co-occurring stressors (salinity,
sulfide, precipitation deficits) relate to recurring perturbation frequency
and recovery dynamics under tropical extreme-climate regimes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


DATA_FILE = Path(__file__).resolve().parent / "Data_Mangrove_resilience_Sundarbans.xlsx"
SHEET = "Plot_level_Raw_data"

STRESS_VARS = ("MAT", "MAP", "SALINITY", "SULFIDE")
RESILIENCE_VARS = ("PF", "ADI", "WDI", "lambda_ac1_py", "lambda_va_py")


def zscore(series: pd.Series) -> pd.Series:
    std = series.std()
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def humid_heat_index(df: pd.DataFrame) -> pd.Series:
    """
    Proxy for humid-heat exposure in the tropics.

    Combines mean annual temperature with moisture availability (MAP).
    High MAT and high MAP indicate sustained humid-heat conditions typical
    of the Sundarbans monsoon tropics.
    """
    mat_z = zscore(df["MAT"])
    map_z = zscore(df["MAP"])
    return mat_z + map_z


def compound_stress_index(df: pd.DataFrame) -> pd.Series:
    """
    Multi-stressor index: humid heat + osmotic/chemical stress + dry-season risk.

    Higher values indicate stronger compound stress under extreme tropical climate.
    """
    hhi = humid_heat_index(df)
    salinity_z = zscore(df["SALINITY"])
    sulfide_z = zscore(df["SULFIDE"])
    drought_z = -zscore(df["MAP"])
    return hhi + salinity_z + sulfide_z + drought_z


def recurring_stress_score(df: pd.DataFrame) -> pd.Series:
    """
    Score for recurring compound stress propagation.

    Combines perturbation frequency with slower recovery (less negative lambdas).
    """
    pf_z = zscore(df["PF"])
    ac1_z = zscore(df["lambda_ac1_py"])
    var_z = zscore(df["lambda_va_py"])
    return pf_z + ac1_z + var_z


def load_plot_data(data_file: Path = DATA_FILE) -> pd.DataFrame:
    df = pd.read_excel(data_file, sheet_name=SHEET)
    df = df.rename(columns={"plot": "Plot"})
    return df


def summarize_correlations(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["humid_heat_index"] = humid_heat_index(df)
    df["compound_stress_index"] = compound_stress_index(df)
    df["recurring_stress_score"] = recurring_stress_score(df)

    rows = []
    for outcome in RESILIENCE_VARS:
        for predictor in ("humid_heat_index", "compound_stress_index", *STRESS_VARS):
            mask = df[[outcome, predictor]].notna().all(axis=1)
            if mask.sum() < 3:
                continue
            r, p = stats.pearsonr(df.loc[mask, predictor], df.loc[mask, outcome])
            rows.append(
                {
                    "outcome": outcome,
                    "predictor": predictor,
                    "r": r,
                    "p": p,
                    "n": int(mask.sum()),
                }
            )
    return pd.DataFrame(rows).sort_values(["outcome", "p"])


def fit_propagation_model(df: pd.DataFrame) -> dict[str, float]:
    """Linear model: recurring stress ~ compound stress + humid heat."""
    df = df.copy()
    df["humid_heat_index"] = humid_heat_index(df)
    df["compound_stress_index"] = compound_stress_index(df)
    df["recurring_stress_score"] = recurring_stress_score(df)

    x = df[["compound_stress_index", "humid_heat_index"]].values
    y = df["recurring_stress_score"].values
    mask = np.isfinite(x).all(axis=1) & np.isfinite(y)
    x, y = x[mask], y[mask]

    design = np.column_stack([np.ones(len(x)), x])
    coef, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    y_hat = design @ coef
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot else np.nan

    return {
        "intercept": coef[0],
        "compound_stress_beta": coef[1],
        "humid_heat_beta": coef[2],
        "r2": r2,
        "n": int(mask.sum()),
    }


def make_figure(df: pd.DataFrame, output_dir: Path) -> Path:
    df = df.copy()
    df["humid_heat_index"] = humid_heat_index(df)
    df["compound_stress_index"] = compound_stress_index(df)
    df["recurring_stress_score"] = recurring_stress_score(df)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    ax = axes[0, 0]
    ax.scatter(df["humid_heat_index"], df["PF"], alpha=0.7, edgecolor="k", linewidth=0.3)
    ax.set_xlabel("Humid-heat index (z)")
    ax.set_ylabel("Perturbation frequency (PF)")
    ax.set_title("(a) Humid heat vs. recurring perturbations")
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    ax.scatter(df["compound_stress_index"], df["ADI"], alpha=0.7, color="#d62728", edgecolor="k", linewidth=0.3)
    ax.set_xlabel("Compound stress index (z)")
    ax.set_ylabel("Disturbance index (ADI)")
    ax.set_title("(b) Compound stress vs. disturbance intensity")
    ax.grid(True, alpha=0.3)

    ax = axes[1, 0]
    ax.scatter(df["compound_stress_index"], df["recurring_stress_score"], alpha=0.7, color="#2ca02c", edgecolor="k", linewidth=0.3)
    ax.set_xlabel("Compound stress index (z)")
    ax.set_ylabel("Recurring stress score (z)")
    ax.set_title("(c) Propagation of recurring compound stress")
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    corr = df[list(STRESS_VARS)].corr()
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(STRESS_VARS)))
    ax.set_yticks(range(len(STRESS_VARS)))
    ax.set_xticklabels(STRESS_VARS, rotation=45, ha="right")
    ax.set_yticklabels(STRESS_VARS)
    ax.set_title("(d) Co-stressor correlation matrix")
    plt.colorbar(im, ax=ax, shrink=0.8)
    for i in range(len(STRESS_VARS)):
        for j in range(len(STRESS_VARS)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)

    fig.suptitle(
        "Humid heat and recurring compound stress under extreme tropical climate\n"
        "Sundarbans mangrove plot-level data",
        fontsize=13,
        fontweight="bold",
    )
    plt.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "compound_stress_propagation.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


def run_analysis(data_file: Path, output_dir: Path) -> None:
    df = load_plot_data(data_file)
    corr_table = summarize_correlations(df)
    model = fit_propagation_model(df)
    fig_path = make_figure(df, output_dir)

    corr_path = output_dir / "compound_stress_correlations.csv"
    corr_table.to_csv(corr_path, index=False)

    print("=== Humid heat & compound stress propagation (Sundarbans plots) ===\n")
    print(f"Plots analyzed: {len(df)}")
    print(f"\nPropagation model (recurring stress ~ compound + humid heat):")
    print(f"  n={model['n']}, R²={model['r2']:.3f}")
    print(f"  compound stress β={model['compound_stress_beta']:.3f}")
    print(f"  humid heat β={model['humid_heat_beta']:.3f}")
    print("\nTop correlations (|r| > 0.25, p < 0.05):")
    sig = corr_table[(corr_table["p"] < 0.05) & (corr_table["r"].abs() > 0.25)]
    if sig.empty:
        print("  (none met threshold)")
    else:
        for _, row in sig.iterrows():
            print(f"  {row['predictor']} → {row['outcome']}: r={row['r']:.3f}, p={row['p']:.4f}")
    print(f"\nSaved figure: {fig_path}")
    print(f"Saved correlations: {corr_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze humid heat and recurring compound stress in Sundarbans plots."
    )
    parser.add_argument("--data", type=Path, default=DATA_FILE, help="Excel data file path")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("compound_stress_output"),
        help="Directory for figures and tables",
    )
    args = parser.parse_args()
    run_analysis(args.data, args.output_dir)


if __name__ == "__main__":
    main()
