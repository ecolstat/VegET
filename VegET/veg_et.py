"""
Main file for running VegET model.

"""

from VegET import interpolate, daily_aggregate, utils

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
ndvi_coll = ee.ImageCollection("MODIS/006/MOD13Q1").filterDate(start_date, end_date)\
    .select('NDVI').filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
    .map(lambda f: f.clip(polygon))

# Get daily climate dataset
# TODO: band is hardcoded to precipitation
precip_coll = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET').filterDate(start_date, end_date)\
    .select('pr').filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
    .map(lambda f: f.clip(polygon))

# Get Potential ET imageCollection
# TODO: Band is hardcoded to 'PotEvap_tavg'. Needs to be generalized.
pet_coll =  ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H").filterDate(start_date, end_date)\
    .select('PotEvap_tavg').filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
    .map(lambda f: f.clip(polygon))

# Specify canopy intercept image or imageCollection
# TODO: Band is hardcoded to 'Ei' for intercept. Needs to be generalized.
canop_int_coll = ee.ImageCollection("CAS/IGSNRR/PML/V2").filterDate(start_date, end_date)\
    .select('Ei').filter(ee.Filter.calendarRange(g_season_begin, g_season_end, 'month'))\
    .map(lambda f: f.clip(polygon))


# Get static Soil Water Holding Capacity grid (manually uploaded as GEE asset)
whc_grid = ee.Image('users/darin_EE/whc3_1mwgs250m.tif')

ndvi_daily = interpolate.daily(precip_coll, ndvi_coll)
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


#if __name__ == '__main__':
#    pass

