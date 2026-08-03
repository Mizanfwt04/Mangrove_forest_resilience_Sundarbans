# Remnant mangrove within shrimp ponds

Goal: map **mangrove that remains inside aquaculture / shrimp-pond footprints** (remnant mangrove), starting from Chakaria and scalable to other coasts.

## Your local data folder

```text
C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond
```

This cloud environment cannot read that Windows path directly. On your PC, either:

1. Run the Python script with `--shrimppond-dir` pointing at that folder, or  
2. Upload pond GeoTIFF / shapefile to Earth Engine and set `POND_ASSET` in the `.js` script, or  
3. Copy pond layers into `scripts/remnant_mangrove_shrimppond/data/shrimppond/`.

## Remnant definition

```text
remnant_inside = mangrove ∩ shrimp_pond
edge_remnant   = mangrove within 30 m of ponds but outside the pond mask
```

Mangrove source: ESA WorldCover class **95** (Python) or GMW 2020 + WorldCover (GEE).  
Pond source: your local `shrimppond` exports when available; otherwise WorldCover water / uploaded assets.

## Quick start (Python)

```bash
cd scripts/remnant_mangrove_shrimppond
pip install -r requirements.txt

# Chakaria demo (Planetary Computer WorldCover; no EE auth)
python map_remnant_mangrove.py --aoi chakaria

# Use your local shrimp-pond exports
python map_remnant_mangrove.py --aoi chakaria \
  --shrimppond-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"

# Only inspect what files are in that folder
python map_remnant_mangrove.py --list-only \
  --shrimppond-dir "C:/Users/Md Mizanur Rahman/OneDrive/Desktop/scripts/outputs/agb_stability/shrimppond"
```

Outputs land in `outputs/`:

| File | Content |
|------|---------|
| `{aoi}_remnant_mangrove_shrimppond.tif` | bands: pond, mangrove, remnant |
| `{aoi}_remnant_mangrove_map.png` | RGB preview + RMSP/PMSP/PMWSP sites |
| `{aoi}_remnant_mangrove_stats.csv` | area summary (ha) |
| `{aoi}_sites_remnant_overlay.csv` | field sites vs mangrove/pond |

## Earth Engine (interactive)

Paste `remnant_mangrove_shrimppond.js` into the [Code Editor](https://code.earthengine.google.com/).

1. Set `REGION` to `chakaria` or `sundarbans`.  
2. Upload your shrimppond layer → set `POND_ASSET`.  
3. Run → inspect red remnant layer → start Drive exports.

## Chakaria pilot result (this repo)

Using WorldCover mangrove ∩ aquaculture landscape for the Chakaria bbox:

| Metric | ha |
|--------|----|
| Mangrove in AOI | 1102 |
| Aquaculture / pond mask | 15207 |
| **Remnant mangrove inside ponds** | **90** |
| Mangrove within 30 m of ponds | 65 |

Field design (same as Chakaria uGPP study):

| Group | Meaning |
|-------|---------|
| RMSP | Remanent mangrove in shrimp ponds |
| PMSP | Planted mangrove in shrimp ponds |
| PMWSP | Protected mangrove without shrimp ponds |

## How many countries?

Sample-window scan (WorldCover mangrove ∩ Wang et al. 2022 global landside aquaculture ponds) found remnant mangrove inside aquaculture in **29 countries** (lower bound; not a full national census):

Bangladesh, Benin, Brazil, Cambodia, Colombia, Costa Rica, Ecuador, El Salvador, Ghana, Guatemala, Guinea, Honduras, India, Indonesia, Kenya, Malaysia, Mexico, Mozambique, New Caledonia, Nicaragua, Panama, Peru, Philippines, Sri Lanka, Suriname, Tanzania, Thailand, Venezuela, Vietnam.

See `outputs/country_remnant_mangrove_sample.csv` and `data/aquaculture_pond_countries.csv` (79 countries with mapped aquaculture ponds).

## Relation to AGB stability exports

If `outputs/agb_stability/shrimppond` holds AGB stability GeoTIFFs clipped to ponds, pass that folder with `--shrimppond-dir`. Non-zero / valid pixels are treated as the pond analysis mask, then intersected with WorldCover mangroves to isolate remnant biomass pixels.

## Data credits

- ESA WorldCover v200  
- Global Mangrove Watch (GEE path in `.js`)  
- Wang et al. global landside aquaculture ponds (Zenodo 5643036) — used for country scan only  
