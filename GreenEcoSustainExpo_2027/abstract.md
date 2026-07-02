# Conference Abstract — GreenEcoSustainExpo-2027

**Event:** Global Conference & Expo on Green Manufacturing, Circular Economy & Sustainable Development (GreenEcoSustainExpo-2027)  
**Dates:** 22–24 March 2027  
**Location:** Tokyo, Japan  
**Website:** https://greenmanufacturing.theinfiniteminds.net/

---

## Title

**Mangrove Forest Resilience to Cyclone Disturbances and Recurring Compound Climate Stress in the Sundarbans: A Remote Sensing and Plot-Level Analysis (2000–2024)**

---

## Authors

[Author names and affiliations to be added]

---

## Track / Theme

- Climate Change Mitigation
- Sustainable Development Goals (SDGs) — SDG 13 (Climate Action), SDG 14 (Life Below Water), SDG 15 (Life on Land)
- Environmental Policy and Ecosystem-Based Adaptation

---

## Abstract (≈300 words)

The Sundarbans, the world's largest contiguous mangrove forest, provides critical coastal protection, carbon storage, and livelihoods for millions, yet faces intensifying cyclone impacts and compound tropical climate stressors. This study integrates 24 years of MODIS-based kernel Normalized Difference Vegetation Index (kNDVI) time series (2000–2024, 250 m, 16-day) with ETH canopy height data and plot-level field measurements across 100 monitoring sites to quantify mangrove forest resilience to cyclone disturbances and recurring compound stress under extreme tropical climate conditions.

We applied STL decomposition, derivative-based perturbation detection (24-timestep window, 95th-percentile threshold), and exponential recovery curve fitting (up to 5 years post-disturbance) to characterize vegetation dynamics across 33 tracked cyclone events, including major impacts from Sidr (2007), Aila (2009), Amphan (2020), and Remal (2024). Resilience metrics include perturbation frequency (PF), accumulated disturbance index (ADI), and weighted accumulated disturbance (WAD), mapped spatially across West, Central, and East Sundarbans regions.

At the plot level, we constructed humid-heat and compound stress indices combining mean annual temperature, precipitation, salinity, and sulfide exposure to examine how co-occurring tropical stressors propagate recurring disturbance regimes. Significant relationships (p < 0.05, n = 100) emerged between higher mean annual precipitation and lower perturbation frequency (r = −0.34), between sulfide concentrations and recovery-rate metrics (λ_AC1, λ_variance; |r| up to 0.43), and between humid-heat exposure and reduced perturbation frequency (r = −0.27). Spatial analysis revealed heterogeneous resilience patterns linked to baseline kNDVI, canopy height, and regional position.

These findings demonstrate that mangrove resilience in the Sundarbans is shaped by both acute cyclone disturbances and chronic compound climate stress, with implications for ecosystem-based coastal adaptation, blue-carbon conservation policy, and sustainable development planning in climate-vulnerable delta systems. We discuss pathways for integrating remote sensing resilience metrics into regional environmental governance and SDG monitoring frameworks.

---

## Keywords

Mangrove resilience; Sundarbans; kNDVI; cyclone disturbance; compound climate stress; humid heat; remote sensing; ecosystem-based adaptation; sustainable development; coastal blue carbon

---

## Presentation Format

Oral presentation (preferred) or poster

---

## Supporting Materials in This Repository

| Resource | Description |
|----------|-------------|
| `Figs_resilience03022026.ipynb` | Full analysis pipeline: time series, spatial maps, recovery fits |
| `compound_stress_analysis.py` | Plot-level humid-heat and compound stress propagation analysis |
| `Data_Mangrove_resilience_Sundarbans.xlsx` | 100-plot field and resilience metric dataset |
| `compound_stress_output/` | Generated figures and correlation tables (run script to regenerate) |

---

## Suggested Figures for Submission

1. **Figure 1** — kNDVI time series with perturbation detection and exponential recovery fits (notebook Cell 1)
2. **Figure 2** — Spatial maps of perturbation frequency, ADI, and WAD (notebook Cell 2)
3. **Figure 3** — Compound stress propagation scatter plots (`compound_stress_output/compound_stress_propagation.png`)

---

## Data Availability

Analysis code and plot-level summary data are available in this repository. Full MODIS kNDVI rasters and shapefiles require separate data access (Google Drive paths documented in the notebook).
