#!/usr/bin/env python3
"""
Country-wise remnant mangrove maps — improved remnant definition.

Clark maps mangrove (1) and pond aquaculture (3) as mutually exclusive classes,
so remnant cannot be read as pixel overlap. We define remnant as:

  Isolated / small mangrove patches that are enclosed by shrimp ponds.

Rules (connected mangrove patches):
  1. Label 4-connected mangrove patches
  2. For each patch, measure pond fraction in a ~150 m ring around it
  3. Keep patch as remnant if:
       - area ≤ MAX_PATCH_HA and pond_frac ≥ MIN_POND_FRAC
       OR pond_frac ≥ HIGH_POND_FRAC and area ≤ MAX_ENCLOSED_HA
  4. Large continuous mangrove (e.g. Sundarbans core) is NOT remnant,
     even where its outer edge touches ponds

Outputs under outputs/country_maps_v2/
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

# Remnant patch rules (grounded distances; scaled to pixel size)
MAX_PATCH_HA = 50.0          # small remnant fragments
MIN_POND_FRAC = 0.30         # min pond share in ring for small patches
HIGH_POND_FRAC = 0.55        # strongly pond-enclosed
MAX_ENCLOSED_HA = 200.0      # max size for strongly enclosed IMA-style patches
RING_M = 150.0               # ring width around patch to score pond enclosure

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "country_maps_v2"
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
            if ".ovr" in tif.name.lower() or "landcover" not in tif.name.lower():
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


def read_overview(path: Path, max_dim: int = 12000, target_px_m: float = 120.0) -> tuple[np.ndarray, float]:
    """
    Read landcover at a resolution suitable for remnant-patch detection.

    Prefer pixel size ≤ target_px_m so small pond-enclosed mangrove patches
    are not merged away. Cap long-side length at max_dim for memory.
    """
    with rasterio.open(path) as src:
        native = abs(src.res[0])
        h, w = src.height, src.width
        factors = [1] + list(src.overviews(1) or [])

        candidates = []
        for f in factors:
            px = native * f
            out_h = max(1, h // f)
            out_w = max(1, w // f)
            if max(out_h, out_w) <= max_dim:
                candidates.append((f, px, out_h, out_w))

        if not candidates:
            f = factors[-1]
            px = native * f
            out_h, out_w = max(1, h // f), max(1, w // f)
            chosen = (f, px, out_h, out_w)
        else:
            ok = [c for c in candidates if c[1] <= target_px_m]
            # finest (smallest factor) among those meeting target px, else finest that fits
            chosen = min(ok or candidates, key=lambda c: c[0])

        f, px, out_h, out_w = chosen
        if f == 1:
            arr = src.read(1)
        else:
            arr = src.read(1, out_shape=(out_h, out_w), resampling=Resampling.nearest)
        return arr, px


def map_remnant_patches(
    mangrove: np.ndarray,
    pond: np.ndarray,
    px_m: float,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Return remnant mask, ponds-near-remnant mask, and stats.
    Uses connected mangrove patches + pond enclosure in a ring.
    """
    px_ha = (px_m * px_m) / 10000.0
    ring_iter = max(1, int(round(RING_M / px_m)))
    near_iter = max(1, int(round(45.0 / px_m)))
    max_keep_px = int(MAX_ENCLOSED_HA / px_ha) + 1

    structure = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)  # 4-connected
    labels, nlab = ndimage.label(mangrove, structure=structure)
    remnant = np.zeros_like(mangrove, dtype=bool)
    n_remnant_patches = 0

    # Cropped per-object loop — skip giant continuous forests by bbox pixel count
    slices = ndimage.find_objects(labels)
    for lab, slc in enumerate(slices, start=1):
        if slc is None:
            continue
        # Expand slice a bit for ring calculation
        r0, r1 = slc[0].start, slc[0].stop
        c0, c1 = slc[1].start, slc[1].stop
        pad = ring_iter + 1
        r0p, r1p = max(0, r0 - pad), min(labels.shape[0], r1 + pad)
        c0p, c1p = max(0, c0 - pad), min(labels.shape[1], c1 + pad)
        sub_lab = labels[r0p:r1p, c0p:c1p]
        sub_pond = pond[r0p:r1p, c0p:c1p]
        patch = sub_lab == lab
        npix = int(patch.sum())
        if npix == 0 or npix > max_keep_px:
            continue
        area_ha = npix * px_ha

        dilated = ndimage.binary_dilation(patch, iterations=ring_iter)
        ring = dilated & ~patch
        if not ring.any():
            continue
        pond_frac = float(sub_pond[ring].mean())

        keep = (area_ha <= MAX_PATCH_HA and pond_frac >= MIN_POND_FRAC) or (
            area_ha <= MAX_ENCLOSED_HA and pond_frac >= HIGH_POND_FRAC
        )
        if keep:
            remnant[r0p:r1p, c0p:c1p][patch] = True
            n_remnant_patches += 1

    rem_d = ndimage.binary_dilation(remnant, iterations=near_iter) if remnant.any() else remnant
    ponds_near = pond & rem_d

    stats = {
        "mangrove_ha": float(mangrove.sum()) * px_ha,
        "pond_ha": float(pond.sum()) * px_ha,
        "n_mangrove_patches": int(nlab),
        "n_remnant_patches": int(n_remnant_patches),
        "remnant_mangrove_ha": float(remnant.sum()) * px_ha,
        "pond_with_nearby_mangrove_ha": float(ponds_near.sum()) * px_ha,
        "max_patch_ha": MAX_PATCH_HA,
        "min_pond_frac": MIN_POND_FRAC,
        "high_pond_frac": HIGH_POND_FRAC,
        "max_enclosed_ha": MAX_ENCLOSED_HA,
    }
    return remnant, ponds_near, stats


