"""
Generate synthetic annual uGPP so the metrics / stats / figures pipeline
can be tested without Earth Engine credentials.

Site means differ slightly by group to mimic a plausible restoration narrative:
  PMWSP ≈ highest mean & stability
  RMSP  ≈ intermediate (remanent capacity)
  PMSP  ≈ planted ponds (recovering / variable)

Usage (from chakaria_mangrove_productivity/):
  python scripts/make_demo_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (  # noqa: E402
    ANNUAL_UGPP_CSV,
    END_YEAR,
    RANDOM_SEED,
    SITES_CSV,
    START_YEAR,
)

# Group-level generative parameters (mean level, SD of residuals, linear trend)
GROUP_PARAMS = {
    "PMWSP": {"mu": 1450.0, "sigma": 90.0, "trend": 4.0},
    "RMSP": {"mu": 1320.0, "sigma": 120.0, "trend": 3.0},
    "PMSP": {"mu": 1180.0, "sigma": 150.0, "trend": 5.5},
}


def make_demo_timeseries(
    sites_path: Path = SITES_CSV,
    out_path: Path = ANNUAL_UGPP_CSV,
    seed: int = RANDOM_SEED,
) -> Path:
    sites = pd.read_csv(sites_path)
    rng = np.random.default_rng(seed)
    years = np.arange(START_YEAR, END_YEAR + 1)

    records = []
    for _, row in sites.iterrows():
        params = GROUP_PARAMS[row["Group"]]
        site_offset = rng.normal(0, 60)
        for year in years:
            t = year - START_YEAR
            val = (
                params["mu"]
                + site_offset
                + params["trend"] * t
                + rng.normal(0, params["sigma"])
            )
            records.append(
                {
                    "Site": row["ID"],
                    "Group": row["Group"],
                    "Year": int(year),
                    "uGPP": float(max(val, 50.0)),
                }
            )

    df = pd.DataFrame(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote demo time series: {out_path} ({len(df)} rows, {df['Site'].nunique()} sites)")
    return out_path


if __name__ == "__main__":
    make_demo_timeseries()
