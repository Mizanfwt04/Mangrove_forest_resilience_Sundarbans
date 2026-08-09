#!/usr/bin/env python3
"""
Country-wise remnant mangrove maps — v3 (strict pond-enclosed patches).

Why v1/v2 were imperfect
------------------------
* v1 counted any mangrove ≤45 m from ponds → Sundarbans / large-forest
  fringe was painted as "remnant".
* v2 used connected patches but pond_frac ≥ 0.30 was still too loose, so
  many forest-edge fragments remained.
* Clark itself under-maps true field remnants: Chakaria RMSP GPS points are
  class 5 (Other), not mangrove, and sit kilometres from Clark ponds.

v3 remnant definition
---------------------
Connected mangrove patches kept only when BOTH hold:

  1. area ≤ MAX_PATCH_HA (default 40 ha), OR
     area ≤ MAX_ENCLOSED_HA (default 120 ha) with stronger enclosure
  2. pond fraction in a ~150 m ring around the patch ≥ threshold
       - small patches: MIN_POND_FRAC (default 0.45)
       - larger patches: HIGH_POND_FRAC (default 0.65)

Large continuous mangrove is never remnant. Edge fragments of big forests
fail the higher pond-enclosure bar more often than true pond-island scraps.

Also writes Clark vs field-site validation for Chakaria RMSP/PMSP/PMWSP.
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
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window, from_bounds
from scipy import ndimage

CLASS_MANGROVE = 1
CLASS_POND = 3
CLASS_OTHER = 5

# Stricter than v2
MAX_PATCH_HA = 40.0
MIN_POND_FRAC = 0.45
HIGH_POND_FRAC = 0.65
MAX_ENCLOSED_HA = 120.0
RING_M = 150.0
NEAR_M = 45.0

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "country_maps_v3"
DEFAULT_DIR = ROOT.parent / "outputs" / "agb_stability" / "shrimppond"
SITES_CSV = ROOT / "data" / "chakaria_sites.csv"


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
            if "change" in tif.name.lower() and "landcover" not in tif.name.lower():
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


def choose_overview_factor(
    src, max_dim: int = 12000, target_px_m: float = 90.0
) -> tuple[int, float, int, int]:
    native = abs(src.res[0])
    h, w = src.height, src.width
    factors = [1] + list(src.overviews(1) or [])
    candidates = []
    for f in factors:
        px = native * f
        out_h, out_w = max(1, h // f), max(1, w // f)
        if max(out_h, out_w) <= max_dim:
            candidates.append((f, px, out_h, out_w))
    if not candidates:
        f = factors[-1]
        return f, native * f, max(1, h // f), max(1, w // f)
    ok = [c for c in candidates if c[1] <= target_px_m]
    return min(ok or candidates, key=lambda c: c[0])


def read_overview(
    path: Path, max_dim: int = 12000, target_px_m: float = 90.0
) -> tuple[np.ndarray, float]:
    """Read landcover near target_px_m so small pond-islands survive."""
    with rasterio.open(path) as src:
        f, px, out_h, out_w = choose_overview_factor(src, max_dim, target_px_m)
        if f == 1:
            arr = src.read(1)
        else:
            arr = src.read(1, out_shape=(out_h, out_w), resampling=Resampling.nearest)
        return arr, px


def map_remnant_tiled(
    path: Path,
    target_px_m: float = 60.0,
    tile_px: int = 3500,
    pond_pad_m: float = 2500.0,
    display_max_dim: int = 12000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, dict]:
    """
    Accurate remnant detection for huge rasters.

    1. Coarse overview for national display + pond locations
    2. Fine tiles (~target_px_m) only where ponds exist
    3. Stamp fine remnant/ponds-near onto the coarse canvas
    """
    with rasterio.open(path) as src:
        native = abs(src.res[0])
        # display canvas
        df, dpx, dh, dw = choose_overview_factor(src, display_max_dim, target_px_m=240.0)
        display = src.read(1, out_shape=(dh, dw), resampling=Resampling.nearest) if df > 1 else src.read(1)
        mangrove_d = display == CLASS_MANGROVE
        pond_d = display == CLASS_POND
        remnant_d = np.zeros_like(display, dtype=bool)
        near_d = np.zeros_like(display, dtype=bool)

        # fine read factor
        fine_f = max(1, int(round(target_px_m / native)))
        # snap to available overview if close
        ovrs = [1] + list(src.overviews(1) or [])
        fine_f = min(ovrs, key=lambda x: abs(x - fine_f))
        fine_px = native * fine_f
        fine_h, fine_w = max(1, src.height // fine_f), max(1, src.width // fine_f)

        # pond mask at moderate res to find tiles (≤240 m)
        loc_f, loc_px, loc_h, loc_w = choose_overview_factor(src, max_dim=8000, target_px_m=240.0)
        loc = src.read(1, out_shape=(loc_h, loc_w), resampling=Resampling.nearest) if loc_f > 1 else src.read(1)
        pond_loc = loc == CLASS_POND
        pad_loc = max(1, int(round(pond_pad_m / loc_px)))
        pond_zone = ndimage.binary_dilation(pond_loc, iterations=pad_loc) if pond_loc.any() else pond_loc

        # tile coordinates in fine grid
        scale_loc_to_fine = fine_f / loc_f
        # iterate tiles on fine grid, skip empty
        n_tiles = 0
        rem_ha = 0.0
        near_ha = 0.0
        n_patches = 0
        pond_fracs: list[float] = []
        px_ha_fine = (fine_px * fine_px) / 10000.0
        covered = np.zeros((fine_h, fine_w), dtype=bool)  # avoid double-count on overlap

        # Build list of fine-grid bounding boxes from pond_zone components
        lab, nlab = ndimage.label(pond_zone)
        slices = ndimage.find_objects(lab) if nlab else []
        windows = []
        for slc in slices:
            if slc is None:
                continue
            r0 = int(slc[0].start * scale_loc_to_fine)
            r1 = int(np.ceil(slc[0].stop * scale_loc_to_fine))
            c0 = int(slc[1].start * scale_loc_to_fine)
            c1 = int(np.ceil(slc[1].stop * scale_loc_to_fine))
            r0, c0 = max(0, r0), max(0, c0)
            r1, c1 = min(fine_h, r1), min(fine_w, c1)
            # split large components into tile_px chunks
            for rr in range(r0, r1, tile_px):
                for cc in range(c0, c1, tile_px):
                    windows.append((rr, min(r1, rr + tile_px), cc, min(c1, cc + tile_px)))

        # dedupe windows
        windows = sorted(set(windows))
        print(f"  tiled: {len(windows)} pond-region tiles at {fine_px:.0f} m")

        for r0, r1, c0, c1 in windows:
            # map fine window → native window
            nr0, nr1 = r0 * fine_f, r1 * fine_f
            nc0, nc1 = c0 * fine_f, c1 * fine_f
            nr1 = min(src.height, nr1)
            nc1 = min(src.width, nc1)
            if nr1 <= nr0 or nc1 <= nc0:
                continue
            out_h = max(1, (nr1 - nr0) // fine_f)
            out_w = max(1, (nc1 - nc0) // fine_f)
            win = Window(nc0, nr0, nc1 - nc0, nr1 - nr0)
            tile = src.read(1, window=win, out_shape=(out_h, out_w), resampling=Resampling.nearest)
            mang = tile == CLASS_MANGROVE
            pond = tile == CLASS_POND
            if not pond.any() or not mang.any():
                continue
            rem, near, st = map_remnant_patches(mang, pond, fine_px)
            n_tiles += 1
            # accumulate unique remnant pixels in fine grid space
            # tile may be slightly smaller than (r1-r0,c1-c0)
            th, tw = rem.shape
            fr0, fc0 = r0, c0
            fr1, fc1 = min(fine_h, fr0 + th), min(fine_w, fc0 + tw)
            th, tw = fr1 - fr0, fc1 - fc0
            rem = rem[:th, :tw]
            near = near[:th, :tw]
            new_rem = rem & ~covered[fr0:fr1, fc0:fc1]
            rem_ha += float(new_rem.sum()) * px_ha_fine
            near_ha += float((near & ~covered[fr0:fr1, fc0:fc1]).sum()) * px_ha_fine
            # patch count: only count patches fully interior to avoid edge double-count — approximate
            n_patches += int(st["n_remnant_patches"])
            if st["median_remnant_pond_frac"] > 0:
                pond_fracs.append(st["median_remnant_pond_frac"])
            covered[fr0:fr1, fc0:fc1] |= rem | near

            # stamp onto display canvas
            scale_f_to_d = df / fine_f
            dr0 = int(fr0 / scale_f_to_d) if scale_f_to_d >= 1 else int(fr0 * (fine_f / df))
            # fine_f and df are both overview factors relative to native
            # display index = fine_index * fine_f / df
            dr0 = int(fr0 * fine_f / df)
            dr1 = int(np.ceil(fr1 * fine_f / df))
            dc0 = int(fc0 * fine_f / df)
            dc1 = int(np.ceil(fc1 * fine_f / df))
            dr0, dc0 = max(0, dr0), max(0, dc0)
            dr1, dc1 = min(dh, dr1), min(dw, dc1)
            if dr1 <= dr0 or dc1 <= dc0:
                continue
            # downsample rem/near into display block
            block_r = rem_d[dr0:dr1, dc0:dc1]
            # map each display pixel from fine
            # simple: any fine remnant in the display cell
            yy = np.arange(dr0, dr1)
            xx = np.arange(dc0, dc1)
            # convert display coords to fine
            fy = np.clip((yy * df) // fine_f - fr0, 0, th - 1)
            fx = np.clip((xx * df) // fine_f - fc0, 0, tw - 1)
            # paint rows
            for i, y in enumerate(fy):
                remnant_d[dr0 + i, dc0:dc1] |= rem[y, fx]
                near_d[dr0 + i, dc0:dc1] |= near[y, fx]

        # patch count overestimate from tile overlaps — recompute from covered remnant if feasible
        # Use unique rem_ha; estimate patches from fine covered remnant components at display for reporting
        # Prefer re-labeling stamped remnant at display for n_patches display consistency
        n_patches_disp = int(ndimage.label(remnant_d)[1]) if remnant_d.any() else 0

        stats = {
            "mangrove_ha": float(mangrove_d.sum()) * (dpx * dpx) / 10000.0,
            "pond_ha": float(pond_d.sum()) * (dpx * dpx) / 10000.0,
            "n_mangrove_patches": int(ndimage.label(mangrove_d)[1]),
            "n_remnant_patches": n_patches_disp,
            "remnant_mangrove_ha": rem_ha,
            "pond_with_nearby_mangrove_ha": near_ha,
            "median_remnant_pond_frac": float(np.median(pond_fracs)) if pond_fracs else 0.0,
            "max_patch_ha": MAX_PATCH_HA,
            "min_pond_frac": MIN_POND_FRAC,
            "high_pond_frac": HIGH_POND_FRAC,
            "max_enclosed_ha": MAX_ENCLOSED_HA,
            "fine_pixel_m": fine_px,
            "display_pixel_m": dpx,
            "n_tiles_processed": n_tiles,
        }
        return mangrove_d, pond_d, remnant_d, near_d, dpx, stats


def map_remnant_patches(
    mangrove: np.ndarray,
    pond: np.ndarray,
    px_m: float,
) -> tuple[np.ndarray, np.ndarray, dict]:
    px_ha = (px_m * px_m) / 10000.0
    ring_iter = max(1, int(round(RING_M / px_m)))
    near_iter = max(1, int(round(NEAR_M / px_m)))
    max_keep_px = int(MAX_ENCLOSED_HA / px_ha) + 1

    structure = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
    labels, nlab = ndimage.label(mangrove, structure=structure)
    remnant = np.zeros_like(mangrove, dtype=bool)
    n_remnant_patches = 0
    pond_fracs = []

    slices = ndimage.find_objects(labels)
    for lab, slc in enumerate(slices, start=1):
        if slc is None:
            continue
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
            pond_fracs.append(pond_frac)

    rem_d = ndimage.binary_dilation(remnant, iterations=near_iter) if remnant.any() else remnant
    ponds_near = pond & rem_d

    stats = {
        "mangrove_ha": float(mangrove.sum()) * px_ha,
        "pond_ha": float(pond.sum()) * px_ha,
        "n_mangrove_patches": int(nlab),
        "n_remnant_patches": int(n_remnant_patches),
        "remnant_mangrove_ha": float(remnant.sum()) * px_ha,
        "pond_with_nearby_mangrove_ha": float(ponds_near.sum()) * px_ha,
        "median_remnant_pond_frac": float(np.median(pond_fracs)) if pond_fracs else 0.0,
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


def densest_remnant_window(
    remnant: np.ndarray, pond: np.ndarray, win: int = 400
) -> tuple[slice, slice] | None:
    """Return row/col slices around the densest remnant+pond hotspot."""
    if not remnant.any():
        return None
    # coarse density on ~win/4 grid for speed
    step = max(1, win // 8)
    dens = ndimage.uniform_filter(
        (remnant.astype(np.float32) * 3.0 + pond.astype(np.float32)),
        size=max(3, win // step),
    )
    dens = dens[::step, ::step]
    # mask to remnant-present coarse cells
    rem_c = ndimage.maximum_filter(remnant.astype(np.uint8), size=win)[::step, ::step]
    dens = np.where(rem_c > 0, dens, -1)
    if dens.max() < 0:
        return None
    iy, ix = np.unravel_index(int(np.argmax(dens)), dens.shape)
    cy, cx = iy * step, ix * step
    half = win // 2
    r0 = max(0, cy - half)
    c0 = max(0, cx - half)
    r1 = min(remnant.shape[0], r0 + win)
    c1 = min(remnant.shape[1], c0 + win)
    r0 = max(0, r1 - win)
    c0 = max(0, c1 - win)
    return slice(r0, r1), slice(c0, c1)


def make_country_map(
    country, year, mangrove, pond, rem, ponds_near, stats, out_path: Path, px_m: float
):
    (pond_c, mang_c, rem_c, near_c), _ = crop_to_content(pond, mangrove, rem, ponds_near)
    h, w = pond_c.shape
    step = max(1, max(h, w) // 2500)
    pond_d, mang_d, rem_d, near_d = (
        pond_c[::step, ::step],
        mang_c[::step, ::step],
        rem_c[::step, ::step],
        near_c[::step, ::step],
    )

    fig = plt.figure(figsize=(14, 7.2), facecolor="white")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.05, 1.0], wspace=0.08)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])

    rgb1 = np.full((*pond_d.shape, 3), 0.94)
    rgb1[pond_d] = (0.12, 0.40, 0.75)
    rgb1[mang_d] = (0.15, 0.55, 0.22)
    rgb1[rem_d] = (0.85, 0.10, 0.10)
    ax1.imshow(rgb1, origin="upper", interpolation="nearest")
    ax1.set_title("National: ponds · mangrove · remnant", fontsize=10)
    ax1.set_xticks([])
    ax1.set_yticks([])
    ax1.legend(
        handles=[
            mpatches.Patch(color=(0.12, 0.40, 0.75), label="Pond aquaculture"),
            mpatches.Patch(color=(0.15, 0.55, 0.22), label="Mangrove (all)"),
            mpatches.Patch(color=(0.85, 0.10, 0.10), label="Remnant (v3)"),
        ],
        loc="lower left",
        fontsize=7,
        framealpha=0.92,
    )

    rgb2 = np.full((*pond_d.shape, 3), 0.94)
    rgb2[pond_d] = (0.70, 0.80, 0.90)
    rgb2[near_d] = (0.80, 0.15, 0.10)
    rgb2[rem_d] = (0.95, 0.55, 0.10)
    ax2.imshow(rgb2, origin="upper", interpolation="nearest")
    ax2.set_title("Ponds next to remnant patches", fontsize=10)
    ax2.set_xticks([])
    ax2.set_yticks([])

    # Hotspot inset so small remnants are actually visible
    win_px = max(200, int(round(25000 / px_m)))  # ~25 km window
    hot = densest_remnant_window(rem, pond, win=win_px)
    if hot is not None:
        rs, cs = hot
        rgb3 = np.full((rs.stop - rs.start, cs.stop - cs.start, 3), 0.94)
        rgb3[pond[rs, cs]] = (0.12, 0.40, 0.75)
        rgb3[mangrove[rs, cs]] = (0.15, 0.55, 0.22)
        rgb3[rem[rs, cs]] = (0.85, 0.10, 0.10)
        ax3.imshow(rgb3, origin="upper", interpolation="nearest")
        ax3.set_title("Hotspot (~25 km) — remnant in ponds", fontsize=10)
    else:
        ax3.text(0.5, 0.5, "No remnant patches", ha="center", va="center")
        ax3.set_facecolor("0.94")
    ax3.set_xticks([])
    ax3.set_yticks([])

    fig.suptitle(
        f"{country} — Remnant mangrove inside shrimp-pond landscapes (Clark {year}, v3)",
        fontsize=12,
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
            f"Rule: ≤{MAX_PATCH_HA:.0f} ha & pond-ring ≥{MIN_POND_FRAC:.0%} "
            f"(or ≤{MAX_ENCLOSED_HA:.0f} ha & ≥{HIGH_POND_FRAC:.0%})"
        ),
        ha="center",
        fontsize=8.5,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170, bbox_inches="tight", facecolor="white")
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
        "Remnant mangrove patches enclosed by shrimp ponds (v3 strict definition)",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def validate_chakaria_sites(clark_dir: Path, year: int, out_dir: Path) -> pd.DataFrame:
    """Compare Clark classes at field RMSP/PMSP/PMWSP GPS points."""
    by = list_landcover(clark_dir)
    if "Bangladesh" not in by:
        return pd.DataFrame()
    tif = pick_year(by["Bangladesh"], year)
    sites = pd.read_csv(SITES_CSV)
    class_names = {
        0: "nodata",
        1: "mangrove",
        2: "coastal_wetland",
        3: "pond_aquaculture",
        4: "water",
        5: "other",
        6: "missing",
    }

    with rasterio.open(tif) as src:
        xs, ys = warp_transform(
            "EPSG:4326", src.crs, sites.Longitude.tolist(), sites.Latitude.tolist()
        )
        rows = []
        # also build a local window for distance-to-pond
        pad = 20000
        win = from_bounds(
            min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad, transform=src.transform
        ).round_offsets().round_lengths()
        arr = src.read(1, window=win)
        transform = src.window_transform(win)
        pond = arr == CLASS_POND
        mang = arr == CLASS_MANGROVE
        dist_pond = ndimage.distance_transform_edt(~pond) * abs(src.res[0])
        dist_mang = ndimage.distance_transform_edt(~mang) * abs(src.res[0])

        for (_, site), x, y in zip(sites.iterrows(), xs, ys):
            col, row = ~transform * (x, y)
            r, c = int(row), int(col)
            if not (0 <= r < arr.shape[0] and 0 <= c < arr.shape[1]):
                rows.append(
                    {
                        "ID": site.ID,
                        "Group": site.Group,
                        "Longitude": site.Longitude,
                        "Latitude": site.Latitude,
                        "clark_class": None,
                        "clark_label": "out_of_raster",
                        "dist_to_clark_pond_m": None,
                        "dist_to_clark_mangrove_m": None,
                        "clark_maps_as_mangrove": False,
                        "clark_maps_as_pond": False,
                    }
                )
                continue
            cls = int(arr[r, c])
            rows.append(
                {
                    "ID": site.ID,
                    "Group": site.Group,
                    "Longitude": site.Longitude,
                    "Latitude": site.Latitude,
                    "clark_class": cls,
                    "clark_label": class_names.get(cls, str(cls)),
                    "dist_to_clark_pond_m": float(dist_pond[r, c]),
                    "dist_to_clark_mangrove_m": float(dist_mang[r, c]),
                    "clark_maps_as_mangrove": cls == CLASS_MANGROVE,
                    "clark_maps_as_pond": cls == CLASS_POND,
                }
            )

    df = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "chakaria_clark_field_site_validation.csv", index=False)

    # summary plot
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="white")
    summary = (
        df.groupby(["Group", "clark_label"]).size().unstack(fill_value=0)
        if len(df)
        else pd.DataFrame()
    )
    if not summary.empty:
        summary.plot(kind="bar", stacked=True, ax=ax, colormap="Set2")
    ax.set_ylabel("Field sites")
    ax.set_title("Chakaria field sites vs Clark 2022 class at GPS point")
    ax.legend(title="Clark class", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "chakaria_clark_field_site_validation.png", dpi=150)
    plt.close(fig)

    # native-resolution remnant map for Chakaria AOI
    with rasterio.open(tif) as src:
        xs, ys = warp_transform("EPSG:4326", src.crs, [91.95, 92.08], [21.45, 21.72])
        win = from_bounds(
            min(xs), min(ys), max(xs), max(ys), transform=src.transform
        ).round_offsets().round_lengths()
        arr = src.read(1, window=win)
        px = abs(src.res[0])
    mang = arr == CLASS_MANGROVE
    pond = arr == CLASS_POND
    rem, near, stats = map_remnant_patches(mang, pond, px)
    stats["aoi"] = "Chakaria"
    pd.DataFrame([stats]).to_csv(out_dir / "chakaria_remnant_v3_stats.csv", index=False)

    with rasterio.open(tif) as src:
        xs_b, ys_b = warp_transform("EPSG:4326", src.crs, [91.95, 92.08], [21.45, 21.72])
        aoi_win = from_bounds(
            min(xs_b), min(ys_b), max(xs_b), max(ys_b), transform=src.transform
        ).round_offsets().round_lengths()
        aoi_transform = src.window_transform(aoi_win)
        xs, ys = warp_transform(
            "EPSG:4326", src.crs, sites.Longitude.tolist(), sites.Latitude.tolist()
        )

    fig, axes = plt.subplots(1, 2, figsize=(12, 6), facecolor="white")
    rgb = np.full((*arr.shape, 3), 0.93)
    rgb[pond] = (0.12, 0.40, 0.75)
    rgb[mang] = (0.15, 0.55, 0.22)
    rgb[rem] = (0.85, 0.10, 0.10)
    axes[0].imshow(rgb, origin="upper", interpolation="nearest")
    axes[0].set_title("Chakaria Clark classes + v3 remnant")
    colors = {"RMSP": "red", "PMSP": "orange", "PMWSP": "purple"}
    for (_, site), x, y in zip(sites.iterrows(), xs, ys):
        col, row = ~aoi_transform * (x, y)
        axes[0].scatter(
            col,
            row,
            s=28,
            c=colors.get(site.Group, "black"),
            edgecolors="white",
            linewidths=0.4,
            zorder=5,
            label=site.Group,
        )
    # unique legend entries
    handles, labels = axes[0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    axes[0].legend(by_label.values(), by_label.keys(), loc="lower left", fontsize=8)
    axes[0].set_xticks([])
    axes[0].set_yticks([])

    rgb2 = np.full((*arr.shape, 3), 0.93)
    rgb2[pond] = (0.70, 0.80, 0.90)
    rgb2[near] = (0.80, 0.15, 0.10)
    rgb2[rem] = (0.95, 0.55, 0.10)
    axes[1].imshow(rgb2, origin="upper", interpolation="nearest")
    axes[1].set_title(
        f"v3 remnant patches: {stats['n_remnant_patches']} ({stats['remnant_mangrove_ha']:.1f} ha)"
    )
    axes[1].set_xticks([])
    axes[1].set_yticks([])
    fig.suptitle(
        "Chakaria — Clark under-maps RMSP (sites often 'Other', far from Clark ponds)",
        fontsize=11,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(out_dir / "chakaria_remnant_v3_map.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clark-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--max-dim", type=int, default=12000)
    parser.add_argument("--target-px", type=float, default=90.0)
    parser.add_argument("--skip-countries", action="store_true", help="Only run Chakaria validation")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    print("Validating Chakaria field sites against Clark…")
    val = validate_chakaria_sites(args.clark_dir, args.year, OUT)
    if len(val):
        rmsp = val[val.Group == "RMSP"]
        print(
            f"  RMSP sites mapped as mangrove by Clark: "
            f"{rmsp.clark_maps_as_mangrove.sum()}/{len(rmsp)}"
        )
        print(
            f"  RMSP median distance to Clark pond: "
            f"{rmsp.dist_to_clark_pond_m.median():.0f} m"
        )

    if args.skip_countries:
        return

    by = list_landcover(args.clark_dir)
    if not by:
        raise SystemExit("No Clark landcover GeoTIFFs found")

    rows = []
    for country in sorted(by):
        tif = pick_year(by[country], args.year)
        years = [int(x) for x in re.findall(r"(?:19|20)\d{2}", tif.name)]
        year = max(years) if years else args.year
        print(f"{country:15s} {tif.name}")

        with rasterio.open(tif) as src:
            _, peek_px, _, _ = choose_overview_factor(src, args.max_dim, args.target_px)

        if peek_px > 120:
            print(f"  overview would be {peek_px:.0f} m → pond-region tiling")
            mangrove, pond, rem, ponds_near, px, stats = map_remnant_tiled(
                tif,
                target_px_m=min(90.0, args.target_px),
                display_max_dim=args.max_dim,
            )
            print(
                f"  display shape={mangrove.shape} px={px:.1f} m  "
                f"fine={stats.get('fine_pixel_m', px):.1f} m"
            )
        else:
            arr, px = read_overview(tif, max_dim=args.max_dim, target_px_m=args.target_px)
            print(f"  read shape={arr.shape} px={px:.1f} m")
            mangrove = arr == CLASS_MANGROVE
            pond = arr == CLASS_POND
            rem, ponds_near, stats = map_remnant_patches(mangrove, pond, px)

        stats.update({"country": country, "year": year, "source_tif": str(tif), "pixel_m": px})
        rows.append(stats)
        out_png = OUT / f"{country}_{year}_remnant_mangrove_map.png"
        make_country_map(country, year, mangrove, pond, rem, ponds_near, stats, out_png, px)
        print(
            f"  patches={stats['n_remnant_patches']}  "
            f"remnant={stats['remnant_mangrove_ha']:.1f} ha  "
            f"median_pond_frac={stats['median_remnant_pond_frac']:.2f}"
        )

    df = pd.DataFrame(rows).sort_values("remnant_mangrove_ha", ascending=False)
    df.to_csv(OUT / "country_remnant_map_index.csv", index=False)
    make_atlas(df.to_dict("records"), OUT, OUT / "atlas_remnant_mangrove_all_countries.png")

    # compare to v2 if present
    v2 = ROOT / "outputs" / "country_maps_v2" / "country_remnant_map_index.csv"
    if v2.exists():
        old = pd.read_csv(v2)[["country", "remnant_mangrove_ha", "n_remnant_patches"]].rename(
            columns={
                "remnant_mangrove_ha": "remnant_ha_v2",
                "n_remnant_patches": "n_patches_v2",
            }
        )
        cmp = df[["country", "remnant_mangrove_ha", "n_remnant_patches"]].merge(old, on="country")
        cmp["reduction_pct"] = 100 * (1 - cmp["remnant_mangrove_ha"] / cmp["remnant_ha_v2"].replace(0, np.nan))
        cmp.to_csv(OUT / "v2_vs_v3_remnant_comparison.csv", index=False)

    print("\n=== v3 strict remnant summary ===")
    print(
        df[
            [
                "country",
                "n_remnant_patches",
                "remnant_mangrove_ha",
                "median_remnant_pond_frac",
                "pond_with_nearby_mangrove_ha",
            ]
        ].to_string(index=False)
    )
    print(f"\nMaps → {OUT}")


if __name__ == "__main__":
    main()
