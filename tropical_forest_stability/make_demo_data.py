"""Generate synthetic demo data to test analysis.py without GEE access."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import N_CANDIDATE_POINTS, OUTPUT_DIR, POINTS_RAW_CSV, RANDOM_SEED


def make_demo_csv(n: int = N_CANDIDATE_POINTS, seed: int = RANDOM_SEED) -> str:
    rng = np.random.default_rng(seed)
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    water_stress = rng.normal(0, 1, n)
    rooting = 2.5 - 0.4 * water_stress + rng.normal(0, 0.3, n)
    ssd = 0.55 - 0.05 * water_stress + rng.normal(0, 0.03, n)
    sla = 12 + 1.5 * water_stress + rng.normal(0, 1.0, n)

    stability = (
        8
        + 0.6 * ssd
        + 0.4 * rooting
        - 0.8 * water_stress
        + rng.normal(0, 0.5, n)
    )
    stability = np.clip(stability, 0.5, 25)

    agb_mean = rng.uniform(80, 250, n)
    agb_std = agb_mean / stability

    df = pd.DataFrame(
        {
            "lon": rng.uniform(-80, 140, n),
            "lat": rng.uniform(-25, 25, n),
            "agb_mean": agb_mean,
            "agb_std": agb_std,
            "agb_cv": agb_std / agb_mean,
            "stability_mu_sigma": stability,
            "vpd_mean": rng.uniform(0.5, 2.5, n),
            "vpd_p95": rng.uniform(1.0, 4.0, n) + 0.3 * water_stress,
            "soil_min": rng.uniform(50, 200, n),
            "soil_mean": rng.uniform(120, 280, n),
            "soil_deficit": np.clip(0.2 + 0.15 * water_stress + rng.normal(0, 0.05, n), 0, 1),
            "def_mean": rng.uniform(20, 120, n),
            "pdsi_min": rng.uniform(-4, 1, n),
            "pr_mean": rng.uniform(1000, 3000, n),
            "pr_cv": rng.uniform(0.05, 0.35, n),
            "sla_m2_kg": sla,
            "ssd_g_cm3": ssd,
            "rooting_depth_m": rooting,
            "leaf_n_area_g_m2": rng.uniform(1.0, 3.5, n),
            "conduit_diameter_um": rng.uniform(80, 200, n),
            "SLA_aoa": 1,
            "SSD_aoa": 1,
            "Rooting_depth_aoa": 1,
            "Leaf_N_area_aoa": 1,
            "Stem_conduit_diameter_aoa": 1,
        }
    )

    out = Path(POINTS_RAW_CSV)
    df.to_csv(out, index=False)
    print(f"Wrote demo data: {out} ({len(df)} rows)")
    return str(out)


if __name__ == "__main__":
    make_demo_csv()
