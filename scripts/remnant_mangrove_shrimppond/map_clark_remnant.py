#!/usr/bin/env python3
"""
Remnant mangrove within shrimp ponds — Clark CGA collection (LOCAL ONLY).

Reads the Clark zip/GeoTIFF files you already downloaded under::

    C:\\Users\\Md Mizanur Rahman\\OneDrive\\Desktop\\scripts\\outputs\\agb_stability\\shrimppond

Does NOT download anything. Zips are unzipped once into ``<clark-dir>/_extracted/``.

Clark legend (15 m): 1 Mangrove · 2 Coastal Wetland · 3 Pond Aquaculture ·
4 Water · 5 Other · 6 Missing

Remnant (classes do not overlap on one pixel):
  mangrove with ≥30% Pond Aquaculture in a ~315 m window, and/or
  mangrove adjacent to ponds (15–45 m)

Examples
--------
python map_clark_remnant.py --list-only --clark-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"

python map_clark_remnant.py --all-countries --clark-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"

python map_clark_remnant.py --country bangladesh --year 2022 --aoi chakaria --clark-dir "C:/Users/.../shrimppond"
"""

from __future__ import annotations

import argparse
import os
import re
import zipfile
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

# Exact zip names you listed (plus any others already in the folder)
KNOWN_ZIPS = [
    "Bangladesh_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
    "brazil_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    "Cambodia_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
    "china_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    "ecuador_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
    "elsalvador_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    "honduras_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    "india_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    "indonesia_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
    "Malaysia_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
    "mexico_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    "myanmar_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
    "nicaragua_landcover_change_maps_1999_2014_2018_2020_2022.zip",
    "Philippines_Change_Persistence_Maps_1999_to_2022.zip",
    "SriLanka_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip",
    "thailand_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
    "vietnam_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip",
]

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

COUNTRY_FROM_ZIP = {
    "bangladesh": "Bangladesh",
    "cambodia": "Cambodia",
    "china": "China",
    "ecuador": "Ecuador",
    "elsalvador": "El Salvador",
    "el_salvador": "El Salvador",
    "honduras": "Honduras",
    "india": "India",
    "indonesia": "Indonesia",
    "malaysia": "Malaysia",
    "mexico": "Mexico",
    "myanmar": "Myanmar",
    "philippines": "Philippines",
    "srilanka": "Sri Lanka",
    "sri_lanka": "Sri Lanka",
    "thailand": "Thailand",
    "vietnam": "Vietnam",
    "brazil": "Brazil",
    "nicaragua": "Nicaragua",
}


def resolve_clark_dir(cli: str | None) -> Path | None:
    candidates: list[Path] = []
    if cli:
        candidates.append(Path(cli))
    env = os.environ.get("CLARK_DIR") or os.environ.get("SHRIMPPOND_DIR")
    if env:
        candidates.append(Path(env))
    candidates.extend(DEFAULT_CLARK_DIRS)
    for path in candidates:
        if path.exists():
            return path
    return None


def country_key_from_name(name: str) -> str:
    n = re.sub(r"[^a-z0-9]+", "", name.lower())
    for key in sorted(COUNTRY_FROM_ZIP, key=len, reverse=True):
        if key.replace("_", "") in n:
            return key.replace("_", "")
    return n


def display_country(name: str) -> str:
    key = country_key_from_name(name)
    return COUNTRY_FROM_ZIP.get(key, key.title())


def list_zips(folder: Path) -> list[Path]:
    zips = sorted(folder.glob("*.zip"))
    # Prefer known names first, then any other zip in folder
    known = {z.lower() for z in KNOWN_ZIPS}
    ordered = [p for p in zips if p.name.lower() in known or "landcover" in p.name.lower() or "philippines" in p.name.lower()]
    if not ordered:
        ordered = zips
    return ordered


