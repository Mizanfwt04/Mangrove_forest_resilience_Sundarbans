#!/usr/bin/env python3
"""
Map remnant mangrove inside shrimp / aquaculture ponds.

Remnant definition
------------------
mangrove ∩ aquaculture_pond   (ESA WorldCover class 95 ∩ pond mask)

Supports
--------
1) Local shrimp-pond folder (your Windows exports)::

    C:\\Users\\Md Mizanur Rahman\\OneDrive\\Desktop\\scripts\\outputs\\agb_stability\\shrimppond

   Pass with ``--shrimppond-dir`` or set env ``SHRIMPPOND_DIR``.

2) Chakaria AOI demo using Planetary Computer WorldCover + optional pond
   GeoJSON / GeoTIFF.

3) Overlay of field sites (RMSP / PMSP / PMWSP).

Examples
--------
python map_remnant_mangrove.py --aoi chakaria
python map_remnant_mangrove.py --shrimppond-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"
"""

from __future__ import annotations

import argparse
import os
from io import StringIO
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import planetary_computer as pc
import rasterio
import rioxarray
from pystac_client import Client
from rasterio import features
from scipy import ndimage
from shapely.geometry import Point, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"

DEFAULT_WINDOWS = Path(
    r"C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond"
)
DEFAULT_RELATIVE = Path("outputs/agb_stability/shrimppond")

AOIS = {
    "chakaria": (91.95, 21.45, 92.08, 21.72),
    "sundarbans": (87.5, 20.5, 90.5, 23.0),
}

BUILTIN_SITES = """ID,Group,Longitude,Latitude
R1,RMSP,92.049444,21.684167
R2,RMSP,92.053850,21.694183
R3,RMSP,92.046400,21.684517
R4,RMSP,92.049817,21.687750
R5,RMSP,92.050217,21.680333
R11,RMSP,92.050833,21.685083
R12,RMSP,92.047967,21.687483
R13,RMSP,92.051333,21.681483
R14,RMSP,92.038073,21.688113
R15,RMSP,92.049050,21.684499
P1,PMSP,91.998933,21.648417
P2,PMSP,91.985617,21.648783
P3,PMSP,91.997717,21.650633
P4,PMSP,91.986633,21.653217
P5,PMSP,91.962617,21.672817
P6,PMSP,91.985875,21.648760
P7,PMSP,91.982721,21.652622
P8,PMSP,91.984599,21.655553
P9,PMSP,91.986912,21.651018
P10,PMSP,92.014457,21.617991
N1,PMWSP,92.013333,21.595278
N2,PMWSP,92.009722,21.601389
N3,PMWSP,91.969883,21.469167
N4,PMWSP,91.973417,21.511150
N5,PMWSP,92.015700,21.612200
N6,PMWSP,92.008450,21.607083
N7,PMWSP,92.003200,21.593867
N8,PMWSP,91.978167,21.527200
N9,PMWSP,92.004883,21.609133
N10,PMWSP,92.006717,21.609433
"""


def resolve_shrimppond_dir(cli_path: str | None) -> Path | None:
    candidates = []
    if cli_path:
        candidates.append(Path(cli_path))
    env = os.environ.get("SHRIMPPOND_DIR")
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            DEFAULT_RELATIVE,
            Path.home() / "OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond",
            DEFAULT_WINDOWS,
            ROOT / "data" / "shrimppond",
        ]
    )
    for path in candidates:
        if path.exists():
            return path
    return None


def list_local_layers(folder: Path) -> dict[str, list[Path]]:
    patterns = {
        "raster": ["*.tif", "*.tiff", "*.TIF", "*.TIFF"],
        "vector": ["*.shp", "*.geojson", "*.gpkg", "*.json"],
    }
    found: dict[str, list[Path]] = {"raster": [], "vector": []}
    for kind, globs in patterns.items():
        for g in globs:
            found[kind].extend(sorted(folder.rglob(g)))
    return found


def load_sites(sites_csv: Path | None) -> gpd.GeoDataFrame:
    if sites_csv and sites_csv.exists():
        df = pd.read_csv(sites_csv)
    elif (DATA / "chakaria_sites.csv").exists():
        df = pd.read_csv(DATA / "chakaria_sites.csv")
    else:
        df = pd.read_csv(StringIO(BUILTIN_SITES))
    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
        crs="EPSG:4326",
    )


def fetch_worldcover_mangrove(bbox: tuple[float, float, float, float]):
    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )
    items = list(
        catalog.search(
            collections=["esa-worldcover"],
            bbox=list(bbox),
            datetime="2021",
            max_items=1,
        ).items()
    )
    if not items:
        raise RuntimeError(f"No WorldCover tile for bbox={bbox}")
    href = pc.sign(items[0].assets["map"].href)
    da = rioxarray.open_rasterio(href).squeeze()
    da = da.rio.clip_box(minx=bbox[0], miny=bbox[1], maxx=bbox[2], maxy=bbox[3])
    mangrove = (da == 95).astype("uint8")
    return mangrove, href


