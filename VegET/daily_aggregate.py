"""
Functions for aggregating sub-daily time-step imageCollections to daily time-steps.

This code is largely structured on the openet.core.interp.py description of
aggregate_func() as of 06.04.19
"""

from VegET import interpolate

import ee

def aggregate_to_daily(image_coll, start_date, end_date, agg_type = 'sum'):
    """
    Aggregate sub-daily time-step imageCollections to daily time-steps

    :param image_coll: ee.ImageCollection
        Input image collection at sub-daily time-steps
    :param start_date: date, number, string
    :param end_date:  date, number, string
    :param agg_type: {'sum'},
        Aggregation method (default is 'sum')

    :return: ee.ImageCollection()

    NOTE: as defined in openet.core.interp.py,
    system:time_start of returned images will be 0 UTC, not the image time.
    """

    # Create list of dates in the image_coll
    def get_date(time):
        return ee.Date(ee.Number(time)).format('yyyy-MM-dd')

    date_list = ee.List(image_coll.aggregate_array('system:time_start'))\
        .map(get_date).distinct().sort()

    def aggregate_func(date_str):
        start_date = ee.Date(ee.String(date_str))
        end_date = start_date.advance(1, 'day')
        agg_coll = image_coll.filterDate(start_date, end_date)

        # if agg_type.lower() == 'sum'
        agg_img = agg_coll.sum()

        return agg_img.set({
            'system:index': start_date.format('YYYMMdd'),
            'system:time_start': start_date.millis(),
            'date': start_date.format('YYYY-MM-dd'),
        })

    return ee.ImageCollection(date_list.map(aggregate_func))

