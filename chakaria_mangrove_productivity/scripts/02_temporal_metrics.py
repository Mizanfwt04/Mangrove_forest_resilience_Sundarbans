"""
Compute site-level temporal metrics from annual uGPP time series.

Outputs:
  - Mean_uGPP, SD_uGPP, Temporal_Stability (= Mean/SD)
  - Sen_Slope (Theil–Sen)
  - Kendall_Tau + Mann–Kendall p-value

Usage (from chakaria_mangrove_productivity/):
  python scripts/02_temporal_metrics.py
  python scripts/02_temporal_metrics.py --input data/annual_ugpp.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import theilslopes

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (  # noqa: E402
    ANNUAL_UGPP_CSV,
    SITE_METRICS_CSV,
    SITES_CSV,
    TABLES_DIR,
)


def mann_kendall(series: np.ndarray) -> tuple[float, float]:
    """
    Return (Kendall Tau, two-sided p) using pymannkendall if available,
    otherwise fall back to scipy.stats.kendalltau.
    """
    x = np.asarray(series, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return np.nan, np.nan

    try:
        import pymannkendall as mk

        res = mk.original_test(x)
        return float(res.Tau), float(res.p)
    except ImportError:
        from scipy.stats import kendalltau

        tau, p = kendalltau(np.arange(len(x)), x)
        return float(tau), float(p)


def site_metrics(ts: pd.DataFrame) -> pd.DataFrame:
    """Aggregate annual uGPP to site-level productivity / stability / trend metrics."""
    required = {"Site", "Year", "uGPP"}
    missing = required - set(ts.columns)
    if missing:
        raise ValueError(f"annual_ugpp.csv missing columns: {sorted(missing)}")

    rows = []
    for site, sub in ts.groupby("Site", sort=False):
        sub = sub.dropna(subset=["uGPP"]).sort_values("Year")
        y = sub["uGPP"].to_numpy(dtype=float)
        years = sub["Year"].to_numpy(dtype=float)

        group = sub["Group"].iloc[0] if "Group" in sub.columns else None
        mean = float(np.nanmean(y)) if y.size else np.nan
        sd = float(np.nanstd(y, ddof=1)) if y.size > 1 else np.nan
        stability = mean / sd if (np.isfinite(sd) and sd > 0) else np.nan

        if y.size >= 2:
            slope, *_ = theilslopes(y, years)
            sen = float(slope)
        else:
            sen = np.nan

        tau, p = mann_kendall(y)

        rows.append(
            {
                "Site": site,
                "Group": group,
                "n_years": int(y.size),
                "Mean_uGPP": mean,
                "SD_uGPP": sd,
                "Temporal_Stability": stability,
                "Sen_Slope": sen,
                "Kendall_Tau": tau,
                "MK_p": p,
            }
        )

    out = pd.DataFrame(rows)

    # Attach lon/lat if available
    if SITES_CSV.exists():
        sites = pd.read_csv(SITES_CSV)
        out = out.merge(
            sites.rename(columns={"ID": "Site"})[["Site", "Longitude", "Latitude"]],
            on="Site",
            how="left",
        )
        # Prefer Group from sites inventory if missing in time series
        if out["Group"].isna().any():
            out = out.drop(columns=["Group"]).merge(
                sites.rename(columns={"ID": "Site"})[["Site", "Group"]],
                on="Site",
                how="left",
            )

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Chakaria uGPP site metrics")
    parser.add_argument("--input", type=Path, default=ANNUAL_UGPP_CSV)
    parser.add_argument("--out", type=Path, default=SITE_METRICS_CSV)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Missing {args.input}. Run scripts/01_extract_gee.py or "
            "scripts/make_demo_data.py first."
        )

    ts = pd.read_csv(args.input)
    metrics = site_metrics(ts)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(args.out, index=False)
    print(f"Wrote {len(metrics)} sites → {args.out}")
    print(metrics.groupby("Group")[["Mean_uGPP", "Temporal_Stability", "Sen_Slope"]].mean())


if __name__ == "__main__":
    main()