def rasterize_vectors(gdf: gpd.GeoDataFrame, transform, shape) -> np.ndarray:
    geoms = [(geom, 1) for geom in gdf.geometry if geom is not None and not geom.is_empty]
    if not geoms:
        return np.zeros(shape, dtype="uint8")
    return features.rasterize(
        geoms, out_shape=shape, transform=transform, fill=0, dtype="uint8"
    )


def load_pond_mask(
    shrimppond_dir: Path | None,
    pond_vector: Path | None,
    mangrove,
    bbox: tuple[float, float, float, float],
) -> np.ndarray:
    transform = mangrove.rio.transform()
    shape = (mangrove.sizes["y"], mangrove.sizes["x"])

    if pond_vector and pond_vector.exists():
        gdf = gpd.read_file(pond_vector).to_crs(4326)
        gdf = gpd.clip(gdf, gpd.GeoDataFrame(geometry=[box(*bbox)], crs=4326))
        return rasterize_vectors(gdf, transform, shape)

    if shrimppond_dir is not None:
        layers = list_local_layers(shrimppond_dir)
        print(f"Local shrimppond layers in {shrimppond_dir}:")
        for kind, paths in layers.items():
            for p in paths:
                print(f"  [{kind}] {p}")

        for rast in layers["raster"]:
            with rasterio.open(rast) as src:
                # Reproject / resample onto mangrove grid via rioxarray
                pond_da = rioxarray.open_rasterio(rast).squeeze()
                if pond_da.rio.crs is None:
                    pond_da = pond_da.rio.write_crs("EPSG:4326")
                pond_da = pond_da.rio.reproject_match(mangrove, resampling=rasterio.enums.Resampling.nearest)
                arr = np.asarray(pond_da.values)
                mask = (np.isfinite(arr) & (arr != 0) & (arr != src.nodata if src.nodata is not None else True)).astype(
                    "uint8"
                )
                if mask.any():
                    print(f"Using pond raster: {rast.name}")
                    return mask

        for vec in layers["vector"]:
            gdf = gpd.read_file(vec).to_crs(4326)
            gdf = gpd.clip(gdf, gpd.GeoDataFrame(geometry=[box(*bbox)], crs=4326))
            mask = rasterize_vectors(gdf, transform, shape)
            if mask.any():
                print(f"Using pond vector: {vec.name}")
                return mask

        print("No usable pond layer found in local folder; WorldCover water used as proxy.")

    # Proxy: permanent water (class 80) as pond-like surface inside AOI
    da = mangrove  # same grid; reopen WorldCover values
    # mangrove is boolean; need original classes — re-fetch
    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )
    item = list(
        catalog.search(collections=["esa-worldcover"], bbox=list(bbox), datetime="2021", max_items=1).items()
    )[0]
    href = pc.sign(item.assets["map"].href)
    wc = rioxarray.open_rasterio(href).squeeze().rio.clip_box(
        minx=bbox[0], miny=bbox[1], maxx=bbox[2], maxy=bbox[3]
    )
    return (np.asarray(wc.values) == 80).astype("uint8")


