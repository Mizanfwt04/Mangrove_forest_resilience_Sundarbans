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
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402
    ANNUAL_UGPP_CSV,
    BOUNDARY_GEOJSON,
    BUFFER_M,
    END_YEAR,
    MAX_PIXELS,
    SCALE_M,
    SITES_CSV,
    START_YEAR,
    UGPP_COLLECTION,
)
from boundary_utils import (  # noqa: E402
    boundary_bbox,
    boundary_to_ee_geometry,
    resolve_boundary_path,
    sites_inside_boundary,
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


def get_ugpp_collection(clip_to_boundary: bool = True, boundary_path: Path | None = None):
    import ee

    col = (
        ee.ImageCollection(UGPP_COLLECTION)
        .filter(ee.Filter.calendarRange(START_YEAR, END_YEAR, "year"))
        .sort("system:time_start")
    )
    if clip_to_boundary and (boundary_path or BOUNDARY_GEOJSON).exists():
        aoi = boundary_to_ee_geometry(boundary_path)
        col = col.map(lambda img: img.clip(aoi))
        # Restrict image footprints to AOI for faster reduceRegion
        col = col.filterBounds(aoi)
    return col


def extract_timeseries_client(
    sites: pd.DataFrame,
    boundary_path: Path | None = None,
) -> pd.DataFrame:
    """
    Client-side extraction (getInfo per site × year).
    Fine for n≈30 sites × ~25 years; use Drive export for larger jobs.
    """
    import ee

    ugpp = get_ugpp_collection(boundary_path=boundary_path)
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


def extract_timeseries_server(
    sites: pd.DataFrame,
    boundary_path: Path | None = None,
):
    """
    Server-side map/reduce: returns an ee.FeatureCollection of annual means.
    Prefer this + Export.table.toDrive for robust runs.
    """
    import ee

    ugpp = get_ugpp_collection(boundary_path=boundary_path)
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


def build_map(sites: pd.DataFrame, boundary_path: Path | None = None):
    """Optional interactive geemap view of AOI + sites + latest uGPP."""
    import ee
    import geemap

    bpath = resolve_boundary_path(boundary_path) if (boundary_path or BOUNDARY_GEOJSON).exists() else None
    if bpath is not None:
        minx, miny, maxx, maxy = boundary_bbox(bpath)
        center = [(miny + maxy) / 2, (minx + maxx) / 2]
    else:
        center = [21.62, 92.00]

    m = geemap.Map(center=center, zoom=11)
    ugpp = get_ugpp_collection(clip_to_boundary=bpath is not None, boundary_path=bpath)
    latest = ee.Image(ugpp.sort("system:time_start", False).first())
    m.addLayer(
        latest,
        {"min": 0, "max": 2000, "palette": ["#ffffcc", "#41b6c4", "#0c2c84"]},
        "uGPP (latest year)",
    )
    if bpath is not None:
        aoi = boundary_to_ee_geometry(bpath)
        m.addLayer(aoi, {"color": "black"}, "Study area boundary")
        m.centerObject(aoi, 11)
    m.addLayer(sites_to_feature_collection(sites), {"color": "red"}, "Sites")
    return m


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Chakaria uGPP via GEE")
    parser.add_argument("--project", default=None, help="GCP EE project id")
    parser.add_argument(
        "--boundary",
        type=Path,
        default=None,
        help=(
            "Study-area GeoJSON. Default: data/chakaria_boundary.geojson "
            r"(copy from D:\A_letter_to_Science\chakaria_boundary.geojson)"
        ),
    )
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

    boundary_path = args.boundary
    if boundary_path is None and BOUNDARY_GEOJSON.exists():
        boundary_path = BOUNDARY_GEOJSON

    if boundary_path is not None:
        bpath = resolve_boundary_path(boundary_path)
        print(f"Study area boundary: {bpath}")
        inside = sites_inside_boundary(boundary_path=bpath)
        outside = [sid for sid, ok in inside.items() if not ok]
        if outside:
            print(f"WARNING: {len(outside)} sites outside boundary: {outside}")
        else:
            print(f"All {len(inside)} sites fall inside the study-area boundary.")
    else:
        print(
            "No boundary GeoJSON found — extraction will use site buffers only.\n"
            f"  Expected: {BOUNDARY_GEOJSON}\n"
            r"  Copy from: D:\A_letter_to_Science\chakaria_boundary.geojson"
        )

    if args.export_drive:
        fc = extract_timeseries_server(sites, boundary_path=boundary_path)
        export_to_drive(fc)
        return

    df = extract_timeseries_client(sites, boundary_path=boundary_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows → {args.out}")
    print(df.groupby("Group")["Site"].nunique())


if __name__ == "__main__":
    main()