def crop_to_content(*masks: np.ndarray, pad: int = 30):
    union = np.zeros_like(masks[0], dtype=bool)
    for m in masks:
        union |= np.asarray(m, dtype=bool)
    if not union.any():
        return list(masks), (0, masks[0].shape[0], 0, masks[0].shape[1])
    rows = np.any(union, axis=1)
    cols = np.any(union, axis=0)
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    r0 = max(0, r0 - pad)
    c0 = max(0, c0 - pad)
    r1 = min(masks[0].shape[0], r1 + pad + 1)
    c1 = min(masks[0].shape[1], c1 + pad + 1)
    return [m[r0:r1, c0:c1] for m in masks], (r0, r1, c0, c1)


def make_country_map(country, year, mangrove, pond, rem, ponds_near, stats, out_path: Path):
    (pond_c, mang_c, rem_c, near_c), _ = crop_to_content(pond, mangrove, rem, ponds_near)
    h, w = pond_c.shape
    step = max(1, max(h, w) // 2500)
    pond_d, mang_d, rem_d, near_d = (
        pond_c[::step, ::step],
        mang_c[::step, ::step],
        rem_c[::step, ::step],
        near_c[::step, ::step],
    )

    fig = plt.figure(figsize=(11, 8), facecolor="white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0], wspace=0.08)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    rgb1 = np.full((*pond_d.shape, 3), 0.94)
    rgb1[pond_d] = (0.12, 0.40, 0.75)
    rgb1[mang_d] = (0.15, 0.55, 0.22)
    rgb1[rem_d] = (0.85, 0.10, 0.10)
    ax1.imshow(rgb1, origin="upper", interpolation="nearest")
    ax1.set_title("Ponds · mangrove · remnant patches", fontsize=11)
    ax1.set_xticks([])
    ax1.set_yticks([])

    rgb2 = np.full((*pond_d.shape, 3), 0.94)
    rgb2[pond_d] = (0.70, 0.80, 0.90)
    rgb2[near_d] = (0.80, 0.15, 0.10)
    rgb2[rem_d] = (0.95, 0.55, 0.10)
    ax2.imshow(rgb2, origin="upper", interpolation="nearest")
    ax2.set_title("Shrimp ponds next to remnant patches", fontsize=11)
    ax2.set_xticks([])
    ax2.set_yticks([])

    ax1.legend(
        handles=[
            mpatches.Patch(color=(0.12, 0.40, 0.75), label="Pond aquaculture"),
            mpatches.Patch(color=(0.15, 0.55, 0.22), label="Mangrove (all)"),
            mpatches.Patch(color=(0.85, 0.10, 0.10), label="Remnant patch"),
        ],
        loc="lower left",
        fontsize=8,
        framealpha=0.92,
    )
    ax2.legend(
        handles=[
            mpatches.Patch(color=(0.70, 0.80, 0.90), label="All ponds"),
            mpatches.Patch(color=(0.80, 0.15, 0.10), label="Ponds near remnant"),
            mpatches.Patch(color=(0.95, 0.55, 0.10), label="Remnant patch"),
        ],
        loc="lower left",
        fontsize=8,
        framealpha=0.92,
    )

    fig.suptitle(
        f"{country} — Remnant mangrove patches in shrimp-pond areas (Clark {year})",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.5,
        0.02,
        (
            f"Mangrove {stats['mangrove_ha']:,.0f} ha  ·  "
            f"Ponds {stats['pond_ha']:,.0f} ha  ·  "
            f"Remnant patches {stats['n_remnant_patches']:,} "
            f"({stats['remnant_mangrove_ha']:,.0f} ha)  ·  "
            f"Ponds near remnant {stats['pond_with_nearby_mangrove_ha']:,.0f} ha"
        ),
        ha="center",
        fontsize=9,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_atlas(rows: list[dict], map_dir: Path, out_path: Path) -> None:
    n = len(rows)
    ncols = 4
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 3.6 * nrows), facecolor="white")
    axes = np.atleast_2d(axes)
    for i, r in enumerate(rows):
        ax = axes[i // ncols, i % ncols]
        png = map_dir / f"{r['country']}_{r['year']}_remnant_mangrove_map.png"
        if png.exists():
            ax.imshow(plt.imread(png))
        ax.set_title(
            f"{r['country']}\n{r['n_remnant_patches']} patches · {r['remnant_mangrove_ha']:,.0f} ha",
            fontsize=9,
        )
        ax.axis("off")
    for j in range(n, nrows * ncols):
        axes[j // ncols, j % ncols].axis("off")
    fig.suptitle(
        "Remnant mangrove patches inside shrimp-pond landscapes (improved definition)",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clark-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--max-dim", type=int, default=12000)
    parser.add_argument("--target-px", type=float, default=120.0, help="Target max pixel size (m) for remnant detection")
    args = parser.parse_args()

    by = list_landcover(args.clark_dir)
    if not by:
        raise SystemExit("No Clark landcover GeoTIFFs found")

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for country in sorted(by):
        tif = pick_year(by[country], args.year)
        years = [int(x) for x in re.findall(r"(?:19|20)\d{2}", tif.name)]
        year = max(years) if years else args.year
        print(f"{country:15s} {tif.name}")
        arr, px = read_overview(tif, max_dim=args.max_dim, target_px_m=args.target_px)
        print(f"  read shape={arr.shape} px={px:.1f} m")
        mangrove = arr == CLASS_MANGROVE
        pond = arr == CLASS_POND
        rem, ponds_near, stats = map_remnant_patches(mangrove, pond, px)
        stats.update({"country": country, "year": year, "source_tif": str(tif), "pixel_m": px})
        rows.append(stats)
        out_png = OUT / f"{country}_{year}_remnant_mangrove_map.png"
        make_country_map(country, year, mangrove, pond, rem, ponds_near, stats, out_png)
        print(
            f"  patches={stats['n_remnant_patches']}  "
            f"remnant={stats['remnant_mangrove_ha']:.1f} ha  "
            f"ponds_near={stats['pond_with_nearby_mangrove_ha']:.1f} ha"
        )

    df = pd.DataFrame(rows).sort_values("remnant_mangrove_ha", ascending=False)
    df.to_csv(OUT / "country_remnant_map_index.csv", index=False)
    make_atlas(df.to_dict("records"), OUT, OUT / "atlas_remnant_mangrove_all_countries.png")

    print("\n=== Improved remnant summary ===")
    print(
        df[
            [
                "country",
                "n_remnant_patches",
                "remnant_mangrove_ha",
                "pond_with_nearby_mangrove_ha",
            ]
        ].to_string(index=False)
    )
    print(f"\nMaps → {OUT}")


if __name__ == "__main__":
    main()
