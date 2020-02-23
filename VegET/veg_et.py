"""
Testing VegET runs in interactive Python console.

VegET model code from G. Senay, S. Kagone, and M.Velpuri
Openet code from openet (etdata.org) and (https://github.com/Open-ET)
"""

from VegET import interpolate, daily_aggregate, utils, veg_et_model
import cartoee as cee
import matplotlib.pyplot as plt
import ee
import ee.mapclient

ee.Initialize()

# TODO: change all to be user inputs

# Define date range
# TODO: this needs a check to ensure the dates are within the ranges for the imageCollections
#    accounting for the extra dates added for interpolation
start_date = ee.Date('2003-04-01')
end_date = ee.Date('2003-11-01')

# TODO: needs a check to ensure spatial overlap between this and imageCollections
# TODO: add ability to include shapefiles or manually defined coordinates
# Filter to only include images within the colorado and utah boundaries (from ee-api/python examples)
polygon = ee.Geometry.Polygon([[
    [-109.05, 37.0], [-102.05, 37.0], [-102.05, 41.0],   # colorado
    [-109.05, 41.0], [-111.05, 41.0], [-111.05, 42.0],   # utah
    [-114.05, 42.0], [-114.05, 37.0], [-109.05, 37.0]]])

# Define growing season months as integers. Filtering is inclusive.
g_season_begin = 4
g_season_end = 10

# NOTE: for this case, the imagecollections are global or continent wide rasters. Ordinarily, the
#   imageCollections would need .filterBounds() to the ROI to subset to the images that intersect the
#   polygon. In this case, the filter does nothing since the images are continent/global scale.

# TODO: Generalize so user can pick raw bands or modeled bands (e.g., ndvi)
#   and add check to ensure those bands are in the imageCollection, as well as calculations
#   if necessary from raw bands
# Get NDVI collection and clip to ROI
# TODO: cloud masking
# TODO: Check to see if this could be condensed into one call
ndvi_coll = ee.ImageCollection("MODIS/006/MOD09Q1").filterDate(start_date, end_date)\
    .filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
    .map(lambda f: f.clip(polygon))
ndvi_coll = ndvi_coll.map(utils.getNDVI)
# DS: select 'ndvi' may not be necessary. Seems to return a 1 band image
# ndvi_coll = ndvi_coll.select('NDVI')

# Get daily climate dataset(prexcip, eto, temp)
# TODO: band is hardcoded to precipitation and daily ref et (et0 -> grass)
precip_eto_coll = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET').filterDate(start_date, end_date)\
    .select('pr', 'eto', 'tmmn', 'tmmx').filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
    .map(lambda f: f.clip(polygon))

# Add band for calculated mean daily temp
precip_eto_coll = precip_eto_coll.map(utils.dailyMeanTemp)
# Convert to Celsius
precip_eto_coll = precip_eto_coll.map(utils.kelvin2celsius).select(['pr', 'eto', 'tminC', 'tmaxC', 'tmeanC'])

# TODO: Condense all static asset integration to a function in utils
# Specify canopy intercept image or imageCollection. NOTE: Assumes single band image
canopy_int = ee.Image('users/darin_EE/VegET/Interception').clip(polygon).double().rename('intercept')
# Get static Soil Water Holding Capacity grid (manually uploaded as GEE asset)
whc = ee.Image('users/darin_EE/VegET/WaterHoldingCapacity_mm').clip(polygon).double().rename('whc')
# Get static Soil Saturation image
soil_sat = ee.Image('users/darin_EE/VegET/SoilSaturation_mm').clip(polygon).double().rename('soil_sat')
# Get static Field Capacity image
fcap = ee.Image('users/darin_EE/VegET/FieldCapacity_mm').clip(polygon).double().rename('fcap')

# Create single static image with static inputs as bands
staticImage = canopy_int.addBands([whc, soil_sat, fcap])

# Add statics to ndvi_coll as bands
ndvi_coll = ndvi_coll.map(utils.addStaticBands([staticImage]))

# Create daily interpolated ndvi collection
ndvi_daily = interpolate.daily(precip_eto_coll, ndvi_coll)

# Add date band as 'time'
ndvi_daily = ee.ImageCollection(ndvi_daily.map(utils.add_date_band))
#canInt_daily = ee.ImageCollection(canInt_daily.map(utils.add_date_band))

# Merge images to new ImageCollection as bands by date
# NOTE: eto was removed in interp since it only takes the first band for target coll. Add back here.

#merged_coll = utils.merge_colls(ndvi_daily, precip_eto_coll, bands_2_add = 'eto')
#merged_coll = utils.merge_colls(merged_coll, canInt_daily, bands_2_add = 'Ei')

# Run VegET model
vegET_run = veg_et_model.vegET_model(ndvi_daily, polygon)

#if __name__ == '__main__':
#    pass

# Show map example (NOTE: outdated visualization, but used for initial testing)
#ee.mapclient.addToMap(vegET_run.first())2