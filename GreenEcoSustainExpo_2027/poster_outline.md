# Poster Outline — GreenEcoSustainExpo-2027

**Dimensions:** A0 portrait (841 × 1189 mm) or conference-specified size  
**Title:** Mangrove Forest Resilience to Cyclone Disturbances and Recurring Compound Climate Stress in the Sundarbans (2000–2024)

---

## Layout (4 columns)

### Column 1 — Introduction & Study Area

- **Background:** Sundarbans mangroves — largest mangrove ecosystem; cyclone-prone Bay of Bengal delta
- **Research gap:** How acute cyclone impacts interact with chronic humid-heat and chemical stressors
- **Map:** Study area with West / Central / East regions and 100 monitoring plots
- **Objectives:**
  1. Quantify perturbation and recovery dynamics from kNDVI time series
  2. Map spatial resilience indices (PF, ADI, WAD)
  3. Relate compound climate stress to recurring disturbance regimes

### Column 2 — Methods

- **Remote sensing:** MODIS kNDVI stack, 2000–2024, 250 m, 16-day composites
- **Ancillary data:** ETH canopy height (2020), Sundarbans boundary shapefile
- **Perturbation detection:** STL decomposition → Savitzky–Golay derivative → 95th-percentile threshold
- **Recovery fitting:** Exponential model y = a·exp(b·t), max 5 years
- **Compound stress indices:**
  - Humid-heat index = z(MAT) + z(MAP)
  - Compound stress = humid heat + z(salinity) + z(sulfide) − z(MAP)
- **Events:** 33 cyclones tracked (2000–2024)

### Column 3 — Results

- **Time series panel:** kNDVI trends, residuals, perturbation markers, recovery curves
- **Spatial maps:** PF, ADI, WAD across Sundarbans
- **Key statistics (n = 100 plots):**
  - MAP → PF: r = −0.34, p < 0.001
  - Sulfide → λ_variance: r = 0.43, p < 0.001
  - Humid-heat index → PF: r = −0.27, p = 0.006
- **Resilience classification:** Resilient (kNDVI > 0.49), Moderate (0.39–0.49), Low (< 0.39)

### Column 4 — Discussion & Conclusions

- **Findings:** Heterogeneous resilience driven by cyclone history, soil chemistry, and precipitation regime
- **Policy relevance:** Ecosystem-based adaptation; blue-carbon conservation; SDG 13/14/15 monitoring
- **Limitations:** kNDVI proxy; plot-level n = 100; ENSO effects not included
- **Future work:** Integrate sea-level rise projections; expand to Bangladesh sector
- **QR code:** Link to GitHub repository
- **Contact / Acknowledgments**

---

## Color Palette

- Primary greens for vegetation maps (`Greens` colormap)
- Red/yellow/green for resilience status classification
- Neutral background (#F5F5F5) for readability

---

## Files to Export from Notebook

Run `Figs_resilience03022026.ipynb` and `compound_stress_analysis.py` to generate high-resolution (300 dpi) figures for poster assembly.
