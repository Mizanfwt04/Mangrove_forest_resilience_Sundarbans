/**
 * Chakaria remanent mangrove productivity — GEE Code Editor backup
 *
 * Dataset: Global Pasture Watch annual uGPP (ggpp-30m/v1/ugpp_m)
 * Metrics per 60 m buffer around each site:
 *   Mean_uGPP, SD_uGPP, Temporal_Stability (= Mean/SD),
 *   Sen_Slope, Kendall_Tau
 *
 * Paste into https://code.earthengine.google.com/ and Run.
 * Then start the two Export tasks (site metrics + full time series).
 */

// ======================================================
// GPW ANNUAL uGPP DATASET
// ======================================================

var ugpp = ee.ImageCollection(
  'projects/global-pasture-watch/assets/ggpp-30m/v1/ugpp_m'
).filter(ee.Filter.calendarRange(2000, 2024, 'year'));

// ======================================================
// SITE INVENTORY (n = 30)
// ======================================================

var sites = ee.FeatureCollection([

  // RMSP — remanent mangrove in shrimp ponds
  ee.Feature(ee.Geometry.Point([92.049444, 21.684167]), {ID: 'R1', Group: 'RMSP'}),
  ee.Feature(ee.Geometry.Point([92.053850, 21.694183]), {ID: 'R2', Group: 'RMSP'}),
  ee.Feature(ee.Geometry.Point([92.046400, 21.684517]), {ID: 'R3', Group: 'RMSP'}),
  ee.Feature(ee.Geometry.Point([92.049817, 21.687750]), {ID: 'R4', Group: 'RMSP'}),
  ee.Feature(ee.Geometry.Point([92.050217, 21.680333]), {ID: 'R5', Group: 'RMSP'}),
  ee.Feature(ee.Geometry.Point([92.050833, 21.685083]), {ID: 'R11', Group: 'RMSP'}),
  ee.Feature(ee.Geometry.Point([92.047967, 21.687483]), {ID: 'R12', Group: 'RMSP'}),
  ee.Feature(ee.Geometry.Point([92.051333, 21.681483]), {ID: 'R13', Group: 'RMSP'}),
  ee.Feature(ee.Geometry.Point([92.038073, 21.688113]), {ID: 'R14', Group: 'RMSP'}),
  ee.Feature(ee.Geometry.Point([92.049050, 21.684499]), {ID: 'R15', Group: 'RMSP'}),

  // PMSP — planted mangrove in shrimp ponds
  ee.Feature(ee.Geometry.Point([91.998933, 21.648417]), {ID: 'P1', Group: 'PMSP'}),
  ee.Feature(ee.Geometry.Point([91.985617, 21.648783]), {ID: 'P2', Group: 'PMSP'}),
  ee.Feature(ee.Geometry.Point([91.997717, 21.650633]), {ID: 'P3', Group: 'PMSP'}),
  ee.Feature(ee.Geometry.Point([91.986633, 21.653217]), {ID: 'P4', Group: 'PMSP'}),
  ee.Feature(ee.Geometry.Point([91.962617, 21.672817]), {ID: 'P5', Group: 'PMSP'}),
  ee.Feature(ee.Geometry.Point([91.985875, 21.648760]), {ID: 'P6', Group: 'PMSP'}),
  ee.Feature(ee.Geometry.Point([91.982721, 21.652622]), {ID: 'P7', Group: 'PMSP'}),
  ee.Feature(ee.Geometry.Point([91.984599, 21.655553]), {ID: 'P8', Group: 'PMSP'}),
  ee.Feature(ee.Geometry.Point([91.986912, 21.651018]), {ID: 'P9', Group: 'PMSP'}),
  ee.Feature(ee.Geometry.Point([92.014457, 21.617991]), {ID: 'P10', Group: 'PMSP'}),

  // PMWSP — protected mangrove without shrimp ponds
  ee.Feature(ee.Geometry.Point([92.013333, 21.595278]), {ID: 'N1', Group: 'PMWSP'}),
  ee.Feature(ee.Geometry.Point([92.009722, 21.601389]), {ID: 'N2', Group: 'PMWSP'}),
  ee.Feature(ee.Geometry.Point([91.969883, 21.469167]), {ID: 'N3', Group: 'PMWSP'}),
  ee.Feature(ee.Geometry.Point([91.973417, 21.511150]), {ID: 'N4', Group: 'PMWSP'}),
  ee.Feature(ee.Geometry.Point([92.015700, 21.612200]), {ID: 'N5', Group: 'PMWSP'}),
  ee.Feature(ee.Geometry.Point([92.008450, 21.607083]), {ID: 'N6', Group: 'PMWSP'}),
  ee.Feature(ee.Geometry.Point([92.003200, 21.593867]), {ID: 'N7', Group: 'PMWSP'}),
  ee.Feature(ee.Geometry.Point([91.978167, 21.527200]), {ID: 'N8', Group: 'PMWSP'}),
  ee.Feature(ee.Geometry.Point([92.004883, 21.609133]), {ID: 'N9', Group: 'PMWSP'}),
  ee.Feature(ee.Geometry.Point([92.006717, 21.609433]), {ID: 'N10', Group: 'PMWSP'})
]);

