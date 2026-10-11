# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
A single-product **research / data-analysis** repo (no servers, no database, no web/API, nothing to "serve"). The deliverable is one Jupyter notebook, `Figs_resilience03022026.ipynb`, that analyzes mangrove-forest resilience in the Sundarbans from MODIS kNDVI time series and produces paper figures. There are no lint, test, or build systems configured.

### Environment
- Python 3.12. Dependencies are listed in `requirements.txt` and installed by the startup update script.
- This is a PEP 668 "externally managed" environment, so pip needs `--break-system-packages`. Packages land in `/usr/local/lib/python3.12/dist-packages`; console-script shims (e.g. `jupyter`) land in `~/.local/bin`, which is **not on `PATH`**. Invoke tools as modules instead: `python3 -m jupyter ...`, `python3 -m nbconvert ...` (or prepend `~/.local/bin` to `PATH`).

### Running the notebook
- Interactive: `python3 -m jupyter lab` (or `notebook`).
- Headless: `python3 -m nbconvert --to notebook --execute Figs_resilience03022026.ipynb`.
- Important: the notebook is **Google Colab–oriented** — it uses `from google.colab import drive` and hard-coded `/content/drive/MyDrive/...` paths, and it depends on large external MODIS rasters / a Sundarbans shapefile / a KMZ that are **not in this repo**. It therefore cannot be executed end-to-end here without obtaining that data and rewriting the hard-coded paths. The only in-repo data is `Data_Mangrove_resilience_Sundarbans.xlsx` (plot-level summary for 100 plots, not the raw kNDVI rasters).

### Non-obvious gotcha (scipy)
`detect_perturbations()` feeds an array containing NaN edges into `scipy.signal.savgol_filter`. Modern `scipy` (>=1.x, installed here) raises `ValueError: array must not contain infs or NaNs`; the original Colab scipy tolerated NaNs. When running that code locally, interpolate/fill NaNs before the `savgol_filter` call.

### Verifying the environment works
Because the real rasters are absent, the way to smoke-test the full scientific stack is to run the notebook's core functions (rasterio raster I/O → pixel extraction → STL + harmonic decomposition → Savitzky-Golay perturbation detection → exponential recovery fit → AR1/variance) on a synthetic kNDVI stack. Confirm imports first: `python3 -c "import numpy, pandas, rasterio, geopandas, cartopy, statsmodels, sklearn, scipy; from matplotlib_scalebar.scalebar import ScaleBar"`.
