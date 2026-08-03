# Remnant mangrove in shrimp-pond areas (Clark CGA)

Maps **shrimp-pond landscapes where mangrove still exists as remnants**, using the Clark / Moore coastal landcover collection.

## Results (Clark ~2022)

**All 17 Clark countries** have remnant mangrove in shrimp-pond landscapes.

| | Area |
|--|------|
| Remnant mangrove (in/near ponds) | **≈ 515,000 ha** |
| Shrimp ponds within 45 m of mangrove | **≈ 620,000 ha** |

Largest pond–remnant interfaces: **Indonesia**, **Vietnam**, **Thailand**, **Ecuador**, **Philippines**.

| File | Content |
|------|---------|
| `outputs/clark_remnant_mangrove_in_shrimpponds.csv` | Country table |
| `outputs/clark_remnant_shrimppond_bar.png` | Bar chart |
| `outputs/country_previews/*_remnant_shrimppond.png` | Per-country maps |
| `outputs/chakaria_clark_remnant_shrimppond.png` | Chakaria close-up |

## What is mapped

Clark classes (15 m): `1` Mangrove · `3` Pond Aquaculture

- **Remnant mangrove** = mangrove with ≥30% ponds nearby (~315 m) **or** mangrove ≤45 m from ponds  
- **Ponds with remnant** = pond pixels ≤45 m from mangrove (pond–mangrove interface)

## Run

```bash
# data folder (this repo copy, or your OneDrive shrimppond folder)
DIR=../outputs/agb_stability/shrimppond

python map_remnant_in_shrimpponds.py --clark-dir "$DIR" --year 2022
```

Windows:

```powershell
$dir = "C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond"
python map_remnant_in_shrimpponds.py --clark-dir $dir --year 2022
```

## Clark zip folder

`scripts/outputs/agb_stability/shrimppond/` (all 17 country zips).  
Same path on your PC under Desktop `scripts\outputs\agb_stability\shrimppond`.
