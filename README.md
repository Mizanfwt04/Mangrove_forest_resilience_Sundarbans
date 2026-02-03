# Mangrove Forest Resilience Analysis - Sundarbans

This repository contains the code for analyzing mangrove forest resilience in the Sundarbans region using satellite remote sensing data (MODIS).

## Overview

This project analyzes the resilience of mangrove forests in the Sundarbans to cyclone disturbances using kernel Normalized Difference Vegetation Index (kNDVI) time series data from 2000-2024. The analysis includes perturbation detection, recovery dynamics, and spatial mapping of disturbance indices.

## Research Objectives

- Assess mangrove forest resilience to cyclone disturbances in the Sundarbans
- Detect and quantify perturbations in vegetation health using kNDVI time series
- Analyze recovery patterns following disturbance events
- Map spatial patterns of disturbance frequency and intensity
- Evaluate resilience metrics across different regions (West, Central, East)

## Data Sources

- **Vegetation Index**: MODIS Surface Reflectance-based kNDVI (2000-2024) at 250m resolution, 16-day temporal resolution
- **Canopy Height**: ETH Canopy Height data (2020) at 250m resolution
- **Study Area**: Sundarbans shapefile delineating mangrove boundaries
- **Reference Sites**: KMZ file with resilience study sites

## Key Features

### 1. Time Series Analysis
- STL (Seasonal-Trend decomposition using Loess) for trend and seasonal extraction
- Rolling mean smoothing for noise reduction
- Harmonic regression for seasonal pattern analysis
- Baseline kNDVI calculation for resilience classification

### 2. Perturbation Detection
- Automated detection of vegetation disturbances using derivative-based methods
- Savitzky-Golay filtering for smooth derivative calculation
- Configurable window size (24 timesteps) and percentile threshold (95%)
- Minimum drop threshold (0.01) for valid perturbations

### 3. Recovery Analysis
- Exponential recovery curve fitting
- Recovery rate quantification
- R² goodness-of-fit assessment
- Maximum recovery period: 5 years

### 4. Resilience Metrics
- **Perturbation Frequency**: Count of disturbance events per pixel
- **Disturbance Index (AD)**: Accumulated drop magnitude
- **Weighted Index (WAD)**: Weighted accumulated drop considering recovery dynamics

### 5. Event Analysis
- **Cyclone Events**: 33 tracked cyclones from 2000-2024 including major events (Sidr 2007, Aila 2009, Amphan 2020, Remal 2024)
- **ENSO Events**: El Niño and La Niña events (note: currently not used in analysis)

### 6. Spatial Analysis
- Regional classification (West, Central, East based on longitude)
- Canopy height integration
- Resilience status classification:
  - **Resilient**: kNDVI > 0.49
  - **Moderately resilient**: kNDVI 0.39-0.49
  - **Low resilient**: kNDVI < 0.39

## Code Structure

### Main Notebook: `Figs_resilience03022026.ipynb`

**Cell 1**: Data loading, preprocessing, and time series analysis
- Library imports and setup
- Event definitions (cyclones, ENSO)
- Perturbation detection and recovery fitting functions
- Point-wise time series extraction and analysis
- Resilience metrics calculation

**Cell 2**: Figure 2 - Spatial maps generation
- Perturbation frequency map
- Disturbance Index (AD) map
- Weighted Index (WAD) map
- Uses Cartopy for geographic projections and Matplotlib for visualization

**Cell 3**: Additional analysis and visualization
- Further spatial analysis
- Statistical assessments
- Visualization enhancements

## Requirements

```
rasterio
geopandas
statsmodels
scikit-learn
matplotlib
matplotlib-scalebar
cartopy
scipy
numpy
pandas
```

## Installation

```bash
pip install rasterio geopandas statsmodels scikit-learn matplotlib matplotlib-scalebar cartopy scipy numpy pandas
```

## Usage

1. **Configure file paths**: Update the following paths in the notebook to match your data location:
   ```python
   stack_kndvi_fp = "path/to/SRF_kNDVI_2000_2024.tif"
   canopy_fp = "path/to/SRF_ETH_CanopyHeight_StableLand_2020_250m.tif"
   sundarbans_fp = "path/to/Sundarbans_Shapefile_Export.shp"
   kmz_path = "path/to/RSTCSITE_SUNDARBANS.kmz"
   ```

2. **Run the notebook**: Execute cells sequentially to:
   - Load and preprocess data
   - Extract time series for analysis points
   - Detect perturbations and analyze recovery
   - Generate spatial maps and visualizations

3. **Outputs**: 
   - Time series plots with perturbation markers
   - Recovery curve fits
   - Spatial maps of resilience indices
   - Statistical summaries

## Methodology

### Perturbation Detection Algorithm
1. Calculate residuals from detrended time series
2. Compute average derivative using sliding window (24 timesteps)
3. Apply Savitzky-Golay filter for smoothing
4. Identify local maxima exceeding 95th percentile
5. Validate perturbations with minimum drop threshold (0.01)

### Recovery Analysis
1. Extract post-perturbation time series (up to 5 years)
2. Fit exponential recovery model: y = a × exp(b × t)
3. Calculate R² for goodness-of-fit
4. Estimate recovery rate from parameter b

### Resilience Classification
- Based on baseline kNDVI (year 2000)
- Accounts for spatial heterogeneity
- Integrates canopy height information

## Output Figures

- **Figure 1**: Time series analysis showing kNDVI trends, perturbations, and recovery curves
- **Figure 2**: Spatial maps of perturbation frequency, Disturbance Index, and Weighted Index
- **Figure 3**: Additional spatial and temporal analysis visualizations

## Study Area

**Sundarbans**: The world's largest mangrove forest, spanning Bangladesh and India, vulnerable to frequent cyclone impacts. The study focuses on understanding resilience patterns across three regions:
- **West**: Lon < 89.3°
- **Central**: 89.3° ≤ Lon < 89.6°
- **East**: Lon ≥ 89.6°

## Author

This code is part of a research paper on mangrove forest resilience to cyclone disturbances in the Sundarbans.

## Citation

If you use this code in your research, please cite the associated publication:

[Citation information to be added upon publication]

## License

[Specify license if applicable]

## Contact

[Add contact information if desired]

## Acknowledgments

- MODIS data from NASA Earth Observations
- ETH Canopy Height data
- Study site coordinates from field surveys
