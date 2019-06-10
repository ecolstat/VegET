"""
Utility functions for formatting time-stamps and creating time / date information for imagecollections

This code is largely structured on methods defined in openet.core.utils.py as of 06.04.19
"""

import calendar
import datetime


import ee


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

def merge_colls(main_coll, secondary_coll, bands_2_add):
    """
    Function for band-wise merging of multiple ee.ImageCollections
    :param main_coll: ee.ImageCollection
        Collection into which bands will be added
    :param secondary_coll: ee.ImageCollection
        Collection whose images will be added as bands to main_coll
    :param bands_2_add: list
        List of band name(s) from secondary_coll to add to main_coll
    :return: ee.ImageCollection
    """

    def _newBands(main_image):
        """
        # TODO: change the description
        Function to take in a single image and add its band(s) to the main_coll image with
        matching time band
        :param main_image: ee.Image
            Image from secondary_coll
        :return: ee.Image
            Image with band from secondary_coll added
        """
        main_index = ee.String(main_image.get('system:index'))
        sec_filter = secondary_coll.filterMetadata('system:index', 'equals', main_index)
        sec_image = ee.Image(sec_filter.first())
        sec_image = sec_image.select(bands_2_add)

        # TODO: this depends on image_2_add being a single band image. Change to make more general.
        return main_image.addBands(sec_image) \
            .set({
            'system:index': main_image.get('system:index'),
            'system:time_start': main_image.get('system:time_start')
        })

    merged_coll = ee.ImageCollection(main_coll.map(_newBands))

    return merged_coll