def extract_zip(zip_path: Path, extract_root: Path) -> Path:
    """Unzip once into extract_root/<stem>/ ; skip if landcover tifs already present."""
    dest = extract_root / zip_path.stem
    dest.mkdir(parents=True, exist_ok=True)
    existing = list(dest.rglob("*Landcover*.tif")) + list(dest.rglob("*landcover*.tif"))
    # Philippines package may use different naming
    if not existing:
        existing = [p for p in dest.rglob("*.tif") if "landcover" in p.name.lower() or "persistence" not in p.name.lower()]
        existing = [p for p in existing if not p.name.lower().endswith(".tif.ovr") and ".ovr" not in p.name]
    if existing:
        return dest
    print(f"Extracting {zip_path.name} → {dest}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)
    return dest


def find_landcover_tifs(folder: Path) -> list[Path]:
    tifs: list[Path] = []
    for pat in ("*.tif", "*.tiff", "*.TIF", "*.TIFF"):
        tifs.extend(folder.rglob(pat))
    tifs = [p for p in tifs if ".ovr" not in p.name.lower()]
    land = [p for p in tifs if re.search(r"landcover", p.name, re.I)]
    if land:
        return sorted(land)
    # Philippines change/persistence package may only have persistence maps —
    # still allow any non-persistence landcover-like raster if present
    return sorted([p for p in tifs if "persistence" not in p.name.lower()])


def pick_year_tif(tifs: list[Path], year: int | None) -> Path:
    if not tifs:
        raise FileNotFoundError("No landcover GeoTIFF found")
    if year is not None:
        ymatch = [p for p in tifs if str(year) in p.name]
        if ymatch:
            return sorted(ymatch, key=lambda p: p.name)[-1]
    # latest year token in filename
    def year_key(p: Path) -> int:
        years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", p.name)]
        return max(years) if years else 0

    return sorted(tifs, key=year_key)[-1]


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
    country: str,
    write_maps: bool,
) -> dict:
    with rasterio.open(tif_path) as src:
        if aoi:
            bbox = wgs_bbox_to_raster(AOIS_WGS84[aoi], src.crs)
            window = from_bounds(*bbox, transform=src.transform)
            arr = src.read(1, window=window)
            transform = src.window_transform(window)
            label = f"{country}_{aoi}_{tif_path.stem}"
        else:
            arr = src.read(1)
            transform = src.transform
            label = f"{country}_{tif_path.stem}"
            window = None

        stats, mangrove, pond, rem_matrix, rem_adj = remnant_masks(arr, matrix_pct=matrix_pct)
        years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", tif_path.name)]
        stats.update(
            {
                "country": country,
                "year": max(years) if years else None,
                "source_tif": str(tif_path),
                "aoi": aoi or "national",
                "label": label,
            }
        )
        print(
            f"{country:15s} year={stats['year']}  "
            f"mangrove={stats['mangrove_ha']:.1f} ha  "
            f"pond={stats['pond_aquaculture_ha']:.1f} ha  "
            f"remnant_matrix={stats['remnant_in_pond_matrix_ha']:.1f} ha  "
            f"adj45={stats['remnant_adj_pond_45m_ha']:.1f} ha  "
            f"YES={stats['has_remnant_in_aquaculture']}"
        )

        if write_maps:
            OUT.mkdir(parents=True, exist_ok=True)
            fig, ax = plt.subplots(figsize=(8, 8))
            rgb = np.zeros((*arr.shape, 3), dtype=float)
            rgb[..., 2] = pond * 0.7
            rgb[..., 1] = mangrove * 0.85
            rgb[..., 0] = rem_matrix.astype(float)
            edge = rem_adj & ~rem_matrix
            rgb[..., 0] = np.maximum(rgb[..., 0], edge.astype(float))
            rgb[..., 1] = np.maximum(rgb[..., 1], edge.astype(float) * 0.35)
            ax.imshow(rgb, origin="upper")
            ax.set_title(f"{country}: remnant mangrove in aquaculture\npond=blue mangrove=green remnant=red")
            ax.set_xticks([])
            ax.set_yticks([])
            map_path = OUT / f"{label}_remnant_map.png"
            fig.savefig(map_path, dpi=160, bbox_inches="tight")
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
        return stats


def prepare_country_dirs(clark_dir: Path) -> dict[str, Path]:
    """Map country display name → folder with extracted (or already loose) TIFFs."""
    extract_root = clark_dir / "_extracted"
    extract_root.mkdir(exist_ok=True)
    country_dirs: dict[str, Path] = {}

    for zip_path in list_zips(clark_dir):
        dest = extract_zip(zip_path, extract_root)
        country_dirs[display_country(zip_path.stem)] = dest

    # Also accept already-unzipped country folders / loose tifs in clark_dir
    loose = find_landcover_tifs(clark_dir)
    if loose:
        # group by country key in filename
        for tif in loose:
            if "_extracted" in tif.parts:
                continue
            cname = display_country(tif.name)
            country_dirs.setdefault(cname, tif.parent)

    return country_dirs


