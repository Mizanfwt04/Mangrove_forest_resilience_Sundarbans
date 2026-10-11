"""Configuration for tropical forest carbon stability analysis."""

from __future__ import annotations

# Study region
BIOME_NAME = "Tropical & Subtropical Moist Broadleaf Forests"
START_YEAR = 2000
END_YEAR = 2025

# Sampling
N_TARGET_POINTS = 1000
N_CANDIDATE_POINTS = 5000  # oversample, then stratify in Python
MIN_MEAN_AGB_MG_HA = 50.0  # forest mask threshold
RANDOM_SEED = 42

# Google Earth Engine asset IDs
ECOREGIONS_ASSET = "RESOLVE/ECOREGIONS/2017"
CTREES_AGB_COLLECTION = "projects/sat-io/open-datasets/CTREES-GLOBAL-AGB-100M"
TERRACLIMATE_COLLECTION = "IDAHO_EPSCOR/TERRACLIMATE"
TRAIT_BASE_PATH = "projects/sat-io/open-datasets/global-traits/Shrub_Tree_Grass"

# Traits to extract (GEE image suffix -> output column name)
# Only traits with Pearson r >= 0.5 in Lusk et al. 2026 (tropics-relevant)
TRAITS = {
    "SLA": "sla_m2_kg",
    "SSD": "ssd_g_cm3",
    "Rooting_depth": "rooting_depth_m",
    "Leaf_N_area": "leaf_n_area_g_m2",
    "Stem_conduit_diameter": "conduit_diameter_um",
}

# TerraClimate band scale factors (GEE catalog)
TERRACLIMATE_SCALES = {
    "vpd": 0.01,
    "soil": 1.0,
    "def": 0.1,
    "pdsi": 0.01,
    "pr": 1.0,
    "tmmx": 0.1,
}

# Output files
OUTPUT_DIR = "outputs"
POINTS_RAW_CSV = f"{OUTPUT_DIR}/tropical_forest_points_raw.csv"
POINTS_STRATIFIED_CSV = f"{OUTPUT_DIR}/tropical_forest_points_1000.csv"
SEM_RESULTS_CSV = f"{OUTPUT_DIR}/sem_mediation_results.csv"
FIGURES_DIR = f"{OUTPUT_DIR}/figures"
