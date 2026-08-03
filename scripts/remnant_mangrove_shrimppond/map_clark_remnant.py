#!/usr/bin/env python3
"""
Remnant mangrove within shrimp ponds — Clark CGA / Moore aquaculture collection.

Uses YOUR already-downloaded Clark landcover GeoTIFFs. Does not download anything.

Default local folder (your machine)::

    C:\\Users\\Md Mizanur Rahman\\OneDrive\\Desktop\\scripts\\outputs\\agb_stability\\shrimppond

Clark legend (15 m)
-------------------
1 Mangrove
2 Coastal Wetland
3 Pond Aquaculture
4 Water
5 Other Land Cover
6 Missing

Remnant definition (classes are mutually exclusive, so not pixel∩pixel)::

    mangrove pixels whose neighborhood is pond-dominated
    (default: ≥30% Pond Aquaculture in a ~315 m window)
    plus optional mangrove adjacent to ponds (15–45 m)

Examples
--------
# List Clark TIFFs in your folder
python map_clark_remnant.py --list-only

# Chakaria window on Bangladesh 2022
python map_clark_remnant.py --clark-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond" --aoi chakaria

# Full Bangladesh national stats
python map_clark_remnant.py --clark-dir "..." --country bangladesh --year 2022
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds
from scipy import ndimage

CLASS_MANGROVE = 1
CLASS_POND = 3
PX_M = 15.0
PX_HA = (PX_M * PX_M) / 10000.0

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"

DEFAULT_CLARK_DIRS = [
    Path(r"C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond"),
    Path("outputs/agb_stability/shrimppond"),
    Path.home() / "OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond",
    ROOT / "data" / "clark",
    ROOT / "data" / "shrimppond",
]

AOIS_WGS84 = {
    "chakaria": (91.95, 21.45, 92.08, 21.72),
    "sundarbans": (87.5, 20.5, 90.5, 23.0),
}


def resolve_clark_dir(cli: str | None) -> Path | None:
    candidates = []
    if cli:
        candidates.append(Path(cli))
    env = os.environ.get("CLARK_DIR") or os.environ.get("SHRIMPPOND_DIR")
    if env:
        candidates.append(Path(env))
    candidates.extend(DEFAULT_CLARK_DIRS)
    for p in candidates:
        if p.exists():
            return p
    return None


def find_clark_tifs(folder: Path) -> list[Path]:
    tifs = []
    for pat in ("*.tif", "*.tiff", "*.TIF", "*.TIFF"):
        tifs.extend(folder.rglob(pat))
    # prefer landcover over change/persistence and overviews
    tifs = [p for p in tifs if ".ovr" not in p.name.lower()]
    return sorted(tifs)


def pick_landcover(tifs: list[Path], country: str | None, year: int | None) -> Path:
    land = [p for p in tifs if re.search(r"landcover", p.name, re.I)]
    pool = land or tifs
    if country:
        pool = [p for p in pool if country.lower().replace(" ", "") in p.name.lower().replace(" ", "").replace("_", "")]
        if not pool:
            pool = land or tifs
    if year is not None:
        ypool = [p for p in pool if str(year) in p.name]
        if ypool:
            pool = ypool
    if not pool:
        raise FileNotFoundError("No Clark GeoTIFF found in folder")
    # prefer latest year-looking name
    return sorted(pool, key=lambda p: p.name)[-1]


def remnant_masks(arr: np.ndarray, matrix_pct: float = 0.30, window: int = 21):
    mangrove = arr == CLASS_MANGROVE
    pond = arr == CLASS_POND
    pond_d1 = ndimage.binary_dilation(pond, iterations=1)
    pond_d3 = ndimage.binary_dilation(pond, iterations=3)
    pond_f = ndimage.uniform_filter(pond.astype(np.float32), size=window)
    rem_matrix = mangrove & (pond_f >= matrix_pct)
    rem_adj15 = mangrove & pond_d1
    rem_adj45 = mangrove & pond_d3
    stats = {
        "mangrove_ha": float(mangrove.sum()) * PX_HA,
        "pond_aquaculture_ha": float(pond.sum()) * PX_HA,
        "remnant_adj_pond_15m_ha": float(rem_adj15.sum()) * PX_HA,
        "remnant_adj_pond_45m_ha": float(rem_adj45.sum()) * PX_HA,
        "remnant_in_pond_matrix_ha": float(rem_matrix.sum()) * PX_HA,
        "matrix_pond_fraction": matrix_pct,
        "matrix_window_px": window,
        "has_remnant_in_aquaculture": bool(rem_matrix.any() or rem_adj45.any()),
    }
    return stats, mangrove, pond, rem_matrix, rem_adj45


def wgs_bbox_to_raster(bbox_wgs, crs):
    lonmin, latmin, lonmax, latmax = bbox_wgs
    to_r = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = to_r.transform(
        [lonmin, lonmax, lonmin, lonmax],
        [latmin, latmin, latmax, latmax],
    )
    return min(xs), min(ys), max(xs), max(ys)


def analyze_tif(
    tif_path: Path,
    aoi: str | None,
    matrix_pct: float,
    out_prefix: str,
) -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    with rasterio.open(tif_path) as src:
        if aoi:
            bbox = wgs_bbox_to_raster(AOIS_WGS84[aoi], src.crs)
            window = from_bounds(*bbox, transform=src.transform)
            arr = src.read(1, window=window)
            transform = src.window_transform(window)
            label = f"{out_prefix}_{aoi}"
        else:
            arr = src.read(1)
            transform = src.transform
            label = f"{out_prefix}_full"
            window = None

        stats, mangrove, pond, rem_matrix, rem_adj = remnant_masks(arr, matrix_pct=matrix_pct)
        stats["source_tif"] = str(tif_path)
        stats["aoi"] = label
        rows.append(stats)
        print(pd.DataFrame([stats]).to_string(index=False))

        # RGB preview
        fig, ax = plt.subplots(figsize=(8, 8))
        rgb = np.zeros((*arr.shape, 3), dtype=float)
        rgb[..., 2] = pond * 0.7
        rgb[..., 1] = mangrove * 0.85
        rgb[..., 0] = rem_matrix.astype(float)
        edge = rem_adj & ~rem_matrix
        rgb[..., 0] = np.maximum(rgb[..., 0], edge.astype(float))
        rgb[..., 1] = np.maximum(rgb[..., 1], edge.astype(float) * 0.35)
        ax.imshow(rgb, origin="upper")
        ax.set_title(
            f"Clark remnant mangrove in aquaculture\n{Path(tif_path).name}\n"
            "pond=blue mangrove=green remnant-in-matrix=red"
        )
        ax.set_xticks([])
        ax.set_yticks([])
        map_path = OUT / f"{label}_remnant_map.png"
        fig.savefig(map_path, dpi=200, bbox_inches="tight")
        plt.close(fig)

        profile = src.profile.copy()
        profile.update(
            height=arr.shape[0],
            width=arr.shape[1],
            transform=transform,
            count=3,
            dtype="uint8",
            compress="lzw",
            nodata=0,
        )
        tif_out = OUT / f"{label}_remnant.tif"
        with rasterio.open(tif_out, "w", **profile) as dst:
            dst.write(pond.astype(np.uint8), 1)
            dst.write(mangrove.astype(np.uint8), 2)
            dst.write(rem_matrix.astype(np.uint8), 3)
            dst.set_band_description(1, "pond_aquaculture")
            dst.set_band_description(2, "mangrove")
            dst.set_band_description(3, "remnant_mangrove_in_aquaculture_matrix")
        print(f"Wrote {map_path}")
        print(f"Wrote {tif_out}")

    df = pd.DataFrame(rows)
    csv_path = OUT / f"{label}_remnant_stats.csv"
    df.to_csv(csv_path, index=False)
    print(f"Wrote {csv_path}")
    return df


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--clark-dir",
        default=None,
        help="Folder with your already-downloaded Clark GeoTIFFs "
        "(default: SHRIMPPOND_DIR / CLARK_DIR / Desktop shrimppond path)",
    )
    p.add_argument("--country", default=None, help="e.g. bangladesh")
    p.add_argument("--year", type=int, default=2022)
    p.add_argument("--tif", default=None, help="Exact Clark landcover GeoTIFF path")
    p.add_argument("--aoi", choices=sorted(AOIS_WGS84), default=None)
    p.add_argument("--matrix-pct", type=float, default=0.30)
    p.add_argument("--list-only", action="store_true")
    args = p.parse_args()

    if args.tif:
        tif_path = Path(args.tif)
        if not tif_path.exists():
            raise SystemExit(f"TIFF not found: {tif_path}")
        analyze_tif(tif_path, args.aoi, args.matrix_pct, tif_path.stem)
        return

    clark_dir = resolve_clark_dir(args.clark_dir)
    if clark_dir is None:
        raise SystemExit(
            "Clark folder not found.\n"
            "Point to your already-downloaded data, e.g.\n"
            '  --clark-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"'
        )

    tifs = find_clark_tifs(clark_dir)
    print(f"Clark dir: {clark_dir}")
    print(f"Found {len(tifs)} GeoTIFF(s)")
    for t in tifs:
        print(f"  {t.relative_to(clark_dir) if t.is_relative_to(clark_dir) else t}")
    if args.list_only:
        return
    if not tifs:
        raise SystemExit(f"No GeoTIFFs in {clark_dir}")

    tif_path = pick_landcover(tifs, args.country, args.year)
    print(f"Using: {tif_path}")
    analyze_tif(tif_path, args.aoi, args.matrix_pct, tif_path.stem)


if __name__ == "__main__":
    main()
