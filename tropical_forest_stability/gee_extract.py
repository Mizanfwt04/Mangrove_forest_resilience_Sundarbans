"""
Google Earth Engine extraction for tropical forest carbon stability study.

Run in Google Colab or locally after: earthengine authenticate
"""

from __future__ import annotations

import json
from typing import Any

import ee

from config import (
    BIOME_NAME,
    CTREES_AGB_COLLECTION,
    ECOREGIONS_ASSET,
    END_YEAR,
    MIN_MEAN_AGB_MG_HA,
    N_CANDIDATE_POINTS,
    RANDOM_SEED,
    START_YEAR,
    TERRACLIMATE_COLLECTION,
    TERRACLIMATE_SCALES,
    TRAIT_BASE_PATH,
    TRAITS,
)


def initialize_gee(project: str | None = None) -> None:
    """Initialize Earth Engine. Pass project= for high-volume exports."""
    try:
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()
    except Exception:
        ee.Authenticate()
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()


def get_tropical_moist_forest_geometry() -> ee.Geometry:
    """Union geometry of tropical moist broadleaf forest ecoregions."""
    ecoregions = ee.FeatureCollection(ECOREGIONS_ASSET)
    tropical = ecoregions.filter(ee.Filter.eq("BIOME_NAME", BIOME_NAME))
    return tropical.geometry().dissolve(maxError=1000)


def _rescale_ctrees_agb(image: ee.Image) -> ee.Image:
    scale = ee.Number(image.get("agb_scale_factor"))
    agb = image.select("agb").multiply(scale).rename("agb")
    return agb.updateMask(agb.gt(0)).copyProperties(image, ["year", "system:time_start"])


def build_agb_collection() -> ee.ImageCollection:
    col = (
        ee.ImageCollection(CTREES_AGB_COLLECTION)
        .filter(ee.Filter.calendarRange(START_YEAR, END_YEAR, "year"))
        .map(_rescale_ctrees_agb)
    )
    return col


def build_agb_stability_image(agb_col: ee.ImageCollection) -> ee.Image:
    """
    Temporal stability metrics from annual AGB (2000-2025).
    - agb_mean, agb_std, agb_cv, stability_mu_sigma (= mean/std)
    """
    mean = agb_col.mean().rename("agb_mean")
    std = agb_col.reduce(ee.Reducer.stdDev()).rename("agb_std")
    cv = std.divide(mean).rename("agb_cv")
    stability = mean.divide(std).rename("stability_mu_sigma")
    return ee.Image.cat([mean, std, cv, stability])


def _scale_terraclimate_band(image: ee.Image, band: str) -> ee.Image:
    scale = TERRACLIMATE_SCALES[band]
    return image.select(band).multiply(scale).rename(band)


def build_climate_composites() -> ee.Image:
    """
    Compound climate stress variables from TerraClimate (2000-2025).
    - vpd_mean, vpd_p95: atmospheric dryness
    - soil_min, soil_deficit: soil moisture stress
    - def_mean: climatic water deficit
    - pdsi_min: drought severity
    - pr_cv: precipitation interannual variability
    """
    tc = ee.ImageCollection(TERRACLIMATE_COLLECTION).filter(
        ee.Filter.calendarRange(START_YEAR, END_YEAR, "year")
    )

    vpd = tc.map(lambda img: _scale_terraclimate_band(img, "vpd"))
    soil = tc.map(lambda img: _scale_terraclimate_band(img, "soil"))
    deficit = tc.map(lambda img: _scale_terraclimate_band(img, "def"))
    pdsi = tc.map(lambda img: _scale_terraclimate_band(img, "pdsi"))
    pr = tc.map(lambda img: _scale_terraclimate_band(img, "pr"))

    vpd_p95 = vpd.reduce(ee.Reducer.percentile([95])).rename("vpd_p95")
    soil_min = soil.min().rename("soil_min")
    soil_mean = soil.mean().rename("soil_mean")
    def_mean = deficit.mean().rename("def_mean")
    pdsi_min = pdsi.min().rename("pdsi_min")

    pr_scaled = tc.map(lambda img: img.select("pr"))
    pr_mean = pr_scaled.mean().rename("pr_mean")
    pr_std = pr_scaled.reduce(ee.Reducer.stdDev())
    pr_cv = pr_std.divide(pr_mean).rename("pr_cv")

    # Soil moisture deficit: 1 - (min soil / mean soil), bounded
    soil_deficit = ee.Image(1).subtract(soil_min.divide(soil_mean)).clamp(0, 1).rename(
        "soil_deficit"
    )

    vpd_mean = vpd.mean().rename("vpd_mean")

    return ee.Image.cat(
        [
            vpd_mean,
            vpd_p95,
            soil_min,
            soil_mean,
            soil_deficit,
            def_mean,
            pdsi_min,
            pr_mean,
            pr_cv,
        ]
    )


