# Remnant mangrove within shrimp ponds (Clark CGA collection)

Uses **your already-downloaded** Clark / Moore aquaculture–coastal landcover GeoTIFFs.

**No downloads.** Point the script at the folder you already have.

## Your data

```text
C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond
```

Clark legend (15 m): `1` Mangrove · `2` Coastal Wetland · `3` Pond Aquaculture · `4` Water · `5` Other · `6` Missing

Clark countries (17): Bangladesh, Brazil, Cambodia, China, Ecuador, El Salvador, Honduras, India, Indonesia, Malaysia, Mexico, Myanmar, Nicaragua, Philippines, Sri Lanka, Thailand, Vietnam.

## Remnant definition

Clark classes do not overlap on one pixel, so remnant is **mangrove embedded in the aquaculture landscape**:

- mangrove with ≥30% Pond Aquaculture in a ~315 m neighborhood, and/or  
- mangrove adjacent to ponds (15–45 m)

## Run (local only)

```bash
cd scripts/remnant_mangrove_shrimppond
pip install -r requirements.txt

# see what Clark TIFFs you already have
python map_clark_remnant.py --list-only \
  --clark-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"

# Chakaria remnant mangrove in aquaculture
python map_clark_remnant.py \
  --clark-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond" \
  --country bangladesh --year 2022 --aoi chakaria

# or pass the exact TIFF
python map_clark_remnant.py \
  --tif "C:/Users/.../shrimppond/Bangladesh_Landcover_2022_v1exp.tif" \
  --aoi chakaria
```

Outputs → `outputs/*_remnant_map.png`, `*_remnant.tif`, `*_remnant_stats.csv`

## GEE (optional)

`remnant_mangrove_shrimppond.js` — only if you upload **your** Clark TIFF as an EE asset (`POND_ASSET` / landcover asset). It does not fetch Clark from the web.