def analyze(
    aoi_name: str,
    shrimppond_dir: Path | None,
    pond_vector: Path | None,
    sites_csv: Path | None,
    buffer_m: int = 30,
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    bbox = AOIS[aoi_name]
    print(f"AOI={aoi_name} bbox={bbox}")

    mangrove, wc_href = fetch_worldcover_mangrove(bbox)
    mang_arr = np.asarray(mangrove.values).astype("uint8")
    pond_mask = load_pond_mask(shrimppond_dir, pond_vector, mangrove, bbox)

    remnant = ((mang_arr == 1) & (pond_mask == 1)).astype("uint8")
    dilate_iter = max(1, int(round(buffer_m / 10)))
    near = (
        (mang_arr == 1)
        & ndimage.binary_dilation(pond_mask.astype(bool), iterations=dilate_iter)
        & (pond_mask == 0)
    ).astype("uint8")

    px_area = 100.0  # 10 m WorldCover
    stats = {
        "aoi": aoi_name,
        "mangrove_ha": float(mang_arr.sum()) * px_area / 10000,
        "pond_ha": float(pond_mask.sum()) * px_area / 10000,
        "remnant_inside_pond_ha": float(remnant.sum()) * px_area / 10000,
        "mangrove_within_buffer_ha": float(near.sum()) * px_area / 10000,
        "buffer_m": buffer_m,
        "remnant_pct_of_pond_area": 100.0 * float(remnant.sum()) / max(float(pond_mask.sum()), 1.0),
    }
    stats_df = pd.DataFrame([stats])
    stats_path = OUT / f"{aoi_name}_remnant_mangrove_stats.csv"
    stats_df.to_csv(stats_path, index=False)
    print(stats_df.to_string(index=False))

    transform = mangrove.rio.transform()
    shape = mang_arr.shape
    tif_path = OUT / f"{aoi_name}_remnant_mangrove_shrimppond.tif"
    profile = {
        "driver": "GTiff",
        "height": shape[0],
        "width": shape[1],
        "count": 3,
        "dtype": "uint8",
        "crs": "EPSG:4326",
        "transform": transform,
        "compress": "lzw",
    }
    with rasterio.open(tif_path, "w", **profile) as dst:
        dst.write(pond_mask, 1)
        dst.write(mang_arr, 2)
        dst.write(remnant, 3)
        dst.set_band_description(1, "aquaculture_pond")
        dst.set_band_description(2, "mangrove")
        dst.set_band_description(3, "remnant_mangrove_in_pond")

    sites = load_sites(sites_csv)
    sites = sites.cx[bbox[0] : bbox[2], bbox[1] : bbox[3]].copy()
    if len(sites):
        coords = list(zip(sites["Longitude"], sites["Latitude"]))
        with rasterio.open(wc_href) as src:
            samples = [int(s[0]) for s in src.sample(coords)]
        sites["WorldCover"] = samples
        labels = {
            10: "trees",
            20: "shrub",
            30: "grass",
            40: "crop",
            50: "built",
            60: "bare",
            80: "water",
            90: "herbaceous_wetland",
            95: "mangrove",
        }
        sites["WC_label"] = sites["WorldCover"].map(labels).fillna("other")
        if pond_mask.any():
            # point-in-pond via raster sample on written grid is awkward; use geometry if vector available
            ys = ((bbox[3] - sites["Latitude"]) / (bbox[3] - bbox[1]) * (shape[0] - 1)).round().astype(int)
            xs = ((sites["Longitude"] - bbox[0]) / (bbox[2] - bbox[0]) * (shape[1] - 1)).round().astype(int)
            ys = ys.clip(0, shape[0] - 1)
            xs = xs.clip(0, shape[1] - 1)
            sites["in_pond"] = pond_mask[ys, xs].astype(bool)
            sites["on_mangrove"] = mang_arr[ys, xs].astype(bool)
            sites["remnant_candidate"] = sites["in_pond"] & sites["on_mangrove"]
        sites.to_csv(OUT / f"{aoi_name}_sites_remnant_overlay.csv", index=False)
        print(sites.groupby(["Group", "WC_label"], dropna=False).size())

    fig, ax = plt.subplots(figsize=(8, 8))
    rgb = np.zeros((*shape, 3), dtype=float)
    rgb[..., 2] = pond_mask * 0.55
    rgb[..., 1] = mang_arr * 0.85
    rgb[..., 0] = np.maximum(remnant, near * 0.7)
    ax.imshow(rgb, extent=[bbox[0], bbox[2], bbox[1], bbox[3]], origin="upper")
    colors = {"RMSP": "#1b9e77", "PMSP": "#d95f02", "PMWSP": "#7570b3"}
    for g, sub in sites.groupby("Group"):
        ax.scatter(
            sub.geometry.x,
            sub.geometry.y,
            s=36,
            c=colors.get(g, "white"),
            edgecolors="white",
            linewidths=0.4,
            label=g,
            zorder=5,
        )
    ax.legend(loc="lower left")
    ax.set_title(
        f"{aoi_name}: remnant mangrove in shrimp ponds\npond=blue mangrove=green remnant/edge=red"
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    map_path = OUT / f"{aoi_name}_remnant_mangrove_map.png"
    fig.savefig(map_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {tif_path}")
    print(f"Wrote {map_path}")
    print(f"Wrote {stats_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aoi", choices=sorted(AOIS), default="chakaria")
    parser.add_argument(
        "--shrimppond-dir",
        default=None,
        help="Folder with shrimp-pond GeoTIFF/shapefile exports "
        "(default: env SHRIMPPOND_DIR or local outputs/agb_stability/shrimppond)",
    )
    parser.add_argument("--pond-vector", default=None, help="Optional pond GeoJSON/shp")
    parser.add_argument("--sites-csv", default=None)
    parser.add_argument("--buffer-m", type=int, default=30)
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list files found in the shrimppond folder",
    )
    args = parser.parse_args()

    shrimppond_dir = resolve_shrimppond_dir(args.shrimppond_dir)
    if shrimppond_dir is None:
        print(
            "Shrimppond folder not found on this machine.\n"
            "Pass --shrimppond-dir to your local path, e.g.\n"
            '  --shrimppond-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"'
        )
    else:
        print(f"Using shrimppond dir: {shrimppond_dir}")
        if args.list_only:
            print(list_local_layers(shrimppond_dir))
            return

    analyze(
        aoi_name=args.aoi,
        shrimppond_dir=shrimppond_dir,
        pond_vector=Path(args.pond_vector) if args.pond_vector else None,
        sites_csv=Path(args.sites_csv) if args.sites_csv else None,
        buffer_m=args.buffer_m,
    )


if __name__ == "__main__":
    main()
