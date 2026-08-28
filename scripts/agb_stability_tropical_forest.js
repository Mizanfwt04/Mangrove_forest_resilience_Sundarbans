/**
 * AGB Temporal Stability — Global Tropical Forest
 *
 * Metric: stability = mean(AGB) / SD(AGB)  (higher = more temporally stable)
 *
 * Masks (all must pass):
 *   1. WWF tropical forest biomes
 *   2. ESA WorldCover 2021 — tree cover or mangroves, exclude permanent water
 *   3. Hansen GFC — ≥30% tree cover in 2000, no canopy loss through 2023
 *   4. JRC Global Surface Water — <10% historical water occurrence
 */

// =============================================================================
// CONFIG
// =============================================================================

var START_DATE = '2000-01-01';
var END_DATE   = '2025-12-31';

var TREE_COVER_MIN_PCT = 30;       // Hansen treecover2000 threshold
var WATER_OCCURRENCE_MAX = 10;     // JRC occurrence % above which pixel is excluded
var MIN_MEAN_AGB = 10;             // Mg/ha; drop scrub/grass misclassified as forest

var MAP_CENTER = [-62, -4];
var MAP_ZOOM   = 4;

// =============================================================================
// CTREES AGB — load, rescale, temporal stack
// =============================================================================

var collection = ee.ImageCollection('projects/sat-io/open-datasets/CTREES-GLOBAL-AGB-100M');

function rescaleAGB(image) {
  var scaled = image.multiply(image.getNumber('agb_scale_factor'));
  return scaled.updateMask(scaled.gt(0)).copyProperties(image, image.propertyNames());
}

var filtered = collection
  .filterDate(START_DATE, END_DATE)
  .map(rescaleAGB);

var meanAGB = filtered.select('agb').mean().rename('agb_mean');
var sdAGB   = filtered.select('agb').reduce(ee.Reducer.stdDev()).rename('agb_sd');

// Stability = mean / SD  (inverse coefficient of variation; higher = more stable)
var stability = meanAGB
  .divide(sdAGB)
  .rename('agb_stability')
  .updateMask(sdAGB.gt(0));  // SD = 0 → undefined; treat as perfectly stable if needed

// =============================================================================
// MASK 1 — WWF tropical forest biomes
// =============================================================================

var ecoregions = ee.FeatureCollection('RESOLVE/ECOREGIONS/2017');

var tropicalForests = ecoregions.filter(ee.Filter.inList('BIOME_NAME', [
  'Tropical & Subtropical Moist Broadleaf Forests',
  'Tropical & Subtropical Dry Broadleaf Forests',
  'Tropical & Subtropical Coniferous Forests'
]));

var tropicalBiomeMask = ee.Image().paint(tropicalForests, 1).selfMask();

// =============================================================================
// MASK 2 — ESA WorldCover 2021: forest classes, exclude water
// =============================================================================

var worldCover = ee.Image('ESA/WorldCover/v200').select('Map');

// 10 = Tree cover, 95 = Mangroves
var wcForest = worldCover.eq(10).or(worldCover.eq(95));
var wcNotWater = worldCover.neq(80);  // 80 = Permanent water bodies

var worldCoverMask = wcForest.and(wcNotWater);

// =============================================================================
// MASK 3 — Hansen GFC: persistent forest (no loss 2000–2023)
// =============================================================================

var hansen = ee.Image('UMD/hansen/global_forest_change_2023_v1_11');
var hansenYear = 2023;  // last loss year in this Hansen version

var forest2000 = hansen.select('treecover2000').gte(TREE_COVER_MIN_PCT);
var noLoss = hansen.select('lossyear').eq(0);
var stableForestMask = forest2000.and(noLoss);

// =============================================================================
// MASK 4 — JRC Global Surface Water: exclude frequently inundated pixels
// =============================================================================

var jrcWater = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence');
var notWaterMask = jrcWater.lt(WATER_OCCURRENCE_MAX);

// =============================================================================
// COMBINED ANALYSIS MASK
// =============================================================================

var analysisMask = tropicalBiomeMask
  .and(worldCoverMask)
  .and(stableForestMask)
  .and(notWaterMask)
  .and(meanAGB.gte(MIN_MEAN_AGB));

var stabilityMasked = stability.updateMask(analysisMask);
var meanAGBMasked   = meanAGB.updateMask(analysisMask);
var sdAGBMasked     = sdAGB.updateMask(analysisMask);

// =============================================================================
// VISUALIZATION
// =============================================================================

// Mean/SD: low = variable biomass, high = stable biomass
// Use percentiles over tropical masked area for sensible stretch
var stabilityStats = stabilityMasked.reduceRegion({
  reducer: ee.Reducer.percentile([2, 98]),
  geometry: tropicalForests.geometry(),
  scale: 1000,
  maxPixels: 1e13,
  bestEffort: true
});

var stabilityVis = {
  min: stabilityStats.get('agb_stability_p2'),
  max: stabilityStats.get('agb_stability_p98'),
  palette: [
    '#253494',  // unstable (low mean/SD)
    '#2c7fb8',
    '#41b6c4',
    '#a1dab4',
    '#ffffcc'   // stable (high mean/SD)
  ]
};

var meanVis = {min: 0, max: 200, palette: ['#f7fcf5', '#00441b']};
var sdVis   = {min: 0, max: 50,  palette: ['#fff5f0', '#67000d']};

Map.setCenter(MAP_CENTER[0], MAP_CENTER[1], MAP_ZOOM);

Map.addLayer(
  stabilityMasked,
  stabilityVis,
  'AGB Stability (mean/SD) — stable tropical forest'
);

// Toggle off by default — useful for QA
Map.addLayer(meanAGBMasked, meanVis, 'Mean AGB', false);
Map.addLayer(sdAGBMasked, sdVis, 'SD AGB', false);
Map.addLayer(analysisMask.selfMask(), {palette: ['#2d6a4f']}, 'Analysis mask', false);

// =============================================================================
// OPTIONAL — Snazzy basemap
// =============================================================================

var snazzy = require('users/aazuspan/snazzy:styles');
snazzy.addStyle('https://snazzymaps.com/style/15/subtle-grayscale', 'Greyscale');

// =============================================================================
// OPTIONAL — Export (uncomment and set region)
// =============================================================================

/*
var exportRegion = ee.Geometry.Rectangle([-80, -25, -35, 15]);  // Amazon example

Export.image.toDrive({
  image: stabilityMasked.float(),
  description: 'AGB_stability_tropical_stable_forest',
  folder: 'GEE_exports',
  region: exportRegion,
  scale: 100,
  maxPixels: 1e13
});
*/

// =============================================================================
// OPTIONAL — Zonal summary by ecoregion
// =============================================================================

/*
var zonalStats = stabilityMasked.reduceRegions({
  collection: tropicalForests,
  reducer: ee.Reducer.mean().combine({
    reducer2: ee.Reducer.stdDev(),
    sharedInputs: true
  }),
  scale: 1000
});

print('Ecoregion stability stats', zonalStats.limit(10));
*/
