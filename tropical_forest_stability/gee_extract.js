/**
 * Google Earth Engine script: tropical moist forest carbon stability sampling
 *
 * Paste into https://code.earthengine.google.com/
 * Exports ~5000 candidate points to Google Drive as CSV.
 * Then run analysis.py in Python on the downloaded file.
 */

var BIOME = 'Tropical & Subtropical Moist Broadleaf Forests';
var START_YEAR = 2000;
var END_YEAR = 2025;
var N_POINTS = 5000;
var SEED = 42;
var MIN_AGB = 50;

// --- Region ---
var ecoregions = ee.FeatureCollection('RESOLVE/ECOREGIONS/2017');
var region = ecoregions.filter(ee.Filter.eq('BIOME_NAME', BIOME)).geometry().dissolve(1000);

// --- CTrees AGB stability ---
function rescaleAGB(img) {
  var agb = img.select('agb').multiply(img.getNumber('agb_scale_factor')).rename('agb');
  return agb.updateMask(agb.gt(0));
}

var agbCol = ee.ImageCollection('projects/sat-io/open-datasets/CTREES-GLOBAL-AGB-100M')
  .filter(ee.Filter.calendarRange(START_YEAR, END_YEAR, 'year'))
  .map(rescaleAGB);

var agbMean = agbCol.mean().rename('agb_mean');
var agbStd = agbCol.reduce(ee.Reducer.stdDev()).rename('agb_std');
var stability = agbMean.divide(agbStd).rename('stability_mu_sigma');
var agbCv = agbStd.divide(agbMean).rename('agb_cv');

// --- TerraClimate compound variables ---
var tc = ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE')
  .filter(ee.Filter.calendarRange(START_YEAR, END_YEAR, 'year'));

var vpd = tc.select('vpd').map(function(i) { return i.multiply(0.01); });
var soil = tc.select('soil');
var def = tc.select('def').map(function(i) { return i.multiply(0.1); });
var pdsi = tc.select('pdsi').map(function(i) { return i.multiply(0.01); });
var pr = tc.select('pr');

var vpdMean = vpd.mean().rename('vpd_mean');
var vpdP95 = vpd.reduce(ee.Reducer.percentile([95])).rename('vpd_p95');
var soilMin = soil.min().rename('soil_min');
var soilMean = soil.mean().rename('soil_mean');
var soilDeficit = ee.Image(1).subtract(soilMin.divide(soilMean)).clamp(0, 1).rename('soil_deficit');
var defMean = def.mean().rename('def_mean');
var pdsiMin = pdsi.min().rename('pdsi_min');
var prMean = pr.mean().rename('pr_mean');
var prCv = pr.reduce(ee.Reducer.stdDev()).divide(prMean).rename('pr_cv');

var climate = ee.Image.cat([vpdMean, vpdP95, soilMin, soilMean, soilDeficit, defMean, pdsiMin, prMean, prCv]);

// --- Traits (rescale using metadata) ---
function loadTrait(name) {
  var img = ee.Image('projects/sat-io/open-datasets/global-traits/Shrub_Tree_Grass/' + name);
  var scale = ee.Number(img.get('trait_scale'));
  var offset = ee.Number(img.get('trait_offset'));
  var trait = img.select('b1').multiply(scale).add(offset).rename(name);
  var aoa = img.select('b3').rename(name + '_aoa');
  return trait.addBands(aoa);
}

var traits = loadTrait('SLA')
  .addBands(loadTrait('SSD'))
  .addBands(loadTrait('Rooting_depth'))
  .addBands(loadTrait('Leaf_N_area'))
  .addBands(loadTrait('Stem_conduit_diameter'));

// --- Stack + forest mask ---
var stack = ee.Image.cat([agbMean, agbStd, agbCv, stability, climate, traits])
  .updateMask(agbMean.gte(MIN_AGB));

Map.centerObject(region, 4);
Map.addLayer(stability.clip(region), {min: 0, max: 20, palette: ['red', 'yellow', 'green']}, 'stability');

// --- Sample ---
var points = stack.sample({
  region: region,
  scale: 1000,
  numPixels: N_POINTS,
  seed: SEED,
  geometries: true,
  tileScale: 4
});

print('Sample size', points.size());
print(points.first());

Export.table.toDrive({
  collection: points,
  description: 'tropical_moist_forest_points_raw',
  folder: 'gee_exports',
  fileFormat: 'CSV'
});