def run_all(clark_dir: Path, year: int | None, matrix_pct: float, write_maps: bool) -> pd.DataFrame:
    country_dirs = prepare_country_dirs(clark_dir)
    if not country_dirs:
        raise SystemExit(f"No Clark zips/TIFFs found in {clark_dir}")

    rows = []
    for country, folder in sorted(country_dirs.items()):
        tifs = find_landcover_tifs(folder)
        if not tifs:
            print(f"{country:15s} SKIP — no landcover GeoTIFF after extract")
            rows.append(
                {
                    "country": country,
                    "year": None,
                    "has_remnant_in_aquaculture": None,
                    "note": "no_landcover_tif",
                    "source_tif": None,
                }
            )
            continue
        try:
            tif = pick_year_tif(tifs, year)
            rows.append(
                analyze_tif(
                    tif_path=tif,
                    aoi=None,
                    matrix_pct=matrix_pct,
                    country=country,
                    write_maps=write_maps,
                )
            )
        except Exception as exc:  # noqa: BLE001 — keep batch running
            print(f"{country:15s} ERROR {exc}")
            rows.append(
                {
                    "country": country,
                    "has_remnant_in_aquaculture": None,
                    "note": str(exc),
                    "source_tif": None,
                }
            )

    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    out_csv = OUT / "clark_countries_remnant_mangrove_in_aquaculture.csv"
    df.to_csv(out_csv, index=False)
    yes = df[df["has_remnant_in_aquaculture"] == True]  # noqa: E712
    print(f"\nCountries with remnant mangrove in aquaculture: {len(yes)} / {len(df)}")
    print(yes["country"].tolist() if len(yes) else [])
    print(f"Wrote {out_csv}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clark-dir",
        default=None,
        help="Folder with your Clark zips (default: Desktop .../agb_stability/shrimppond)",
    )
    parser.add_argument("--country", default=None, help="e.g. bangladesh")
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--tif", default=None, help="Exact GeoTIFF path")
    parser.add_argument("--aoi", choices=sorted(AOIS_WGS84), default=None)
    parser.add_argument("--matrix-pct", type=float, default=0.30)
    parser.add_argument("--all-countries", action="store_true", help="Process every Clark zip in the folder")
    parser.add_argument("--maps", action="store_true", help="Write PNG/GeoTIFF maps (heavier)")
    parser.add_argument("--list-only", action="store_true")
    args = parser.parse_args()

    if args.tif:
        tif_path = Path(args.tif)
        if not tif_path.exists():
            raise SystemExit(f"TIFF not found: {tif_path}")
        stats = analyze_tif(
            tif_path,
            args.aoi,
            args.matrix_pct,
            display_country(tif_path.name),
            write_maps=True,
        )
        OUT.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([stats]).to_csv(OUT / f"{stats['label']}_remnant_stats.csv", index=False)
        return

    clark_dir = resolve_clark_dir(args.clark_dir)
    if clark_dir is None:
        raise SystemExit(
            "Clark folder not found. Pass your local path, e.g.\n"
            '  --clark-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"'
        )

    print(f"Clark dir: {clark_dir}")
    zips = list_zips(clark_dir)
    tifs = find_landcover_tifs(clark_dir)
    print(f"Zips: {len(zips)}")
    for z in zips:
        print(f"  ZIP  {z.name}")
    print(f"Loose landcover TIFFs: {len(tifs)}")
    for t in tifs[:20]:
        print(f"  TIF  {t.name}")

    if args.list_only:
        missing = [n for n in KNOWN_ZIPS if not (clark_dir / n).exists()]
        # case-insensitive presence
        present = {p.name.lower() for p in clark_dir.glob("*.zip")}
        missing = [n for n in KNOWN_ZIPS if n.lower() not in present]
        if missing:
            print("Listed zips not found in folder:")
            for n in missing:
                print(f"  MISSING {n}")
        else:
            print("All 15 listed Clark zips are present.")
        return

    if args.all_countries:
        run_all(clark_dir, args.year, args.matrix_pct, write_maps=args.maps)
        return

    # Single-country mode
    country_dirs = prepare_country_dirs(clark_dir)
    if args.country:
        key = args.country.lower().replace(" ", "").replace("_", "")
        match = None
        for cname, folder in country_dirs.items():
            if key in cname.lower().replace(" ", ""):
                match = (cname, folder)
                break
        if match is None:
            raise SystemExit(f"Country '{args.country}' not found in {list(country_dirs)}")
        cname, folder = match
        tif = pick_year_tif(find_landcover_tifs(folder), args.year)
        stats = analyze_tif(tif, args.aoi, args.matrix_pct, cname, write_maps=True)
        OUT.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([stats]).to_csv(OUT / f"{stats['label']}_remnant_stats.csv", index=False)
        return

    raise SystemExit("Pass --all-countries, or --country NAME, or --tif PATH (see --help).")


if __name__ == "__main__":
    main()
