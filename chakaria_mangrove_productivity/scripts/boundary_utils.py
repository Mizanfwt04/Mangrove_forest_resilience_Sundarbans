"""Helpers for the Chakaria study-area boundary GeoJSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import BOUNDARY_GEOJSON, SITES_CSV  # noqa: E402


def resolve_boundary_path(path: Path | str | None = None) -> Path:
    """
    Resolve the study-area GeoJSON path.

    Preferred local copy for this project:
      chakaria_mangrove_productivity/data/chakaria_boundary.geojson

    Original file on the author's machine:
      D:\\A_letter_to_Science\\chakaria_boundary.geojson
    """
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Boundary not found: {p}")
        return p

    if BOUNDARY_GEOJSON.exists():
        return BOUNDARY_GEOJSON

    raise FileNotFoundError(
        "Study-area boundary missing.\n"
        f"  Place your file at: {BOUNDARY_GEOJSON}\n"
        r"  Source on Windows: D:\A_letter_to_Science\chakaria_boundary.geojson"
        "\n"
        "  Or run: python scripts/make_provisional_boundary.py"
    )


def load_boundary_geojson(path: Path | str | None = None) -> dict[str, Any]:
    p = resolve_boundary_path(path)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("type") not in {"FeatureCollection", "Feature", "Polygon", "MultiPolygon"}:
        raise ValueError(f"Unexpected GeoJSON type in {p}: {data.get('type')}")
    return data


def boundary_geometry_coords(path: Path | str | None = None) -> list:
    """
    Return polygon coordinate rings suitable for ee.Geometry.Polygon /
    MultiPolygon construction. Handles FeatureCollection / Feature / Polygon.
    """
    data = load_boundary_geojson(path)

    def from_geom(geom: dict) -> list:
        gtype = geom["type"]
        coords = geom["coordinates"]
        if gtype == "Polygon":
            return [coords]
        if gtype == "MultiPolygon":
            return coords
        raise ValueError(f"Unsupported geometry type: {gtype}")

    if data["type"] == "FeatureCollection":
        polys: list = []
        for ft in data["features"]:
            polys.extend(from_geom(ft["geometry"]))
        return polys
    if data["type"] == "Feature":
        return from_geom(data["geometry"])
    return from_geom(data)


def boundary_to_ee_geometry(path: Path | str | None = None):
    """Convert local GeoJSON boundary to an ee.Geometry."""
    import ee

    polys = boundary_geometry_coords(path)
    if len(polys) == 1:
        return ee.Geometry.Polygon(polys[0])
    return ee.Geometry.MultiPolygon(polys)


def boundary_bbox(path: Path | str | None = None) -> tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) in lon/lat."""
    polys = boundary_geometry_coords(path)
    xs: list[float] = []
    ys: list[float] = []
    for poly in polys:
        for ring in poly:
            for x, y, *_ in ring:
                xs.append(float(x))
                ys.append(float(y))
    return min(xs), min(ys), max(xs), max(ys)


def sites_inside_boundary(
    sites_csv: Path = SITES_CSV,
    boundary_path: Path | str | None = None,
) -> dict[str, bool]:
    """Quick point-in-polygon check (requires shapely)."""
    import pandas as pd
    from shapely.geometry import Point, shape

    data = load_boundary_geojson(boundary_path)
    if data["type"] == "FeatureCollection":
        geoms = [shape(ft["geometry"]) for ft in data["features"]]
        from shapely.ops import unary_union

        poly = unary_union(geoms)
    elif data["type"] == "Feature":
        poly = shape(data["geometry"])
    else:
        poly = shape(data)

    sites = pd.read_csv(sites_csv)
    return {
        str(row["ID"]): bool(poly.contains(Point(float(row["Longitude"]), float(row["Latitude"]))))
        for _, row in sites.iterrows()
    }
