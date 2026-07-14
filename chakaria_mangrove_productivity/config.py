"""Configuration for Chakaria remanent mangrove uGPP productivity analysis."""

from __future__ import annotations

from pathlib import Path

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"

SITES_CSV = DATA_DIR / "sites.csv"
# Study-area polygon. Copy from:
#   D:\A_letter_to_Science\chakaria_boundary.geojson
BOUNDARY_GEOJSON = DATA_DIR / "chakaria_boundary.geojson"
ANNUAL_UGPP_CSV = DATA_DIR / "annual_ugpp.csv"
SITE_METRICS_CSV = TABLES_DIR / "site_metrics.csv"
GROUP_SUMMARY_CSV = TABLES_DIR / "group_summary.csv"
KRUSKAL_CSV = TABLES_DIR / "kruskal_wallis.csv"
DUNN_CSV = TABLES_DIR / "dunn_posthoc.csv"

# -----------------------------------------------------------------------------
# Study design
# -----------------------------------------------------------------------------

# Global Pasture Watch annual ungrazed GPP (gC m-2 yr-1), ~30 m
UGPP_COLLECTION = "projects/global-pasture-watch/assets/ggpp-30m/v1/ugpp_m"

START_YEAR = 2000
END_YEAR = 2024

# Buffer (m) around each site point for reduceRegion
BUFFER_M = 60
SCALE_M = 30
MAX_PIXELS = int(1e13)

GROUPS = ("RMSP", "PMSP", "PMWSP")
GROUP_LABELS = {
    "RMSP": "Remanent mangrove in shrimp ponds",
    "PMSP": "Planted mangrove in shrimp ponds",
    "PMWSP": "Protected mangrove without shrimp ponds",
}

# Metrics tested across groups
METRIC_COLS = (
    "Mean_uGPP",
    "Temporal_Stability",
    "Sen_Slope",
    "Kendall_Tau",
)

# Plot aesthetics
GROUP_COLORS = {
    "RMSP": "#1b9e77",
    "PMSP": "#d95f02",
    "PMWSP": "#7570b3",
}

FIGURE_DPI = 600
RANDOM_SEED = 42
