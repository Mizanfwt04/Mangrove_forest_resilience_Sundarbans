"""
AGB Temporal Stability — Global Tropical Forest (Python / Earth Engine)

Metric: stability = mean(AGB) / SD(AGB)  (higher = more temporally stable)

Data: CTREES Global AGB 100 m (projects/sat-io/open-datasets/CTREES-GLOBAL-AGB-100M)

Masks (all required):
  1. WWF tropical forest biomes
  2. ESA WorldCover v200 — tree cover or mangroves, exclude permanent water
  3. Hansen GFC — >=30% tree cover in 2000, no loss through 2023
  4. JRC Global Surface Water — occurrence < 10%
  5. Mean AGB >= 10 Mg/ha

Usage:
  pip install earthengine-api geemap rasterio matplotlib cartopy geopandas

  # Authenticate once (browser):
  earthengine authenticate

  python scripts/agb_stability_tropical_forest.py --region amazon
  python scripts/agb_stability_tropical_forest.py --export --output-dir ./outputs
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import ee
import geemap
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap
from rasterio.transform import from_bounds

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

START_DATE = "2000-01-01"
END_DATE = "2025-12-31"

TREE_COVER_MIN_PCT = 30
WATER_OCCURRENCE_MAX = 10
MIN_MEAN_AGB = 10  # Mg/ha

EXPORT_SCALE = 100  # metres; CTREES native resolution is 100 m

REGIONS = {
    "global_tropics": {"bounds": [-180, -35, 180, 35], "label": "Global tropics"},
    "amazon": {"bounds": [-80, -25, -35, 15], "label": "Amazon"},
    "congo": {"bounds": [5, -10, 35, 10], "label": "Congo Basin"},
    "southeast_asia": {"bounds": [90, -15, 145, 25], "label": "Southeast Asia"},
    "sundarbans": {"bounds": [87.5, 20.5, 90.5, 23.0], "label": "Sundarbans"},
}

STABILITY_PALETTE = ["#253494", "#2c7fb8", "#41b6c4", "#a1dab4", "#ffffcc"]


# -----------------------------------------------------------------------------
# EARTH ENGINE PROCESSING
# -----------------------------------------------------------------------------

def initialize_ee(project: str | None = None) -> None:
    """Initialize Earth Engine. Pass --project if your account uses a GCP project."""
    try:
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()
    except ee.EEException as exc:
        raise RuntimeError(
            "Earth Engine not initialized. Run: earthengine authenticate"
        ) from exc


def rescale_agb(image: ee.Image) -> ee.Image:
    scaled = image.multiply(image.getNumber("agb_scale_factor"))
    return scaled.updateMask(scaled.gt(0)).copyProperties(image, image.propertyNames())


def build_agb_stability_stack() -> dict[str, ee.Image]:
    """Compute mean AGB, SD AGB, and stability (mean/SD) from CTREES."""
    collection = ee.ImageCollection("projects/sat-io/open-datasets/CTREES-GLOBAL-AGB-100M")

    filtered = collection.filterDate(START_DATE, END_DATE).map(rescale_agb)

    mean_agb = filtered.select("agb").mean().rename("agb_mean")
    sd_agb = filtered.select("agb").reduce(ee.Reducer.stdDev()).rename("agb_sd")
    stability = (
        mean_agb.divide(sd_agb).rename("agb_stability").updateMask(sd_agb.gt(0))
    )

    return {"mean": mean_agb, "sd": sd_agb, "stability": stability}


def build_analysis_mask(mean_agb: ee.Image) -> ee.Image:
    """Forest-only, stable-land mask stack for global tropical forest."""
    ecoregions = ee.FeatureCollection("RESOLVE/ECOREGIONS/2017")
    tropical_forests = ecoregions.filter(
        ee.Filter.inList(
            "BIOME_NAME",
            [
                "Tropical & Subtropical Moist Broadleaf Forests",
                "Tropical & Subtropical Dry Broadleaf Forests",
                "Tropical & Subtropical Coniferous Forests",
            ],
        )
    )
    tropical_biome_mask = ee.Image().paint(tropical_forests, 1).selfMask()

    world_cover = ee.Image("ESA/WorldCover/v200").select("Map")
    wc_forest = world_cover.eq(10).or(world_cover.eq(95))
    wc_not_water = world_cover.neq(80)
    world_cover_mask = wc_forest.And(wc_not_water)

    hansen = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")
    forest_2000 = hansen.select("treecover2000").gte(TREE_COVER_MIN_PCT)
    no_loss = hansen.select("lossyear").eq(0)
    stable_forest_mask = forest_2000.And(no_loss)

    jrc_water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")
    not_water_mask = jrc_water.lt(WATER_OCCURRENCE_MAX)

    return (
        tropical_biome_mask.And(world_cover_mask)
        .And(stable_forest_mask)
        .And(not_water_mask)
        .And(mean_agb.gte(MIN_MEAN_AGB))
    )


def get_stability_vmin_vmax(
    stability_masked: ee.Image, region: ee.Geometry, scale: int = 1000
) -> tuple[float, float]:
    stats = stability_masked.reduceRegion(
        reducer=ee.Reducer.percentile([2, 98]),
        geometry=region,
        scale=scale,
        maxPixels=int(1e13),
        bestEffort=True,
    ).getInfo()

    vmin = stats.get("agb_stability_p2", 0)
    vmax = stats.get("agb_stability_p98", 10)
    return float(vmin), float(vmax)


def export_geotiff(
    image: ee.Image,
    region: ee.Geometry,
    out_path: str | Path,
    scale: int = EXPORT_SCALE,
) -> Path:
    """Download a single-band EE image to local GeoTIFF."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    geemap.ee_export_image(
        image,
        filename=str(out_path),
        scale=scale,
        region=region,
        file_per_band=False,
    )
    return out_path


