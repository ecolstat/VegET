"""
Main file for running VegET model.

"""

from VegET import interpolate, daily_aggregate, utils
import cartoee as cee
import matplotlib.pyplot as plt
import ee

ee.Initialize()

# TODO: change all to be user inputs
# Specify needed inputs for VegET runs

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
# TODO: Check to see if this could be codensed into one call
ndvi_coll = ee.ImageCollection("MODIS/006/MOD09Q1").filterDate(start_date, end_date)\
    .filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
    .map(lambda f: f.clip(polygon))
ndvi_coll = ndvi_coll.map(utils.addNDVI)
ndvi_coll = ndvi_coll.select('NDVI')

# Get daily climate dataset(prexcip, eto, temp)
# TODO: band is hardcoded to precipitation and daily ref et (et0 -> grass)
precip_eto_coll = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET').filterDate(start_date, end_date)\
    .select('pr', 'eto').filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
    .map(lambda f: f.clip(polygon))

# DS: Old version using GLDS. Delete if not needed anymore.
# Get Potential ET imageCollection
# pet_coll =  ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H").filterDate(start_date, end_date)\
#     .select('PotEvap_tavg').filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
#     .map(lambda f: f.clip(polygon))

# DS: Old version using PML/V2. Delete if not needed anymore.
# Specify canopy intercept image or imageCollection
# # DS: Band is hardcoded to 'Ei' for intercept. Needs to be generalized.
# canop_int_coll = ee.ImageCollection("CAS/IGSNRR/PML/V2").filterDate(start_date, end_date)\
#     .select('Ei').filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
#     .map(lambda f: f.clip(polygon))

# Specify canopy intercept image or imageCollection
canopy_int = ee.Image('users/darin_EE/VegET/Interception')

# Get static Soil Water Holding Capacity grid (manually uploaded as GEE asset)
whc = ee.Image('users/darin_EE/VegET/WaterHoldingCapacity_mm')

# Get static Soil Saturation image
soil_sat = ee.Image('users/darin_EE/VegET/SoilSaturation_mm')

# Get static Field Capacity image
fcap = ee.Image('users/darin_EE/VegET/FieldCapacity_mm')

# Get initial soil water EEEEEEEE image
init_swe = ee.Image('users/darin_EE/VegET/SWE_initial')

# Get initial snowpack image
init_snow_pack = ee.Image('users/darin_EE/VegET/Snowpack_initial')

ndvi_daily = interpolate.daily(precip_eto_coll, ndvi_coll)

# DS: This shouldn't be needed anymore if using eto from gridmet
pet_daily = daily_aggregate.aggregate_to_daily(pet_coll, start_date, end_date)
# TODO: As is, this needs to be run individually since interpolate.py takes only the first band of the
#    target image. Generalize interpolate to be able to extract multiple bands to allow for passing in
#    a previously interpolated collection.
canInt_daily = interpolate.daily(precip_coll, canop_int_coll)

ndvi_daily = ee.ImageCollection(ndvi_daily.map(utils.add_date_band))
pet_daily = ee.ImageCollection(pet_daily.map(utils.add_date_band))
canInt_daily = ee.ImageCollection(canInt_daily.map(utils.add_date_band))

# Merge images to new ImageCollection as bands by date
merged_coll = utils.merge_colls(ndvi_daily, pet_daily, bands_2_add = 'PotEvap_tavg')
merged_coll = utils.merge_colls(merged_coll, canInt_daily, bands_2_add = 'Ei')

# TODO: add in snowmelt

#if __name__ == '__main__':
#    pass

