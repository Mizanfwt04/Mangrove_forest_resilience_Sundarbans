# Tropical Forest Carbon Stability Pipeline

End-to-end code for studying whether **functional traits mediate** the effect of **compound water stress** (VPD + soil moisture deficit) on **temporal stability of forest aboveground carbon** in tropical moist forests.

## Study design

| Component | Source | Resolution |
|-----------|--------|------------|
| Forest carbon stability | CTrees AGB 2000–2025 | 100 m → sampled at 1 km |
| Climate extremes | TerraClimate | ~4 km |
| Functional traits | Lusk et al. 2026 (sPlot + GBIF + TRY) | 1 km |
| Study region | RESOLVE ecoregions | Tropical & Subtropical Moist Broadleaf Forests |
| Sample size | ~1000 stratified points | From ~5000 GEE candidates |

**Stability metric:** `mean(annual AGB) / SD(annual AGB)` per point (2000–2025)

**Compound climate variables:**
- `vpd_p95` — 95th percentile VPD
- `soil_deficit` — 1 − (min soil moisture / mean soil moisture)
- `def_mean` — climatic water deficit
- `water_stress` — z-scored composite (used in mediation)

## Quick start (Google Colab — recommended)

1. Upload this repo folder to Colab (or clone from GitHub).
2. Open `tropical_forest_stability_analysis.ipynb`.
3. Run all cells — authenticate Earth Engine when prompted.
4. Outputs saved to `outputs/`:
   - `tropical_forest_points_raw.csv`
   - `tropical_forest_points_1000.csv`
   - `sem_mediation_results.csv`
   - `figures/`

## Alternative: Earth Engine Code Editor

If Colab `getInfo()` times out:

1. Open [Google Earth Engine Code Editor](https://code.earthengine.google.com/)
2. Paste `tropical_forest_stability/gee_extract.js`
3. Run → Export CSV to Google Drive
4. Download and run analysis:

```bash
pip install -r tropical_forest_stability/requirements.txt
cd tropical_forest_stability
python analysis.py  # after placing CSV at outputs/tropical_forest_points_raw.csv
```

## File structure

```
tropical_forest_stability/
  config.py          # parameters (biome, years, traits, paths)
  gee_extract.py     # Python Earth Engine extraction
  gee_extract.js     # JavaScript Earth Engine extraction (backup)
  analysis.py        # stratified sampling + mediation SEM
  requirements.txt
tropical_forest_stability_analysis.ipynb   # main Colab notebook
outputs/                                   # created on run
```

## Customize

Edit `tropical_forest_stability/config.py`:

```python
N_TARGET_POINTS = 1000
BIOME_NAME = "Tropical & Subtropical Moist Broadleaf Forests"
TRAITS = {"SLA": "sla_m2_kg", "SSD": "ssd_g_cm3", ...}
```

## Citations

- Lusk et al. 2026 trait maps: https://doi.org/10.1038/s41467-026-68996-y
- CTrees AGB: https://doi.org/10.82924/7vmb-zv66
- TerraClimate: Abatzoglou et al. 2018 Scientific Data
- RESOLVE ecoregions: Dinerstein et al. 2017

## Notes

- Trait maps are **static** (community-weighted means); mediation assumes traits represent long-term community context.
- Filter by **Area of Applicability (AOA = 1)** for reliable trait pixels.
- CTrees is a **preprint** product (2026); cite accordingly.
- For publication, add spatial block cross-validation and sensitivity tests (see `analysis.py`).