# -----------------------------------------------------------------------------
# LOCAL PLOTTING (matches notebook style: rasterio + matplotlib)
# -----------------------------------------------------------------------------

def plot_stability_map(
    tif_path: str | Path,
    title: str,
    out_png: str | Path | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    """Plot a stability GeoTIFF with the same blue→yellow palette as the GEE script."""
    with rasterio.open(tif_path) as src:
        data = src.read(1).astype(float)
        nodata = src.nodata
        if nodata is not None:
            data[data == nodata] = np.nan
        bounds = src.bounds

    valid = np.isfinite(data)
    if vmin is None:
        vmin = float(np.nanpercentile(data[valid], 2)) if valid.any() else 0
    if vmax is None:
        vmax = float(np.nanpercentile(data[valid], 98)) if valid.any() else 10

    cmap = LinearSegmentedColormap.from_list("stability", STABILITY_PALETTE, N=256)

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(
        data,
        extent=[bounds.left, bounds.right, bounds.bottom, bounds.top],
        origin="upper",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        interpolation="none",
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title, fontsize=14, fontweight="bold")
    cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("AGB stability (mean / SD)", rotation=90, labelpad=15)
    plt.tight_layout()

    if out_png:
        plt.savefig(out_png, dpi=300, bbox_inches="tight")
        print(f"Saved figure: {out_png}")
    else:
        plt.show()
    plt.close()


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Global tropical forest AGB temporal stability (CTREES, Python)"
    )
    parser.add_argument(
        "--region",
        choices=list(REGIONS.keys()),
        default="amazon",
        help="Predefined export/plot region (default: amazon)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="GCP project ID for Earth Engine (optional)",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export GeoTIFFs to --output-dir",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Plot stability map after export",
    )
    parser.add_argument(
        "--output-dir",
        default="./outputs/agb_stability",
        help="Output directory for GeoTIFFs and figures",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=EXPORT_SCALE,
        help=f"Export scale in metres (default: {EXPORT_SCALE})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_ee(project=args.project)

    region_info = REGIONS[args.region]
    region = ee.Geometry.Rectangle(region_info["bounds"])
    label = region_info["label"]

    print("Building CTREES AGB stack...")
    stack = build_agb_stability_stack()
    mask = build_analysis_mask(stack["mean"])

    stability_masked = stack["stability"].updateMask(mask)
    mean_masked = stack["mean"].updateMask(mask)
    sd_masked = stack["sd"].updateMask(mask)

    vmin, vmax = get_stability_vmin_vmax(stability_masked, region)
    print(f"Stability stretch (p2–p98) for {label}: {vmin:.2f} – {vmax:.2f}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.export:
        print(f"Exporting to {out_dir} at {args.scale} m...")
        export_geotiff(
            stability_masked.float(),
            region,
            out_dir / f"agb_stability_{args.region}.tif",
            scale=args.scale,
        )
        export_geotiff(
            mean_masked.float(),
            region,
            out_dir / f"agb_mean_{args.region}.tif",
            scale=args.scale,
        )
        export_geotiff(
            sd_masked.float(),
            region,
            out_dir / f"agb_sd_{args.region}.tif",
            scale=args.scale,
        )
        print("Export complete.")

    if args.plot:
        stability_tif = out_dir / f"agb_stability_{args.region}.tif"
        if not stability_tif.exists():
            print("Stability GeoTIFF not found — running export first.")
            export_geotiff(
                stability_masked.float(),
                region,
                stability_tif,
                scale=args.scale,
            )
        plot_stability_map(
            stability_tif,
            title=f"AGB Stability (mean/SD) — stable tropical forest\n{label}",
            out_png=out_dir / f"agb_stability_{args.region}.png",
            vmin=vmin,
            vmax=vmax,
        )

    if not args.export and not args.plot:
        print("Nothing to do. Pass --export and/or --plot.")
        print("Example:")
        print("  python scripts/agb_stability_tropical_forest.py --region amazon --export --plot")


if __name__ == "__main__":
    main()
