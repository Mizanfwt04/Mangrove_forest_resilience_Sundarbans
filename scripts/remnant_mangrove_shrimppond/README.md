# Your Clark zips (local)

Point `--clark-dir` at:

```text
C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond
```

Expected zips in that folder (15 you listed):

| Zip |
|-----|
| Bangladesh_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip |
| Cambodia_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip |
| china_landcover_change_maps_1999_2014_2018_2020_2022.zip |
| ecuador_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip |
| elsalvador_landcover_change_maps_1999_2014_2018_2020_2022.zip |
| honduras_landcover_change_maps_1999_2014_2018_2020_2022.zip |
| india_landcover_change_maps_1999_2014_2018_2020_2022.zip |
| indonesia_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip |
| Malaysia_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip |
| mexico_landcover_change_maps_1999_2014_2018_2020_2022.zip |
| myanmar_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip |
| Philippines_Change_Persistence_Maps_1999_to_2022.zip |
| SriLanka_Landcover_Change_Maps_1999_2014_2018_2020_2022.zip |
| thailand_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip |
| vietnam_landcover_change_maps_1999_2014_2018_2020_2022_2024.zip |

Not in your list (Clark has 17 total): **Brazil**, **Nicaragua**.

## Run on your PC (no download)

```powershell
cd <repo>\scripts\remnant_mangrove_shrimppond
pip install -r requirements.txt

$dir = "C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond"

# confirm zips
python map_clark_remnant.py --list-only --clark-dir $dir

# all countries → remnant mangrove in aquaculture summary
python map_clark_remnant.py --all-countries --clark-dir $dir --year 2022

# Chakaria only
python map_clark_remnant.py --country bangladesh --year 2022 --aoi chakaria --clark-dir $dir
```

Zips are extracted once to `$dir\_extracted\`. Output CSV:

`outputs/clark_countries_remnant_mangrove_in_aquaculture.csv`

## Remnant definition (Clark)

`1` Mangrove · `3` Pond Aquaculture (mutually exclusive pixels)

Remnant = mangrove in a pond-dominated neighborhood (≥30% ponds in ~315 m) and/or mangrove adjacent to ponds.
