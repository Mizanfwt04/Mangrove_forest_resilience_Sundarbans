/**
 * Remnant mangrove within shrimp / aquaculture ponds
 *
 * Definition used here:
 *   remnant = current mangrove pixels that fall INSIDE an aquaculture-pond mask
 *   (optional: also mangroves within BUFFER_M of ponds = dike / edge remnants)
 *
 * Mangrove source (toggle):
 *   - GMW annual extent 2020 (10 m; preferred)
 *   - ESA WorldCover v200 class 95 (fallback)
 *
 * Pond source (choose ONE):
 *   A) Upload your local shrimp-pond raster/vector as an EE asset and set POND_ASSET
 *      Local Windows folder to export from:
 *      C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond
 *   B) Leave POND_ASSET empty to use a provisional proxy:
 *      ESA WorldCover permanent water (80) inside the GMW mangrove UNION
 *      (historical mangrove zone) — useful until pond polygons are uploaded
 *
 * Paste into https://code.earthengine.google.com/ and Run.
 */

// =============================================================================
// CONFIG
// =============================================================================

var REGION = 'chakaria'; // 'chakaria' | 'sundarbans' | 'custom'
var BUFFER_M = 30;       // edge / dike remnant search distance
var MAX_PATCH_HA = 50;   // optional: keep only small mangrove patches as "remnant"

// Optional: your uploaded pond mask (Image 1=pond or FeatureCollection polygons)
var POND_ASSET = '';     // e.g. 'users/YOUR_USER/shrimppond_mask'

var REGIONS = {
  chakaria: ee.Geometry.Rectangle([91.95, 21.45, 92.08, 21.72]),
  sundarbans: ee.Geometry.Rectangle([87.5, 20.5, 90.5, 23.0]),
  custom: ee.Geometry.Rectangle([91.95, 21.45, 92.08, 21.72])
};

var aoi = REGIONS[REGION];
Map.centerObject(aoi, 11);

// =============================================================================
// MANGROVE EXTENT
// =============================================================================

var gmw2020 = ee.ImageCollection(
  'projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020'
).mosaic().gt(0).selfMask().rename('mangrove');

var worldCover = ee.Image('ESA/WorldCover/v200').select('Map');
var wcMangrove = worldCover.eq(95).selfMask().rename('mangrove');

// Prefer GMW; fall back to WorldCover where GMW is empty
var mangrove = gmw2020.unmask(0).gt(0)
  .or(wcMangrove.unmask(0).gt(0))
  .selfMask()
  .rename('mangrove');

// Historical mangrove zone (any year in GMW v3 union) — for pond proxy
var gmwUnion = ee.Image(
  'projects/earthengine-legacy/assets/projects/sat-io/open-datasets/GMW/union/gmw_v3_mng_union'
).gt(0);

// =============================================================================
// AQUACULTURE / SHRIMP POND MASK
// =============================================================================

var ponds;
if (POND_ASSET && POND_ASSET.length > 0) {
  var asset = ee.Algorithms.If(
    ee.String(POND_ASSET).match('.*').length(),
    POND_ASSET,
    POND_ASSET
  );
  // Try as Image first; if FeatureCollection, paint it
  ponds = ee.Image(POND_ASSET).rename('pond').gt(0);
  // If asset is a FeatureCollection, comment the line above and use:
  // ponds = ee.Image().byte().paint(ee.FeatureCollection(POND_ASSET), 1).rename('pond');
} else {
  // Provisional proxy: permanent water inside historical mangrove extent
  ponds = worldCover.eq(80).and(gmwUnion).rename('pond').selfMask();
}

ponds = ponds.clip(aoi).selfMask();
mangrove = mangrove.clip(aoi);

// =============================================================================
// REMNANT = mangrove ∩ ponds  (+ optional near-pond fringe)
// =============================================================================

var remnantInside = mangrove.gt(0).and(ponds.gt(0)).selfMask().rename('remnant_inside');

var pondBuffer = ponds.focalMax({
  radius: BUFFER_M,
  units: 'meters',
  kernelType: 'circle'
});
var remnantEdge = mangrove.gt(0)
  .and(pondBuffer.gt(0))
  .and(ponds.unmask(0).eq(0))
  .selfMask()
  .rename('remnant_edge');

var remnantAny = remnantInside.unmask(0).gt(0)
  .or(remnantEdge.unmask(0).gt(0))
  .selfMask()
  .rename('remnant_any');

// Optional patch-size filter (connected pixel count → hectares at 10 m)
var pixelAreaHa = ee.Image.pixelArea().divide(10000);
var patchId = remnantAny.connectedComponents({
  connectedness: ee.Kernel.plus(1),
  maxSize: 1024
}).select('labels');
var patchArea = pixelAreaHa.addBands(patchId).reduceConnectedComponents({
  reducer: ee.Reducer.sum(),
  labelBand: 'labels'
});
var remnantSmall = remnantAny.updateMask(patchArea.lte(MAX_PATCH_HA)).rename('remnant_small');

// =============================================================================
// MAP
// =============================================================================

Map.addLayer(aoi, {color: '000000'}, 'AOI', false);
Map.addLayer(ponds, {palette: ['1f78b4']}, 'Aquaculture / shrimp ponds');
Map.addLayer(mangrove, {palette: ['33a02c']}, 'Mangrove (GMW/WorldCover)');
Map.addLayer(remnantInside, {palette: ['e31a1c']}, 'Remnant mangrove INSIDE ponds');
Map.addLayer(remnantEdge, {palette: ['ff7f00']}, 'Mangrove within ' + BUFFER_M + ' m of ponds', false);
Map.addLayer(remnantSmall, {palette: ['6a3d9a']}, 'Small remnant patches (<=' + MAX_PATCH_HA + ' ha)', false);

// =============================================================================
// AREA SUMMARY
// =============================================================================

function areaHa(img, label) {
  var dict = pixelAreaHa.updateMask(img).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: aoi,
    scale: 10,
    maxPixels: 1e13,
    bestEffort: true
  });
  return ee.Feature(null, {
    class: label,
    area_ha: dict.get('area')
  });
}

var summary = ee.FeatureCollection([
  areaHa(ponds, 'pond'),
  areaHa(mangrove, 'mangrove'),
  areaHa(remnantInside, 'remnant_inside_pond'),
  areaHa(remnantEdge, 'mangrove_within_buffer'),
  areaHa(remnantSmall, 'remnant_small_patch')
]);
print('Area summary (ha)', summary);

// =============================================================================
// EXPORT
// =============================================================================

Export.image.toDrive({
  image: remnantInside.unmask(0).addBands(mangrove.unmask(0)).addBands(ponds.unmask(0)).byte(),
  description: 'remnant_mangrove_shrimppond_' + REGION,
  folder: 'GEE_exports',
  region: aoi,
  scale: 10,
  maxPixels: 1e13
});

Export.table.toDrive({
  collection: summary,
  description: 'remnant_mangrove_shrimppond_areas_' + REGION,
  folder: 'GEE_exports',
  fileFormat: 'CSV'
});