Map.centerObject(sites, 11);
Map.addLayer(sites, {color: 'red'}, 'Sites');

// ======================================================
// SEN SLOPE / MANN–KENDALL PREPARATION
// ======================================================

var annual = ugpp.map(function (img) {
  var year = ee.Date(img.get('system:time_start')).get('year');
  return img.rename('ugpp').addBands(
    ee.Image.constant(year).toFloat().rename('year')
  );
});

// ======================================================
// SITE METRICS
// ======================================================

var results = sites.map(function (ft) {
  var roi = ft.geometry().buffer(60);

  var ts = ee.FeatureCollection(
    ugpp.map(function (img) {
      var value = img.reduceRegion({
        reducer: ee.Reducer.mean(),
        geometry: roi,
        scale: 30,
        maxPixels: 1e13
      }).values().get(0);

      return ee.Feature(null, {
        year: ee.Date(img.get('system:time_start')).get('year'),
        ugpp: value
      });
    })
  );

  var mean = ee.Number(ts.aggregate_mean('ugpp'));
  var sd = ee.Number(ts.aggregate_total_sd('ugpp'));
  var stability = mean.divide(sd);

  var sens = annual.select(['year', 'ugpp']).reduce(ee.Reducer.sensSlope());
  var slope = sens.select('slope').reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: roi,
    scale: 30,
    maxPixels: 1e13
  }).get('slope');

  var mk = annual.select('ugpp').reduce(ee.Reducer.kendallsCorrelation());
  var tau = mk.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: roi,
    scale: 30,
    maxPixels: 1e13
  }).values().get(0);

  return ft.set({
    Mean_uGPP: mean,
    SD_uGPP: sd,
    Temporal_Stability: stability,
    Sen_Slope: slope,
    Kendall_Tau: tau
  });
});

print('Site metrics', results);

Export.table.toDrive({
  collection: results,
  description: 'Chakaria_Mangrove_Productivity',
  fileFormat: 'CSV'
});

// ======================================================
// FULL ANNUAL TIME SERIES
// ======================================================

var allTS = sites.map(function (ft) {
  var roi = ft.geometry().buffer(60);
  return ugpp.map(function (img) {
    var value = img.reduceRegion({
      reducer: ee.Reducer.mean(),
      geometry: roi,
      scale: 30,
      maxPixels: 1e13
    }).values().get(0);

    return ee.Feature(null, {
      Site: ft.get('ID'),
      Group: ft.get('Group'),
      Year: ee.Date(img.get('system:time_start')).get('year'),
      uGPP: value
    });
  });
}).flatten();

Export.table.toDrive({
  collection: allTS,
  description: 'Chakaria_uGPP_TimeSeries',
  fileFormat: 'CSV'
});
