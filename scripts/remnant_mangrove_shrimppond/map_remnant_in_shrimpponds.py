#!/usr/bin/env python3
"""
Map shrimp-pond areas that still contain remnant mangrove (Clark CGA).

For each country landcover (latest year, default 2022):
  class 1 = Mangrove
  class 3 = Pond Aquaculture

Remnant mangrove in aquaculture landscape
-----------------------------------------
  mangrove pixels with ≥30% ponds in a ~315 m neighborhood
  OR mangrove adjacent to ponds (≤45 m)

Shrimp ponds with remnant mangrove
----------------------------------
  pond pixels within 45 m of mangrove (pond–mangrove interface)

Reads zips already in --clark-dir. Does not download.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import array_bounds
from rasterio.windows import Window
from scipy import ndimage

CLASS_MANGROVE = 1
CLASS_POND = 3
PX_M = 15.0
PX_HA = (PX_M * PX_M) / 10000.0

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
DEFAULT_DIR = ROOT.parent / "outputs" / "agb_stability" / "shrimppond"


def country_from_name(name: str) -> str:
    n = re.sub(r"[^a-z]", "", name.lower())
    mapping = {
        "bangladesh": "Bangladesh",
        "brazil": "Brazil",
        "cambodia": "Cambodia",
        "china": "China",
        "ecuador": "Ecuador",
        "elsalvador": "El Salvador",
        "honduras": "Honduras",
        "india": "India",
        "indonesia": "Indonesia",
        "malaysia": "Malaysia",
        "mexico": "Mexico",
        "myanmar": "Myanmar",
        "nicaragua": "Nicaragua",
        "philippines": "Philippines",
        "srilanka": "Sri Lanka",
        "thailand": "Thailand",
        "vietnam": "Vietnam",
    }
    for k, v in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
        if k in n:
            return v
    return name


def extract_zips(clark_dir: Path) -> None:
    extract_root = clark_dir / "_extracted"
    extract_root.mkdir(exist_ok=True)
    for zpath in sorted(clark_dir.glob("*.zip")):
        dest = extract_root / zpath.stem
        dest.mkdir(parents=True, exist_ok=True)
        has_tif = any(dest.rglob("*landcover*.tif")) or any(dest.rglob("*Landcover*.tif"))
        if has_tif:
            continue
        print(f"Extracting {zpath.name} ...")
        with zipfile.ZipFile(zpath, "r") as zf:
            # Extract only landcover tifs + sidecars needed (skip huge .ovr when possible for speed?)
            # Keep ovr — useful for overview reads. Extract all for correctness.
            zf.extractall(dest)


def list_landcover_tifs(clark_dir: Path) -> dict[str, list[Path]]:
    extract_root = clark_dir / "_extracted"
    by_country: dict[str, list[Path]] = {}
    roots = [extract_root] if extract_root.exists() else []
    roots.append(clark_dir)
    for root in roots:
        for tif in root.rglob("*.tif"):
            if ".ovr" in tif.name.lower():
                continue
            if "landcover" not in tif.name.lower():
                continue
            if "_extracted" not in tif.parts and root == clark_dir:
                # avoid double-count loose copies if any
                pass
            c = country_from_name(tif.name)
            by_country.setdefault(c, []).append(tif)
    # unique paths
    return {c: sorted(set(ps), key=lambda p: p.name) for c, ps in by_country.items()}


def pick_year(tifs: list[Path], year: int | None) -> Path:
    if year is not None:
        y = [p for p in tifs if str(year) in p.name]
        if y:
            return sorted(y, key=lambda p: p.name)[-1]

    def ykey(p: Path) -> int:
        ys = [int(x) for x in re.findall(r"(?:19|20)\d{2}", p.name)]
        return max(ys) if ys else 0

    return sorted(tifs, key=ykey)[-1]


def choose_overview(src: rasterio.DatasetReader, max_dim: int = 8000) -> tuple[int | None, float]:
    """Return (overview_index or None, pixel_size_m)."""
    h, w = src.height, src.width
    if max(h, w) <= max_dim:
        return None, abs(src.res[0])
    if not src.overviews(1):
        return None, abs(src.res[0])
    # pick coarsest overview that is still <= max_dim on long side... actually finest that fits
    ovr_factors = src.overviews(1)
    for i, factor in enumerate(ovr_factors):
        if max(h // factor, w // factor) <= max_dim:
            return i, abs(src.res[0]) * factor
    # last overview
    i = len(ovr_factors) - 1
    return i, abs(src.res[0]) * ovr_factors[i]


def read_landcover(path: Path, max_dim: int = 8000) -> tuple[np.ndarray, float, object]:
    with rasterio.open(path) as src:
        ovr_i, px = choose_overview(src, max_dim=max_dim)
        if ovr_i is None:
            arr = src.read(1)
            transform = src.transform
        else:
            # read overview via out_shape
            factor = src.overviews(1)[ovr_i]
            out_h = src.height // factor
            out_w = src.width // factor
            arr = src.read(1, out_shape=(out_h, out_w), resampling=Resampling.nearest)
            transform = src.transform * src.transform.scale(
                (src.width / out_w), (src.height / out_h)
            )
        return arr, px, transform


def remnant_and_pond_stats(arr: np.ndarray, px_m: float) -> dict:
    px_ha = (px_m * px_m) / 10000.0
    # scale morphological windows to ~same ground distance as 15 m native
    # native: dilate 3 → 45 m; uniform 21 → 315 m
    dilate_45 = max(1, int(round(45.0 / px_m)))
    win_315 = max(3, int(round(315.0 / px_m)))
    if win_315 % 2 == 0:
        win_315 += 1

    mangrove = arr == CLASS_MANGROVE
    pond = arr == CLASS_POND

    pond_d = ndimage.binary_dilation(pond, iterations=dilate_45)
    mang_d = ndimage.binary_dilation(mangrove, iterations=dilate_45)
    pond_f = ndimage.uniform_filter(pond.astype(np.float32), size=win_315)

    rem_matrix = mangrove & (pond_f >= 0.30)
    rem_adj = mangrove & pond_d
    rem_any = rem_matrix | rem_adj

    # shrimp ponds that have remnant mangrove nearby (interface)
    ponds_with_remnant = pond & mang_d

    return {
        "pixel_m": px_m,
        "mangrove_ha": float(mangrove.sum()) * px_ha,
        "pond_aquaculture_ha": float(pond.sum()) * px_ha,
        "remnant_mangrove_ha": float(rem_any.sum()) * px_ha,
        "remnant_in_pond_matrix_ha": float(rem_matrix.sum()) * px_ha,
        "remnant_adj_pond_45m_ha": float(rem_adj.sum()) * px_ha,
        "pond_with_nearby_mangrove_ha": float(ponds_with_remnant.sum()) * px_ha,
        "pct_ponds_with_remnant_interface": (
            100.0 * float(ponds_with_remnant.sum()) / max(float(pond.sum()), 1.0)
        ),
        "has_remnant_in_aquaculture": bool(rem_any.any()),
    }, mangrove, pond, rem_any, ponds_with_remnant


def save_preview(
    country: str,
    year: int | None,
    mangrove,
    pond,
    rem_any,
    ponds_with_remnant,
    out_path: Path,
) -> None:
    # downsample preview if huge
    h, w = mangrove.shape
    step = max(1, max(h, w) // 2000)
    m = mangrove[::step, ::step]
    p = pond[::step, ::step]
    r = rem_any[::step, ::step]
    pw = ponds_with_remnant[::step, ::step]

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    rgb1 = np.zeros((*m.shape, 3), dtype=float)
    rgb1[..., 2] = p * 0.65
    rgb1[..., 1] = m * 0.85
    rgb1[..., 0] = r
    axes[0].imshow(rgb1, origin="upper")
    axes[0].set_title(f"{country} {year}\npond=blue mangrove=green remnant=red")
    axes[0].axis("off")

    rgb2 = np.zeros((*m.shape, 3), dtype=float)
    rgb2[..., 2] = p * 0.25
    rgb2[..., 0] = pw * 0.9
    rgb2[..., 1] = r * 0.7
    axes[1].imshow(rgb2, origin="upper")
    axes[1].set_title("Shrimp ponds with nearby remnant mangrove\n(pond∩mangrove-neighborhood)=red/yellow")
    axes[1].axis("off")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def write_remnant_geotiff(
    path: Path,
    transform,
    crs,
    pond,
    mangrove,
    rem_any,
    ponds_with_remnant,
) -> None:
    profile = {
        "driver": "GTiff",
        "height": pond.shape[0],
        "width": pond.shape[1],
        "count": 4,
        "dtype": "uint8",
        "crs": crs,
        "transform": transform,
        "compress": "lzw",
        "nodata": 0,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(pond.astype(np.uint8), 1)
        dst.write(mangrove.astype(np.uint8), 2)
        dst.write(rem_any.astype(np.uint8), 3)
        dst.write(ponds_with_remnant.astype(np.uint8), 4)
        dst.set_band_description(1, "pond_aquaculture")
        dst.set_band_description(2, "mangrove")
        dst.set_band_description(3, "remnant_mangrove")
        dst.set_band_description(4, "ponds_with_nearby_remnant_mangrove")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clark-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--max-dim", type=int, default=8000, help="Max raster side; uses overview if larger")
    parser.add_argument("--write-tif", action="store_true", help="Write 4-band remnant GeoTIFFs (large)")
    args = parser.parse_args()

    clark_dir = args.clark_dir
    if not clark_dir.exists():
        raise SystemExit(f"Clark dir not found: {clark_dir}")

    print(f"Clark dir: {clark_dir}")
    extract_zips(clark_dir)
    by_country = list_landcover_tifs(clark_dir)
    if not by_country:
        raise SystemExit("No landcover GeoTIFFs found after extract")

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for country in sorted(by_country):
        tifs = by_country[country]
        tif = pick_year(tifs, args.year)
        years = [int(x) for x in re.findall(r"(?:19|20)\d{2}", tif.name)]
        year = max(years) if years else args.year
        print(f"\n=== {country}  {tif.name} ===")
        try:
            arr, px, transform = read_landcover(tif, max_dim=args.max_dim)
            stats, mangrove, pond, rem_any, ponds_with_remnant = remnant_and_pond_stats(arr, px)
            stats.update({"country": country, "year": year, "source_tif": str(tif)})
            rows.append(stats)
            print(
                f"  mangrove={stats['mangrove_ha']:.0f} ha | ponds={stats['pond_aquaculture_ha']:.0f} ha | "
                f"remnant_mangrove={stats['remnant_mangrove_ha']:.1f} ha | "
                f"ponds_with_remnant={stats['pond_with_nearby_mangrove_ha']:.1f} ha "
                f"({stats['pct_ponds_with_remnant_interface']:.2f}%)"
            )
            preview = OUT / "country_previews" / f"{country}_{year}_remnant_shrimppond.png"
            save_preview(country, year, mangrove, pond, rem_any, ponds_with_remnant, preview)
            print(f"  preview → {preview}")

            if args.write_tif:
                with rasterio.open(tif) as src:
                    crs = src.crs
                tif_out = OUT / "country_rasters" / f"{country}_{year}_remnant_shrimppond.tif"
                write_remnant_geotiff(
                    tif_out, transform, crs, pond, mangrove, rem_any, ponds_with_remnant
                )
                print(f"  geotiff → {tif_out}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}")
            rows.append(
                {
                    "country": country,
                    "year": year,
                    "has_remnant_in_aquaculture": None,
                    "note": str(exc),
                    "source_tif": str(tif),
                }
            )

    df = pd.DataFrame(rows)
    csv_path = OUT / "clark_remnant_mangrove_in_shrimpponds.csv"
    df.to_csv(csv_path, index=False)

    yes = df[df.get("has_remnant_in_aquaculture") == True] if "has_remnant_in_aquaculture" in df else df  # noqa: E712
    summary = OUT / "clark_countries_with_remnant_in_shrimpponds.csv"
    if "has_remnant_in_aquaculture" in df.columns:
        yes = df[df["has_remnant_in_aquaculture"] == True].copy()  # noqa: E712
        yes.to_csv(summary, index=False)
        print(f"\nCountries with remnant mangrove in shrimp-pond landscapes: {len(yes)} / {len(df)}")
        print(sorted(yes["country"].tolist()))
    print(f"Wrote {csv_path}")

    # bar chart
    if "remnant_mangrove_ha" in df.columns:
        plot_df = df.dropna(subset=["remnant_mangrove_ha"]).sort_values(
            "pond_with_nearby_mangrove_ha", ascending=True
        )
        fig, ax = plt.subplots(figsize=(9, 7))
        ax.barh(plot_df["country"], plot_df["pond_with_nearby_mangrove_ha"], color="#c0392b", label="Ponds near remnant mangrove")
        ax.barh(plot_df["country"], plot_df["remnant_mangrove_ha"], color="#27ae60", alpha=0.85, label="Remnant mangrove")
        ax.set_xlabel("Area (ha)")
        ax.set_title("Shrimp-pond landscapes with remnant mangrove (Clark ~2022)")
        ax.legend(loc="lower right")
        fig.tight_layout()
        bar_path = OUT / "clark_remnant_shrimppond_bar.png"
        fig.savefig(bar_path, dpi=160)
        plt.close(fig)
        print(f"Wrote {bar_path}")


if __name__ == "__main__":
    main()
