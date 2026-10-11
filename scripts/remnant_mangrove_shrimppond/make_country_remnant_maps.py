#!/usr/bin/env python3
"""
Produce country-wise remnant mangrove maps from Clark CGA landcover.

For each country (latest year, default 2022):
  - Pond aquaculture (blue)
  - Mangrove (green)
  - Remnant mangrove in aquaculture landscape (red)

Writes:
  outputs/country_maps/<Country>_<year>_remnant_mangrove_map.png
  outputs/country_maps/atlas_remnant_mangrove_all_countries.png
  outputs/country_maps/country_remnant_map_index.csv
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from scipy import ndimage

CLASS_MANGROVE = 1
CLASS_POND = 3

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "country_maps"
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


def list_landcover(clark_dir: Path) -> dict[str, list[Path]]:
    by: dict[str, list[Path]] = {}
    roots = []
    ext = clark_dir / "_extracted"
    if ext.exists():
        roots.append(ext)
    roots.append(clark_dir)
    for root in roots:
        for tif in root.rglob("*.tif"):
            if ".ovr" in tif.name.lower():
                continue
            if "landcover" not in tif.name.lower():
                continue
            c = country_from_name(tif.name)
            by.setdefault(c, []).append(tif)
    return {c: sorted(set(ps), key=lambda p: p.name) for c, ps in by.items()}


def pick_year(tifs: list[Path], year: int | None) -> Path:
    if year is not None:
        y = [p for p in tifs if str(year) in p.name]
        if y:
            return sorted(y, key=lambda p: p.name)[-1]

    def ykey(p: Path) -> int:
        ys = [int(x) for x in re.findall(r"(?:19|20)\d{2}", p.name)]
        return max(ys) if ys else 0

    return sorted(tifs, key=ykey)[-1]


def read_overview(path: Path, max_dim: int = 4500) -> tuple[np.ndarray, float]:
    with rasterio.open(path) as src:
        h, w = src.height, src.width
        if max(h, w) <= max_dim or not src.overviews(1):
            return src.read(1), abs(src.res[0])
        for factor in src.overviews(1):
            out_h, out_w = h // factor, w // factor
            if max(out_h, out_w) <= max_dim:
                arr = src.read(1, out_shape=(out_h, out_w), resampling=Resampling.nearest)
                return arr, abs(src.res[0]) * factor
        factor = src.overviews(1)[-1]
        out_h, out_w = h // factor, w // factor
        arr = src.read(1, out_shape=(out_h, out_w), resampling=Resampling.nearest)
        return arr, abs(src.res[0]) * factor


def remnant_layers(arr: np.ndarray, px_m: float):
    dilate_45 = max(1, int(round(45.0 / px_m)))
    win = max(3, int(round(315.0 / px_m)))
    if win % 2 == 0:
        win += 1
    mangrove = arr == CLASS_MANGROVE
    pond = arr == CLASS_POND
    pond_d = ndimage.binary_dilation(pond, iterations=dilate_45)
    pond_f = ndimage.uniform_filter(pond.astype(np.float32), size=win)
    rem = mangrove & ((pond_f >= 0.30) | pond_d)
    mang_d = ndimage.binary_dilation(mangrove, iterations=dilate_45)
    ponds_near = pond & mang_d
    px_ha = (px_m * px_m) / 10000.0
    stats = {
        "mangrove_ha": float(mangrove.sum()) * px_ha,
        "pond_ha": float(pond.sum()) * px_ha,
        "remnant_mangrove_ha": float(rem.sum()) * px_ha,
        "pond_with_nearby_mangrove_ha": float(ponds_near.sum()) * px_ha,
    }
    return mangrove, pond, rem, ponds_near, stats


def crop_to_content(*masks: np.ndarray, pad: int = 20):
    union = np.zeros_like(masks[0], dtype=bool)
    for m in masks:
        union |= m.astype(bool)
    if not union.any():
        return [m for m in masks], (0, masks[0].shape[0], 0, masks[0].shape[1])
    rows = np.any(union, axis=1)
    cols = np.any(union, axis=0)
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    r0 = max(0, r0 - pad)
    c0 = max(0, c0 - pad)
    r1 = min(masks[0].shape[0], r1 + pad + 1)
    c1 = min(masks[0].shape[1], c1 + pad + 1)
    return [m[r0:r1, c0:c1] for m in masks], (r0, r1, c0, c1)


def make_country_map(
    country: str,
    year: int,
    mangrove,
    pond,
    rem,
    ponds_near,
    stats: dict,
    out_path: Path,
) -> None:
    # Crop to coastal content for readability
    (pond_c, mang_c, rem_c, near_c), _ = crop_to_content(pond, mangrove, rem, ponds_near, pad=30)

    # Downsample display if still large
    h, w = pond_c.shape
    step = max(1, max(h, w) // 2500)
    pond_d = pond_c[::step, ::step]
    mang_d = mang_c[::step, ::step]
    rem_d = rem_c[::step, ::step]
    near_d = near_c[::step, ::step]

    fig = plt.figure(figsize=(11, 8), facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0], wspace=0.08)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    # Left: context (ponds + all mangrove + remnant)
    rgb1 = np.zeros((*pond_d.shape, 3), dtype=float)
    rgb1[:] = 0.94  # light gray land/background inside AOI
    # keep nodata-ish dark only where nothing mapped — use pale bg everywhere in crop
    rgb1[pond_d] = (0.12, 0.40, 0.75)
    rgb1[mang_d] = (0.15, 0.55, 0.22)
    rgb1[rem_d] = (0.85, 0.10, 0.10)
    ax1.imshow(rgb1, origin="upper", interpolation="nearest")
    ax1.set_title("Ponds · mangrove · remnant", fontsize=11, pad=8)
    ax1.set_xticks([])
    ax1.set_yticks([])
    for spine in ax1.spines.values():
        spine.set_linewidth(0.6)
        spine.set_color("#444444")

    # Right: shrimp ponds that still have remnant mangrove nearby
    rgb2 = np.zeros((*pond_d.shape, 3), dtype=float)
    rgb2[:] = 0.94
    rgb2[pond_d] = (0.70, 0.80, 0.90)  # all ponds (faint)
    rgb2[near_d] = (0.80, 0.15, 0.10)  # ponds with remnant interface
    rgb2[rem_d] = (0.95, 0.55, 0.10)  # remnant mangrove highlights
    ax2.imshow(rgb2, origin="upper", interpolation="nearest")
    ax2.set_title("Shrimp ponds with remnant mangrove", fontsize=11, pad=8)
    ax2.set_xticks([])
    ax2.set_yticks([])
    for spine in ax2.spines.values():
        spine.set_linewidth(0.6)
        spine.set_color("#444444")

    legend1 = [
        mpatches.Patch(color=(0.12, 0.40, 0.75), label="Pond aquaculture"),
        mpatches.Patch(color=(0.15, 0.55, 0.22), label="Mangrove"),
        mpatches.Patch(color=(0.85, 0.10, 0.10), label="Remnant mangrove"),
    ]
    legend2 = [
        mpatches.Patch(color=(0.70, 0.80, 0.90), label="All ponds"),
        mpatches.Patch(color=(0.80, 0.15, 0.10), label="Ponds ≤45 m from mangrove"),
        mpatches.Patch(color=(0.95, 0.55, 0.10), label="Remnant mangrove"),
    ]
    ax1.legend(handles=legend1, loc="lower left", fontsize=8, framealpha=0.92)
    ax2.legend(handles=legend2, loc="lower left", fontsize=8, framealpha=0.92)

    fig.suptitle(
        f"{country} — Remnant mangrove in shrimp-pond areas (Clark {year})",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.5,
        0.02,
        (
            f"Mangrove {stats['mangrove_ha']:,.0f} ha  ·  "
            f"Ponds {stats['pond_ha']:,.0f} ha  ·  "
            f"Remnant mangrove {stats['remnant_mangrove_ha']:,.0f} ha  ·  "
            f"Ponds with remnant {stats['pond_with_nearby_mangrove_ha']:,.0f} ha"
        ),
        ha="center",
        fontsize=9,
        color="#222222",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_atlas(rows: list[dict], preview_dir: Path, out_path: Path) -> None:
    countries = [r["country"] for r in rows]
    n = len(countries)
    ncols = 4
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 3.6 * nrows), facecolor="white")
    axes = np.atleast_2d(axes)
    for i, r in enumerate(rows):
        ax = axes[i // ncols, i % ncols]
        png = preview_dir / f"{r['country']}_{r['year']}_remnant_mangrove_map.png"
        if png.exists():
            img = plt.imread(png)
            # show only left panel roughly by cropping center-left if wide; else full
            ax.imshow(img)
        ax.set_title(
            f"{r['country']}\nremnant {r['remnant_mangrove_ha']:,.0f} ha",
            fontsize=9,
        )
        ax.axis("off")
    for j in range(n, nrows * ncols):
        axes[j // ncols, j % ncols].axis("off")
    fig.suptitle(
        "Country-wise remnant mangrove in shrimp-pond areas (Clark ~2022)",
        fontsize=15,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clark-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--max-dim", type=int, default=4500)
    args = parser.parse_args()

    clark_dir = args.clark_dir
    if not clark_dir.exists():
        raise SystemExit(f"Clark dir not found: {clark_dir}")

    by = list_landcover(clark_dir)
    if not by:
        raise SystemExit("No Clark landcover GeoTIFFs found (extract zips first)")

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for country in sorted(by):
        tif = pick_year(by[country], args.year)
        years = [int(x) for x in re.findall(r"(?:19|20)\d{2}", tif.name)]
        year = max(years) if years else args.year
        print(f"{country:15s} {tif.name}")
        arr, px = read_overview(tif, max_dim=args.max_dim)
        mangrove, pond, rem, ponds_near, stats = remnant_layers(arr, px)
        stats.update({"country": country, "year": year, "source_tif": str(tif)})
        rows.append(stats)
        out_png = OUT / f"{country}_{year}_remnant_mangrove_map.png"
        make_country_map(country, year, mangrove, pond, rem, ponds_near, stats, out_png)
        print(
            f"  remnant={stats['remnant_mangrove_ha']:.0f} ha | "
            f"ponds_with_remnant={stats['pond_with_nearby_mangrove_ha']:.0f} ha → {out_png.name}"
        )

    df = pd.DataFrame(rows).sort_values("remnant_mangrove_ha", ascending=False)
    idx = OUT / "country_remnant_map_index.csv"
    df.to_csv(idx, index=False)
    print(f"Wrote {idx}")

    atlas = OUT / "atlas_remnant_mangrove_all_countries.png"
    make_atlas(df.to_dict("records"), OUT, atlas)
    print(f"Wrote {atlas}")
    print(f"\nCountry-wise maps: {OUT}")


if __name__ == "__main__":
    main()
