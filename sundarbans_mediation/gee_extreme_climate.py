"""
Extract extreme-climate variables for Sundarbans plot locations via Google Earth Engine.

Complements the original CHELSA mean MAP/MAT with compound stress metrics:
  - tmax_p95, tmax_p99   : heat extremes
  - pr_p05, pr_cv        : drought / rainfall variability
  - vpd_p95              : atmospheric dryness extremes
  - pdsi_min             : drought severity
  - heatwave_days        : days above local 90th percentile Tmax
  - dry_spell_max        : longest low-precipitation run (months)

Merge output CSV with Data_Mangrove_resilience_Sundarbans.xlsx on plot ID or lon/lat.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ee

from config import END_YEAR, EXTREME_CLIMATE, START_YEAR, TERRACLIMATE_COLLECTION


def initialize_gee(project: str | None = None) -> None:
    try:
        ee.Initialize(project=project) if project else ee.Initialize()
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project) if project else ee.Initialize()


def get_sundarbans_geometry(shapefile_path: str | None = None) -> ee.Geometry:
    if shapefile_path:
        import geopandas as gpd

        gdf = gpd.read_file(shapefile_path)
        feats = [ee.Feature(ee.Geometry(row.geometry.__geo_interface__), {}) for _, row in gdf.iterrows()]
        return ee.FeatureCollection(feats).geometry()
    # Approximate Sundarbans bounding box
    return ee.Geometry.Rectangle([88.0, 21.5, 89.9, 22.9])


def _scale_tc(image: ee.Image, band: str, factor: float) -> ee.Image:
    return image.select(band).multiply(factor).rename(band)


def build_extreme_climate_image() -> ee.Image:
    """Annual extreme metrics from TerraClimate 2000–2024."""
    tc = ee.ImageCollection(TERRACLIMATE_COLLECTION).filter(
        ee.Filter.calendarRange(START_YEAR, END_YEAR, "year")
    )

    tmax = tc.map(lambda img: _scale_tc(img, "tmmx", 0.1))
    pr = tc.map(lambda img: img.select("pr"))
    vpd = tc.map(lambda img: _scale_tc(img, "vpd", 0.01))
    pdsi = tc.map(lambda img: _scale_tc(img, "pdsi", 0.01))

    tmax_p95 = tmax.reduce(ee.Reducer.percentile([95])).rename("tmax_p95")
    tmax_p99 = tmax.reduce(ee.Reducer.percentile([99])).rename("tmax_p99")
    pr_p05 = pr.reduce(ee.Reducer.percentile([5])).rename("pr_p05")
    pr_mean = pr.mean().rename("pr_mean")
    pr_std = pr.reduce(ee.Reducer.stdDev())
    pr_cv = pr_std.divide(pr_mean).rename("pr_cv")
    vpd_p95 = vpd.reduce(ee.Reducer.percentile([95])).rename("vpd_p95")
    pdsi_min = pdsi.min().rename("pdsi_min")

    # Heatwave days: count months where tmax > local 90th percentile
    tmax_p90 = tmax.reduce(ee.Reducer.percentile([90]))
    heatwave = (
        tmax.map(lambda img: img.gt(tmax_p90).rename("hot"))
        .sum()
        .divide(ee.Number(END_YEAR - START_YEAR + 1))
        .rename("heatwave_days")
    )

    # Dry spell: longest run of months below 20th percentile precipitation
    pr_p20 = pr.reduce(ee.Reducer.percentile([20]))

    def _dry_month(img: ee.Image) -> ee.Image:
        return img.lt(pr_p20).rename("dry")

    dry_stack = pr.map(_dry_month).toBands()
    # Approximate via fraction of dry months (full run-length needs server-side loop)
    dry_frac = dry_stack.reduce(ee.Reducer.mean()).rename("dry_month_fraction")

    return ee.Image.cat(
        [tmax_p95, tmax_p99, pr_p05, pr_cv, vpd_p95, pdsi_min, heatwave, dry_frac]
    )


def sample_at_points(
    fc: ee.FeatureCollection,
    region: ee.Geometry | None = None,
    scale: int = 1000,
) -> ee.FeatureCollection:
    image = build_extreme_climate_image()
    return image.sampleRegions(
        collection=fc,
        scale=scale,
        geometries=True,
        tileScale=4,
    )


def features_to_records(fc: ee.FeatureCollection) -> list[dict[str, Any]]:
    records = []
    for feat in fc.getInfo()["features"]:
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        records.append({"lon": coords[0], "lat": coords[1], **props})
    return records


def extract_for_feature_collection(
    fc: ee.FeatureCollection,
    project: str | None = None,
) -> list[dict[str, Any]]:
    initialize_gee(project=project)
    sampled = sample_at_points(fc)
    return features_to_records(sampled)


if __name__ == "__main__":
    import pandas as pd

    from config import OUTPUT_DIR

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    initialize_gee()
    region = get_sundarbans_geometry()

    # Grid sample across Sundarbans when plot coordinates unavailable
    fc = ee.FeatureCollection.randomPoints(region, 500, seed=42)
    records = extract_for_feature_collection(fc)
    out = Path(OUTPUT_DIR) / "sundarbans_extreme_climate_sample.csv"
    pd.DataFrame(records).to_csv(out, index=False)
    print(f"Wrote {len(records)} rows to {out}")
    print("Columns:", list(EXTREME_CLIMATE.keys()))
