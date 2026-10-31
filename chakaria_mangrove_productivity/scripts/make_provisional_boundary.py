"""
Build a provisional Chakaria study-area boundary from the 30 site points.

Use only when the authoritative GeoJSON is not yet copied into data/.

Authoritative source (Windows):
  D:\\A_letter_to_Science\\chakaria_boundary.geojson

Project destination:
  data/chakaria_boundary.geojson

Usage:
  python scripts/make_provisional_boundary.py
  python scripts/make_provisional_boundary.py --buffer-m 2500 --force
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd
from shapely.geometry import MultiPoint, mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import BOUNDARY_GEOJSON, SITES_CSV  # noqa: E402


def make_provisional(
    sites_csv: Path = SITES_CSV,
    out_path: Path = BOUNDARY_GEOJSON,
    buffer_m: float = 2500.0,
    force: bool = False,
) -> Path:
    if out_path.exists() and not force:
        # Keep an existing authoritative boundary unless --force
        data = json.loads(out_path.read_text(encoding="utf-8"))
        note = ""
        if data.get("type") == "FeatureCollection" and data.get("features"):
            note = str(data["features"][0].get("properties", {}).get("note", ""))
        if "PROVISIONAL" not in note:
            print(f"Keeping existing (non-provisional) boundary: {out_path}")
            return out_path

    sites = pd.read_csv(sites_csv)
    pts = MultiPoint(
        [(float(r.Longitude), float(r.Latitude)) for _, r in sites.iterrows()]
    )
    hull = pts.convex_hull
    lat0 = float(sites["Latitude"].mean())
    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * abs(math.cos(math.radians(lat0)))
    buf_deg = buffer_m / ((m_per_deg_lat + m_per_deg_lon) / 2.0)
    aoi = hull.buffer(buf_deg, resolution=16).simplify(0.0005, preserve_topology=True)

    fc = {
        "type": "FeatureCollection",
        "name": "chakaria_boundary",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Chakaria study area",
                    "note": (
                        "PROVISIONAL: convex hull of 30 sites + "
                        f"~{buffer_m:.0f} m buffer. Replace with "
                        r"D:\A_letter_to_Science\chakaria_boundary.geojson"
                    ),
                    "n_sites": int(len(sites)),
                    "buffer_m": buffer_m,
                },
                "geometry": mapping(aoi),
            }
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(fc, indent=2), encoding="utf-8")
    print(f"Wrote provisional boundary → {out_path}")
    print(f"Bounds (lon/lat): {aoi.bounds}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Make provisional Chakaria AOI")
    parser.add_argument("--buffer-m", type=float, default=2500.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--out", type=Path, default=BOUNDARY_GEOJSON)
    args = parser.parse_args()
    make_provisional(out_path=args.out, buffer_m=args.buffer_m, force=args.force)


if __name__ == "__main__":
    main()
