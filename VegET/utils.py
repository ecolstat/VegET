"""
Utility functions for formatting time-stamps and creating time / date information for imagecollections

This code is largely structured on methods defined in openet.core.utils.py as of 06.04.19
"""

import calendar
import datetime


import ee


def date_0utc(date):
    """NOTE: Copied from openet.core.utils.py from 06.04.19 pull
    Get the 0 UTC date for a date

    Parameters
    ----------
    date : ee.Date
    Returns
    -------
    ee.Date
    """
    return ee.Date.fromYMD(date.get('year'), date.get('month'),
                           date.get('day'))


def add_date_band(image):
    """
    Some operations require that images in collections have 'time' bands. This function is
    to be mapped to an imageCollection and takes only one image as input.
    :param image: ee.Image
        image to which a time band will be added
    :return: ee.Image
        image with time band added
    """
    date_value = date_0utc(ee.Date(image.get('system:time_start')))
    return image.addBands([
        image.select([0]).double().multiply(0).add(date_value.millis()).rename(['time'])])


def addStaticBands(staticsImg):
    """
    Add static images as bands to an imageCollection.
    :param staticsImg: ee.Image
        Single image created from multiple static input images
    :return: ee.Image
        Image with bands added for static input images
    """
    def wrap(image):
        """
        addBands to image in main collection.
        :param image: ee.Image
            image in main collection to which static bands will be added
        :return: ee.Image
            image with bands from the statics image added
        """
        newBands = image.addBands(staticsImg)
        return newBands

    return wrap


def const_image(img, value):
    """
    Create an image with constant values at spatial scale of img
    :param img: ee.Image
        reference image for spatial scale and possibly time-stamp
    :param value: ee.Number
        Constant value to populate the image pixels
    :return: ee.Image
        image with all pixel values set to value parameter
    """
    # TODO: change to check for collection vs image type to determine if .first() should be used.
    const_img = ee.Image(img.select(0).multiply(value).double());
    return const_img

# TODO: This should be combined with const_image() function.
def const_imageColl(imgColl, value):
    """
    Create an image with constant values at spatial scale of imgColl
    :param imgColl: ee.Image
        reference image for spatial scale and possibly time-stamp
    :param value: ee.Number
        Constant value to populate the image pixels
    :return: ee.Image
        image with all pixel values set to value parameter
    """
    # TODO: change to check for collection vs image type to determine if .first() should be used.
    const_img = ee.Image(imgColl.first().select(0).multiply(value).double());
    return const_img


def dailyMeanTemp(img):
    """
    Calculate daily mean temp from daily GRIDMET max and min temp
    :param image: ee.Image
        GRIDMET image with daily min and max temp bands
    :return: ee.Image
        Image with mean daily temperature as a band
    """

    meanTemp = ee.Image(img.select('tmmn').add(img.select('tmmx'))).divide(ee.Number(2)).rename('tmean')
    newImage = img.addBands(meanTemp)
    return newImage


def getNDVI(image):
    """
    Function for calculating NDVI (used here for 8-day NDVI from preprocessed MODIS Terra 8-day SR)
    :param image: ee.Image
        Image with appropriate bands for calculating NDVI
    :return: ee.Image
        Image with NDVI band added
    """
    # TODO: include checks for identifying sensor and appropriate bands. Now just hardcoded for MODIS
    # For MODIS
    ndvi_calc = image.normalizedDifference(['sur_refl_b01', 'sur_refl_b02']).double().rename('NDVI')
    return ndvi_calc\
        .set({
            'system:index': image.get('system:index'),
            'system:time_start': image.get('system:time_start')
    })


# DS: Note: This is not used, but it's potentially a very useful function that may be used later
# # TODO: Change to accept unknown number of secondayr_colls and band names as list
# def merge_colls(main_coll, secondary_coll, bands_2_add):
#     """
#     Function for band-wise merging of multiple ee.ImageCollections
#     :param main_coll: ee.ImageCollection
#         Collection into which bands will be added
#     :param secondary_coll: ee.ImageCollection
#         Collection whose images will be added as bands to main_coll
#     :param bands_2_add: list
#         List of band name(s) from secondary_coll to add to main_coll
#     :return: ee.ImageCollection
#     """
#
#     def _newBands(main_image):
#         """
#         # TODO: change the description
#         Function to take in a single image and add its band(s) to the main_coll image with
#         matching time band
#         :param main_image: ee.Image
#             Image from secondary_coll
#         :return: ee.Image
#             Image with band from secondary_coll added
#         """
#         main_index = ee.String(main_image.get('system:index'))
#         sec_filter = secondary_coll.filterMetadata('system:index', 'equals', main_index)
#         sec_image = ee.Image(sec_filter.first())
#         sec_image = sec_image.select(bands_2_add)
#
#         # TODO: this depends on image_2_add being a single band image. Change to make more general.
#         return main_image.addBands(sec_image) \
#             .set({
#             'system:index': main_image.get('system:index'),
#             'system:time_start': main_image.get('system:time_start')
#         })
#
#     merged_coll = ee.ImageCollection(main_coll.map(_newBands))
#
#     return merged_coll


def kelvin2celsius(img):
    """
    Kelvin to celsius conversion for gridmet data temperature bands
    NOTE: Assumes daily mean temp has been calculated (see utils.dailyMeanTemp())
    :param image: ee.Image
        Gridmet image with tmmn, tmmx and (calculated) tmean bands
    :return: ee.Image
        Image with temperature values converted from kelvin to celsius
    """

    tempsC = ee.Image(img.select(['tmmn', 'tmmx', 'tmean']).subtract(ee.Number(273.15))).rename(['tminC', 'tmaxC',
                                                                                              'tmeanC'])

    newImage = img.addBands(tempsC)
    return newImage


def millis(input_dt):
    """NOTE: Copied from openet.core.utils.py from 06.04.19 pull
    Convert datetime to milliseconds since epoch


    Parameters
    ----------
    input_df : datetime

    Returns
    -------
    int

    """
    return 1000 * int(calendar.timegm(input_dt.timetuple()))

