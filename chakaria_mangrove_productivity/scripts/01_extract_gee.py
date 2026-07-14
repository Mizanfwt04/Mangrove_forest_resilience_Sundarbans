"""
Extract annual uGPP time series for Chakaria mangrove sites via Google Earth Engine.

Requires Earth Engine authentication:
  earthengine authenticate
  # or in notebook: ee.Authenticate(); ee.Initialize()

Usage (from chakaria_mangrove_productivity/):
  python scripts/01_extract_gee.py
  python scripts/01_extract_gee.py --project YOUR_GCP_PROJECT
  python scripts/01_extract_gee.py --export-drive   # server-side Drive export
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as `python scripts/01_extract_gee.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (  # noqa: E402
    ANNUAL_UGPP_CSV,
    BUFFER_M,
    END_YEAR,
    MAX_PIXELS,
    SCALE_M,
    SITES_CSV,
    START_YEAR,
    UGPP_COLLECTION,
)


def initialize_ee(project: str | None = None) -> None:
    import ee

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


def load_sites(path: Path = SITES_CSV) -> pd.DataFrame:
    sites = pd.read_csv(path)
    required = {"ID", "Group", "Longitude", "Latitude"}
    missing = required - set(sites.columns)
    if missing:
        raise ValueError(f"sites.csv missing columns: {sorted(missing)}")
    return sites


def sites_to_feature_collection(sites: pd.DataFrame):
    import ee

    feats = []
    for _, row in sites.iterrows():
        feats.append(
            ee.Feature(
                ee.Geometry.Point([float(row["Longitude"]), float(row["Latitude"])]),
                {"ID": str(row["ID"]), "Group": str(row["Group"])},
            )
        )
    return ee.FeatureCollection(feats)


def get_ugpp_collection():
    import ee

    return (
        ee.ImageCollection(UGPP_COLLECTION)
        .filter(ee.Filter.calendarRange(START_YEAR, END_YEAR, "year"))
        .sort("system:time_start")
    )


def extract_timeseries_client(sites: pd.DataFrame) -> pd.DataFrame:
    """
    Client-side extraction (getInfo per site × year).
    Fine for n≈30 sites × ~25 years; use Drive export for larger jobs.
    """
    import ee

    ugpp = get_ugpp_collection()
    img_list = ugpp.toList(ugpp.size())
    n_img = int(ugpp.size().getInfo())

    # Cache year metadata once
    years = []
    for i in range(n_img):
        img = ee.Image(img_list.get(i))
        year = int(ee.Date(img.get("system:time_start")).get("year").getInfo())
        years.append(year)

    records: list[dict] = []
    for _, row in sites.iterrows():
        point = ee.Geometry.Point([float(row["Longitude"]), float(row["Latitude"])])
        roi = point.buffer(BUFFER_M)
        print(f"Extracting {row['ID']} ({row['Group']}) …")

        for i in range(n_img):
            img = ee.Image(img_list.get(i))
            stats = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=SCALE_M,
                maxPixels=MAX_PIXELS,
            ).getInfo()
            # Band name may vary; take first value
            val = next(iter(stats.values())) if stats else None
            records.append(
                {
                    "Site": row["ID"],
                    "Group": row["Group"],
                    "Year": years[i],
                    "uGPP": val,
                }
            )

    return pd.DataFrame.from_records(records)


def extract_timeseries_server(sites: pd.DataFrame):
    """
    Server-side map/reduce: returns an ee.FeatureCollection of annual means.
    Prefer this + Export.table.toDrive for robust runs.
    """
    import ee

    ugpp = get_ugpp_collection()
    fc_sites = sites_to_feature_collection(sites)

    def per_site(ft):
        roi = ft.geometry().buffer(BUFFER_M)

        def per_image(img):
            value = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=SCALE_M,
                maxPixels=MAX_PIXELS,
            ).values().get(0)
            return ee.Feature(
                None,
                {
                    "Site": ft.get("ID"),
                    "Group": ft.get("Group"),
                    "Year": ee.Date(img.get("system:time_start")).get("year"),
                    "uGPP": value,
                },
            )

        return ugpp.map(per_image)

    return fc_sites.map(per_site).flatten()


def export_to_drive(collection, description: str = "Chakaria_uGPP_TimeSeries") -> None:
    import ee

    task = ee.batch.Export.table.toDrive(
        collection=collection,
        description=description,
        fileFormat="CSV",
    )
    task.start()
    print(f"Started Drive export task: {description} (id={task.id})")
    print("Monitor at https://code.earthengine.google.com/tasks")


def build_map(sites: pd.DataFrame):
    """Optional interactive geemap view of sites + latest uGPP."""
    import ee
    import geemap

    m = geemap.Map(center=[21.62, 92.00], zoom=11)
    ugpp = get_ugpp_collection()
    latest = ee.Image(ugpp.sort("system:time_start", False).first())
    m.addLayer(
        latest,
        {"min": 0, "max": 2000, "palette": ["#ffffcc", "#41b6c4", "#0c2c84"]},
        "uGPP (latest year)",
    )
    m.addLayer(sites_to_feature_collection(sites), {"color": "red"}, "Sites")
    return m


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Chakaria uGPP via GEE")
    parser.add_argument("--project", default=None, help="GCP EE project id")
    parser.add_argument(
        "--export-drive",
        action="store_true",
        help="Start server-side Export.table.toDrive instead of local getInfo",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ANNUAL_UGPP_CSV,
        help="Local CSV output path (client mode)",
    )
    args = parser.parse_args()

    initialize_ee(args.project)
    sites = load_sites()

    if args.export_drive:
        fc = extract_timeseries_server(sites)
        export_to_drive(fc)
        return

    df = extract_timeseries_client(sites)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows → {args.out}")
    print(df.groupby("Group")["Site"].nunique())


if __name__ == "__main__":
    main()
