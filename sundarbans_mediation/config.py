"""Configuration for Sundarbans resilience mediation analysis."""

from __future__ import annotations

# Plot-level data (Box-Cox z-scored sheet used in the published SEM)
DATA_XLSX = "../Data_Mangrove_resilience_Sundarbans.xlsx"
DATA_SHEET = "Boxcoxtransformed_zscore"

# Resilience outcomes (λ from variance or AC1)
OUTCOME_DEFAULT = "lambda_va_py"
OUTCOME_ALT = "lambda_ac1_py"

# Mean climate (CHELSA climatology in original study)
MEAN_CLIMATE = {"MAP": "MAP", "MAT": "MAT"}

# Extreme / compound climate columns (add after GEE extraction)
EXTREME_CLIMATE = {
    "tmax_p95": "Annual max temperature 95th percentile (°C)",
    "tmax_p99": "Annual max temperature 99th percentile (°C)",
    "pr_p05": "Annual precipitation 5th percentile (dry-year intensity, mm)",
    "pr_cv": "Interannual precipitation coefficient of variation",
    "vpd_p95": "Vapor pressure deficit 95th percentile (kPa)",
    "pdsi_min": "Minimum Palmer Drought Severity Index",
    "heatwave_days": "Days per year above local 90th percentile Tmax",
    "dry_spell_max": "Longest consecutive months with pr < 20th percentile",
}

# Biotic mediators (functional composition / diversity / structure)
BIOTIC_MEDIATORS = {
    "CWM.MCH": "Functional composition — maximum canopy height",
    "CWM.SLA": "Functional composition — specific leaf area",
    "FDis.LS": "Functional diversity — leaf succulence",
    "DBHvar": "Structural diversity (DBH coefficient of variation)",
    "nbsp": "Species richness",
}

# Soil / sediment mediators
SOIL_MEDIATORS = {
    "SALINITY": "Sediment salinity",
    "P": "Sediment phosphorus",
    "PH": "Sediment pH",
    "SILT": "Sediment texture (silt %)",
    "SULFIDE": "Sediment sulfide",
    "FE": "Sediment iron",
}

# Disturbance proxy (remote-sensing perturbation count)
DISTURBANCE = "PF"

OUTPUT_DIR = "outputs"
MEDIATION_CSV = f"{OUTPUT_DIR}/sundarbans_mediation_results.csv"
COMPARISON_CSV = f"{OUTPUT_DIR}/mean_vs_extreme_climate_comparison.csv"
FIGURES_DIR = f"{OUTPUT_DIR}/figures"

# GEE
SUNDARBANS_SHAPEFILE = None  # set path if available
TERRACLIMATE_COLLECTION = "IDAHO_EPSCOR/TERRACLIMATE"
CHELSA_TEMP = "projects/climatologies/chelsa/CHELSA_bio01_1980-2010_V2_1"
START_YEAR = 2000
END_YEAR = 2024
