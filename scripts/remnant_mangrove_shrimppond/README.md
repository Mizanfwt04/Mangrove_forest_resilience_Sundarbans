# Remnant mangrove in shrimp-pond areas (Clark CGA)

Maps **mangrove patches enclosed by shrimp ponds** using Clark / Moore coastal landcover (15 m).

## Important finding (Chakaria field check)

Clark **does not map remnant mangrove at your RMSP sites**:

| Group | Clark class at GPS | Median distance to Clark pond |
|-------|--------------------|-------------------------------|
| RMSP (n=10) | **all Other (5)** — never Mangrove | **≈ 5.2 km** |
| PMSP (n=10) | all Mangrove | — |
| PMWSP (n=10) | all Mangrove | — |

So national “remnant” layers can only recover what Clark labelled as mangrove inside pond landscapes. True field remnants that Clark called **Other** are missed. See:

- `outputs/country_maps_v3/chakaria_clark_field_site_validation.csv`
- `outputs/country_maps_v3/chakaria_remnant_v3_map.png`

## Remnant definition (v3 — current)

Clark classes are mutually exclusive (`1` Mangrove · `3` Pond), so remnant ≠ pixel overlap.

**Remnant** = connected mangrove **patch** with high pond enclosure in a ~150 m ring:

| Rule | Max patch area | Min pond fraction in ring |
|------|----------------|---------------------------|
| Small scraps | ≤ 40 ha | ≥ 45% |
| Strongly enclosed | ≤ 120 ha | ≥ 65% |

This drops Sundarbans / large-forest **edge** that v1 painted as remnant (v1 used “any mangrove ≤45 m from ponds”).

| Version | Idea | Problem |
|---------|------|---------|
| v1 | Adjacent to ponds | Forest fringe counted as remnant |
| v2 | Patches, pond ring ≥30% | Still too loose |
| **v3** | Patches, pond ring ≥45% / 65% | Current |

## Results (Clark 2022, v3)

All **17** Clark countries have some pond-enclosed mangrove patches. Largest remnant areas: Indonesia, Vietnam, Thailand, Ecuador, Philippines.

Maps: `outputs/country_maps_v3/`

- `<Country>_2022_remnant_mangrove_map.png` — national + ponds-near-remnant + ~25 km hotspot
- `atlas_remnant_mangrove_all_countries.png`
- `country_remnant_map_index.csv`
- `v2_vs_v3_remnant_comparison.csv`

## Run

```bash
DIR=../outputs/agb_stability/shrimppond   # or your OneDrive shrimppond folder

python make_country_remnant_maps_v3.py --clark-dir "$DIR" --year 2022
```

Windows:

```powershell
$dir = "C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond"
python make_country_remnant_maps_v3.py --clark-dir $dir --year 2022
```

Older scripts (`make_country_remnant_maps.py`, `*_v2.py`) kept for comparison only.

## Clark zip folder

`scripts/outputs/agb_stability/shrimppond/` (gitignored; too large for GitHub).  
Same path on your PC under Desktop `scripts\outputs\agb_stability\shrimppond`.

Fetch missing zips only when needed:

```bash
python fetch_missing_clark.py --out-dir ../outputs/agb_stability/shrimppond
```