def _rescale_trait_image(image: ee.Image) -> ee.Image:
    """Rescale trait band using image metadata."""
    scale = ee.Number(image.get("trait_scale"))
    offset = ee.Number(image.get("trait_offset"))
    trait = image.select("b1").multiply(scale).add(offset).rename("trait")
    aoa = image.select("b3").rename("aoa")
    return ee.Image.cat([trait, aoa])


def load_trait_image(trait_key: str) -> ee.Image:
    """Load a single trait raster from the GEE community catalog."""
    path = f"{TRAIT_BASE_PATH}/{trait_key}"
    image = ee.Image(path)
    scaled = _rescale_trait_image(image)
    return scaled.rename([trait_key, f"{trait_key}_aoa"])


def build_trait_stack() -> ee.Image:
    images = [load_trait_image(k) for k in TRAITS]
    return ee.Image.cat(images)


def build_analysis_image() -> ee.Image:
    """Full stack: AGB stability + climate + traits, masked to forest."""
    agb_col = build_agb_collection()
    stability = build_agb_stability_image(agb_col)
    climate = build_climate_composites()
    traits = build_trait_stack()

    forest_mask = stability.select("agb_mean").gte(MIN_MEAN_AGB_MG_HA)
    return stability.addBands(climate).addBands(traits).updateMask(forest_mask)


def sample_candidate_points(
    analysis_image: ee.Image,
    region: ee.Geometry,
    n_points: int = N_CANDIDATE_POINTS,
    seed: int = RANDOM_SEED,
) -> ee.FeatureCollection:
    """Random sample forest pixels across tropical moist forest biome."""
    return analysis_image.sample(
        region=region,
        scale=1000,  # 1 km aligned with trait maps
        numPixels=n_points,
        seed=seed,
        geometries=True,
        tileScale=4,
    )


def features_to_records(fc: ee.FeatureCollection) -> list[dict[str, Any]]:
    """Download feature collection to Python list (for moderate n only)."""
    features = fc.getInfo()["features"]
    records = []
    for feat in features:
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        row = {"lon": coords[0], "lat": coords[1], **props}
        records.append(row)
    return records


def export_to_drive(
    fc: ee.FeatureCollection,
    description: str = "tropical_forest_points",
    folder: str = "gee_exports",
    file_format: str = "CSV",
) -> ee.batch.Task:
    """Export sampled points to Google Drive (recommended for large jobs)."""
    task = ee.batch.Export.table.toDrive(
        collection=fc,
        description=description,
        folder=folder,
        fileFormat=file_format,
    )
    task.start()
    return task


def run_extraction_local(
    project: str | None = None,
    n_points: int = N_CANDIDATE_POINTS,
) -> list[dict[str, Any]]:
    """
    Full extraction pipeline returning records in memory.
    Use only for <= ~5000 points; otherwise use export_to_drive().
    """
    initialize_gee(project=project)
    region = get_tropical_moist_forest_geometry()
    image = build_analysis_image()
    fc = sample_candidate_points(image, region, n_points=n_points)
    return features_to_records(fc)


if __name__ == "__main__":
    import pandas as pd
    from pathlib import Path

    from config import OUTPUT_DIR, POINTS_RAW_CSV

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    print("Initializing GEE and extracting candidate points...")
    records = run_extraction_local()
    df = pd.DataFrame(records)
    df.to_csv(POINTS_RAW_CSV, index=False)
    print(f"Saved {len(df)} points to {POINTS_RAW_CSV}")
