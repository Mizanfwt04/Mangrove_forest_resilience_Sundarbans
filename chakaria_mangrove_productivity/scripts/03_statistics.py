"""
Group comparisons for Chakaria mangrove productivity / stability / trajectory.

- Kruskal–Wallis across RMSP, PMSP, PMWSP
- Dunn post-hoc (Holm-adjusted) when available

Usage (from chakaria_mangrove_productivity/):
  python scripts/03_statistics.py
"""

from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (  # noqa: E402
    GROUP_SUMMARY_CSV,
    GROUPS,
    KRUSKAL_CSV,
    DUNN_CSV,
    METRIC_COLS,
    SITE_METRICS_CSV,
    TABLES_DIR,
)


def group_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group in GROUPS:
        sub = df.loc[df["Group"] == group]
        for col in METRIC_COLS:
            if col not in sub.columns:
                continue
            x = sub[col].dropna()
            rows.append(
                {
                    "Group": group,
                    "Metric": col,
                    "n": int(x.size),
                    "mean": float(x.mean()) if x.size else np.nan,
                    "sd": float(x.std(ddof=1)) if x.size > 1 else np.nan,
                    "median": float(x.median()) if x.size else np.nan,
                    "q25": float(x.quantile(0.25)) if x.size else np.nan,
                    "q75": float(x.quantile(0.75)) if x.size else np.nan,
                }
            )
    return pd.DataFrame(rows)


def kruskal_tests(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in METRIC_COLS:
        if col not in df.columns:
            continue
        samples = [df.loc[df["Group"] == g, col].dropna().to_numpy() for g in GROUPS]
        if any(len(s) < 1 for s in samples):
            H, p = np.nan, np.nan
        else:
            H, p = kruskal(*samples)
        rows.append(
            {
                "Metric": col,
                "H": float(H),
                "p": float(p),
                "n_RMSP": len(samples[0]),
                "n_PMSP": len(samples[1]),
                "n_PMWSP": len(samples[2]),
            }
        )
    return pd.DataFrame(rows)


def _holm_adjust(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    adjusted = np.empty(m, dtype=float)
    prev = 0.0
    for rank, idx in enumerate(order):
        adj = (m - rank) * pvals[idx]
        adj = min(adj, 1.0)
        adj = max(adj, prev)
        adjusted[idx] = adj
        prev = adj
    return adjusted.tolist()


def dunn_like_posthoc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pairwise Mann–Whitney U with Holm correction (Dunn-style post-hoc).
    Uses scikit-posthocs.dunn if installed; otherwise this fallback.
    """
    try:
        import scikit_posthocs as sp  # type: ignore

        frames = []
        for col in METRIC_COLS:
            if col not in df.columns:
                continue
            mat = sp.posthoc_dunn(df, val_col=col, group_col="Group", p_adjust="holm")
            for a, b in combinations(GROUPS, 2):
                frames.append(
                    {
                        "Metric": col,
                        "Group_A": a,
                        "Group_B": b,
                        "p_holm": float(mat.loc[a, b]),
                        "method": "scikit_posthocs.dunn",
                    }
                )
        return pd.DataFrame(frames)
    except ImportError:
        pass

    rows = []
    for col in METRIC_COLS:
        if col not in df.columns:
            continue
        pairs = list(combinations(GROUPS, 2))
        raw_p = []
        meta = []
        for a, b in pairs:
            xa = df.loc[df["Group"] == a, col].dropna()
            xb = df.loc[df["Group"] == b, col].dropna()
            if len(xa) < 1 or len(xb) < 1:
                p = np.nan
            else:
                _, p = mannwhitneyu(xa, xb, alternative="two-sided")
            raw_p.append(float(p) if np.isfinite(p) else 1.0)
            meta.append((a, b, p))
        adj = _holm_adjust(raw_p)
        for (a, b, p), p_holm in zip(meta, adj):
            rows.append(
                {
                    "Metric": col,
                    "Group_A": a,
                    "Group_B": b,
                    "p_raw": float(p) if np.isfinite(p) else np.nan,
                    "p_holm": float(p_holm) if np.isfinite(p) else np.nan,
                    "method": "mannwhitney_holm",
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Group statistics for Chakaria metrics")
    parser.add_argument("--input", type=Path, default=SITE_METRICS_CSV)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Missing {args.input}. Run scripts/02_temporal_metrics.py first."
        )

    df = pd.read_csv(args.input)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    summary = group_summary(df)
    kw = kruskal_tests(df)
    dunn = dunn_like_posthoc(df)

    summary.to_csv(GROUP_SUMMARY_CSV, index=False)
    kw.to_csv(KRUSKAL_CSV, index=False)
    dunn.to_csv(DUNN_CSV, index=False)

    print("Group summary:")
    print(summary.to_string(index=False))
    print("\nKruskal–Wallis:")
    print(kw.to_string(index=False))
    print("\nPost-hoc:")
    print(dunn.to_string(index=False))
    print(f"\nWrote → {GROUP_SUMMARY_CSV}, {KRUSKAL_CSV}, {DUNN_CSV}")


if __name__ == "__main__":
    main()
