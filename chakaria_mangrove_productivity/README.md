# Chakaria remanent mangrove productivity — Python + geemap + GEE

End-to-end workflow for comparing **ecosystem function**, **temporal stability**, and **productivity trajectories** of remanent / planted mangroves within shrimp ponds versus protected mangrove reference sites in the former Chakaria Sundarbans.

## Study design

| Group | Code | n | Description |
|-------|------|---|-------------|
| Remanent mangrove in shrimp ponds | RMSP | 10 | Remnant mangrove patches inside ponds |
| Planted mangrove in shrimp ponds | PMSP | 10 | Silvofishery plantings |
| Protected mangrove (no shrimp ponds) | PMWSP | 10 | Reference protected mangrove |

| Component | Source |
|-----------|--------|
| Productivity | Global Pasture Watch annual uGPP (`ggpp-30m/v1/ugpp_m`), 2000–2024, ~30 m |
| Spatial unit | Site point + 60 m buffer |
| Function | Mean annual uGPP |
| Stability | Temporal stability \(TS = \mu / \sigma\) |
| Trajectory | Theil–Sen slope + Mann–Kendall Tau |
| Group tests | Kruskal–Wallis + Dunn / Mann–Whitney Holm post-hoc |

**Hypothesis framing:** RMSP and PMSP maintain ecosystem functioning, stability, and positive productivity trajectories comparable to PMWSP — evidence that the former Chakaria Sundarbans retains restoration potential through silvofisheries.

## Project layout

```
chakaria_mangrove_productivity/
├── config.py
├── run_pipeline.py
├── gee_extract.js              # Code Editor backup
├── requirements.txt
├── data/
│   └── sites.csv               # 30 field sites
├── scripts/
│   ├── 01_extract_gee.py       # GEE / geemap extraction
│   ├── 02_temporal_metrics.py  # Mean, SD, TS, Sen, MK
│   ├── 03_statistics.py        # Kruskal + post-hoc
│   ├── 04_figures.py           # Figures 1–4
│   └── make_demo_data.py       # Offline synthetic series
└── outputs/
    ├── tables/
    └── figures/
```

## Quick start in Cursor (offline demo)

No Earth Engine credentials required:

```bash
cd chakaria_mangrove_productivity
pip install -r requirements.txt
python run_pipeline.py
```

This writes:

- `data/annual_ugpp.csv`
- `outputs/tables/site_metrics.csv`
- `outputs/tables/kruskal_wallis.csv`
- `outputs/tables/dunn_posthoc.csv`
- `outputs/figures/Figure1_….png` … `Figure4_….png`

## Real GEE extraction

1. Authenticate once:

```bash
earthengine authenticate
# optional: set a Cloud project
# export EARTHENGINE_PROJECT=your-gcp-project
```

2. Extract + analyse:

```bash
python run_pipeline.py --gee --project YOUR_GCP_PROJECT
```

Or step-by-step:

```bash
python scripts/01_extract_gee.py --project YOUR_GCP_PROJECT
python scripts/02_temporal_metrics.py
python scripts/03_statistics.py
python scripts/04_figures.py
```

For large / slow client pulls, start a Drive export instead:

```bash
python scripts/01_extract_gee.py --export-drive --project YOUR_GCP_PROJECT
```

Download `Chakaria_uGPP_TimeSeries.csv`, place it at `data/annual_ugpp.csv`, then run scripts 02–04.

## GEE Code Editor alternative

Paste `gee_extract.js` into the [Earth Engine Code Editor](https://code.earthengine.google.com/), run, and start the two export tasks. Then continue in Python from `data/annual_ugpp.csv`.

## Interactive map (geemap)

Open `chakaria_ugpp_analysis.ipynb` (repo root) or, from the project directory:

```python
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "extract", Path("scripts/01_extract_gee.py")
)
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)

extract.initialize_ee()  # or extract.initialize_ee("YOUR_GCP_PROJECT")
sites = extract.load_sites()
m = extract.build_map(sites)
m
```

## Evidence chain for the manuscript

```
Long-term productivity (Mean uGPP)
        +
Temporal stability (Mean / SD)
        +
Positive Sen slope + Kendall Tau
        +
Comparable RMSP / PMSP / PMWSP performance
        ↓
Ecological function persists in former Chakaria Sundarbans
        ↓
Silvofisheries as climate–biodiversity–livelihood pathway
```

## R post-hoc (optional)

If you prefer the exact R workflow after exporting site metrics:

```r
df <- read.csv("outputs/tables/site_metrics.csv")
kruskal.test(Temporal_Stability ~ Group, data = df)
kruskal.test(Sen_Slope ~ Group, data = df)
kruskal.test(Mean_uGPP ~ Group, data = df)

library(FSA)
dunnTest(Temporal_Stability ~ Group, data = df)
dunnTest(Sen_Slope ~ Group, data = df)
dunnTest(Mean_uGPP ~ Group, data = df)
```

## Notes

- uGPP units follow the GPW catalog (typically gC m⁻² yr⁻¹); confirm against the asset metadata before final reporting.
- Temporal stability is undefined when SD = 0; those sites are dropped from stability comparisons.
- Demo data are synthetic and only for testing the pipeline — do not use them in the paper.
