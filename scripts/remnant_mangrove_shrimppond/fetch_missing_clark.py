#!/usr/bin/env python3
"""
Download missing Clark CGA country zips into your local shrimppond folder.

Default destination (same folder as your other Clark zips)::

    C:\\Users\\Md Mizanur Rahman\\OneDrive\\Desktop\\scripts\\outputs\\agb_stability\\shrimppond

Only fetches files that are not already present. Does not re-download existing zips.

Example
-------
python fetch_missing_clark.py
python fetch_missing_clark.py --clark-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"
python fetch_missing_clark.py --only brazil nicaragua
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

# Official Clark CGA S3 mirrors (same source as your existing country zips)
CLARK_ZIPS = {
    "brazil": (
        "brazil_landcover_change_maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/brazil/brazil_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    ),
    "nicaragua": (
        "nicaragua_landcover_change_maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/nicaragua/nicaragua_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    ),
    "bangladesh": (
        "Bangladesh_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/bangladesh/Bangladesh_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
    ),
    "cambodia": (
        "Cambodia_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/cambodia/Cambodia_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
    ),
    "china": (
        "china_landcover_change_maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/china/china_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    ),
    "ecuador": (
        "ecuador_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
        "https://clarkcga-aquaculture.s3.us-west-2.amazonaws.com/data/v1.0/zip/ecuador/ecuador_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
    ),
    "elsalvador": (
        "elsalvador_landcover_change_maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/el_salvador/elsalvador_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    ),
    "honduras": (
        "honduras_landcover_change_maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/honduras/honduras_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    ),
    "india": (
        "india_landcover_change_maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/india/india_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    ),
    "indonesia": (
        "indonesia_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
        "https://clarkcga-aquaculture.s3.us-west-2.amazonaws.com/data/v1.0/zip/indonesia/indonesia_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
    ),
    "malaysia": (
        "Malaysia_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/malaysia/Malaysia_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
    ),
    "mexico": (
        "mexico_landcover_change_maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/mexico/mexico_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    ),
    "myanmar": (
        "myanmar_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
        "https://clarkcga-aquaculture.s3.us-west-2.amazonaws.com/data/v1.0/zip/myanmar/myanmar_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
    ),
    "philippines": (
        "Philippines_Change_Persistence_Maps_1999_to_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/philippines/Philippines_Change_Persistence_Maps_1999_to_2022.zip",
    ),
    "srilanka": (
        "SriLanka_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
        "https://clarkcga-aquaculture.s3.amazonaws.com/data/v1.0/zip/sri_lanka/SriLanka_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
    ),
    "thailand": (
        "thailand_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
        "https://clarkcga-aquaculture.s3.us-west-2.amazonaws.com/data/v1.0/zip/thailand/thailand_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
    ),
    "vietnam": (
        "vietnam_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
        "https://clarkcga-aquaculture.s3.us-west-2.amazonaws.com/data/v1.0/zip/vietnam/vietnam_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
    ),
}

DEFAULT_DIR = Path(
    r"C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond"
)
REPO_DIR = Path(__file__).resolve().parents[1] / "outputs" / "agb_stability" / "shrimppond"


def resolve_dir(cli: str | None) -> Path:
    if cli:
        return Path(cli)
    if DEFAULT_DIR.exists():
        return DEFAULT_DIR
    REPO_DIR.mkdir(parents=True, exist_ok=True)
    return REPO_DIR


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    print(f"Downloading {dest.name} ...")
    urllib.request.urlretrieve(url, tmp)  # noqa: S310 — fixed Clark S3 URLs
    tmp.replace(dest)
    print(f"  saved {dest} ({dest.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clark-dir", default=None)
    parser.add_argument(
        "--only",
        nargs="+",
        default=["brazil", "nicaragua"],
        help="Country keys to fetch (default: brazil nicaragua)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the zip already exists",
    )
    args = parser.parse_args()

    out_dir = resolve_dir(args.clark_dir)
    print(f"Destination: {out_dir}")

    for key in args.only:
        k = key.lower().replace(" ", "").replace("_", "")
        if k not in CLARK_ZIPS:
            print(f"Unknown country key: {key}", file=sys.stderr)
            print(f"Choose from: {', '.join(sorted(CLARK_ZIPS))}", file=sys.stderr)
            raise SystemExit(1)
        name, url = CLARK_ZIPS[k]
        dest = out_dir / name
        if dest.exists() and not args.force:
            print(f"SKIP (already present): {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
            continue
        download(url, dest)

    print("Done.")


if __name__ == "__main__":
    main()
