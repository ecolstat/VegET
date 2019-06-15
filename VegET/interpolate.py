"""
Interpolation of one imageCollection (source_coll) to the time-step of another (target_coll).
Ex: Create daily ndvi from 8-day ndvi imageCollection by interpolating to time-steps from a daily
imageCollection. This code is largely structured on the openet.core.interp.py description of
linear interpolation as of 06.04.19

The way this is currently written the source imageCollection (e.g., 8-day NDVI) must be a 'global'
dataset. No processes are included for mosaicking multiple images together for dates. This could be
added though, and openet.core.interp.py has methods for this that could be brought over.
"""

from .utils import millis, date_0utc, add_date_band
import ee


def daily(target_coll, source_coll, interp_days=16, interp_method='linear'):
    """NOTE: Largely copied from openet.core.utils.py from 06.04.19 pull, with docstring edits

    Generate daily images from collection

    :param target_coll: The imageCollection of daily images. This is used to set the time-stamps for
        the interpolated images
    :param source_coll: The imageCollection that will be interpolated to the time-step of the target_coll
    :param interp_days: The number of days after source_coll image to consider for values. This will be
        data source specific. Ex: for 8-day modis ndvi the inter_days would need to be at least 8.
    :param interp_method: Strictly 'LINEAR' for now

    :return: ImageCollection of daily interpolated images
    """

    source_coll = ee.ImageCollection(source_coll.map(add_date_band))

    if interp_method.lower() == 'linear':
        def _linear(image):
            """
            Linearly interpolate source images to target image time_start(s)

            :param image: ee.Image, the first band in the image will be used as the 'target' image
                and will be returned with the output image. This image comes from the target_coll.

            :return: ee.Image of interpolated values with band name 'src'.

            NOTES: the source_coll images must have a time band. This function is intended to be mapped over
            an image collection and can take only one input parameter (i.e., an image from the target_coll)
            """

            # TODO: try to keep all bands from tartet_image if useful to do so
            target_image = ee.Image(image).select(0).double()
            target_date = ee.Date(image.get('system:time_start'))

            # All filtering will be done based on 0 UTC dates
            utc0_date = date_0utc(target_date)

            time_image = ee.Image.constant(utc0_date.millis()).double()

            # Build nodata images / masks that can be placed at the front/back of the
            #    qm image collections in the event that the collections are empty, and for
            #    the beginning / end of the time-series
            bands = source_coll.first().bandNames()
            # TODO: make sure these time offsets are doing what is expected regarding exlcusion
            prev_qm_mask = ee.Image.constant(ee.List.repeat(1, bands.length())) \
                .double().rename(bands).updateMask(0) \
                .set({
                'system:time_start': utc0_date.advance(
                    -interp_days - 1, 'day').millis()})
            next_qm_mask = ee.Image.constant(ee.List.repeat(1, bands.length())) \
                .double().rename(bands).updateMask(0) \
                .set({
                'system:time_start': utc0_date.advance(
                    interp_days + 2, 'day').millis()})

            # Build separate collections for before and after the target date
            prev_qm_coll = source_coll.filterDate(
                utc0_date.advance(-interp_days, 'day'), utc0_date) \
                .merge(ee.ImageCollection(prev_qm_mask))
            next_qm_coll = source_coll.filterDate(
                utc0_date, utc0_date.advance(interp_days + 1, 'day')) \
                .merge(ee.ImageCollection(next_qm_mask))

            # Flatten the previous / next collections to single images
            # The closest image in time should be on 'top'
            prev_qm_image = prev_qm_coll.sort('system:time_start', True).mosaic()
            next_qm_image = next_qm_coll.sort('system:time_start', False).mosaic()

            # Remove 'time' band before interpolation (this is on images originally from
            #    the source_coll
            prev_bands = prev_qm_image.bandNames() \
                .filter(ee.Filter.notEquals('item', 'time'))
            next_bands = next_qm_image.bandNames() \
                .filter(ee.Filter.notEquals('item', 'time'))
            prev_value_image = ee.Image(prev_qm_image.select(prev_bands)).double()
            next_value_image = ee.Image(next_qm_image.select(next_bands)).double()
            prev_time_image = ee.Image(prev_qm_image.select('time')).double()
            next_time_image = ee.Image(next_qm_image.select('time')).double()

            # NOTE: This may not be necessary for 'global' data products, but retained for
            #    reference
            # TODO: verify the note above is correct and adjust as needed
            # Fill masked values with values from the opposite image. Necessary to ensure
            #    that there are always tw0 values to interpolate between.
            prev_time_mosaic = ee.Image(ee.ImageCollection.fromImages([
                next_time_image, prev_time_image]).mosaic())
            next_time_mosaic = ee.Image(ee.ImageCollection.fromImages([
                prev_time_image, next_time_image]).mosaic())
            prev_value_mosaic = ee.Image(ee.ImageCollection.fromImages([
                next_value_image, prev_value_image]).mosaic())
            next_value_mosaic = ee.Image(ee.ImageCollection.fromImages([
                prev_value_image, next_value_image]).mosaic())

            # Calculate time ratio of current image from target_coll between the other source_coll
            #    images.
            time_ratio_image = time_image.subtract(prev_time_mosaic) \
                .divide(next_time_mosaic.subtract(prev_time_mosaic))

            # Interpolate values to the current image (i.e., target_coll image) time
            interp_value_image = next_value_mosaic.subtract(prev_value_mosaic) \
                .multiply(time_ratio_image).add(prev_value_mosaic)

            return interp_value_image \
                .addBands(target_image) \
                .set({
                'system:index': image.get('system:index'),
                'system:time_start': image.get('system:time_start')
            })

        interp_coll = ee.ImageCollection(target_coll.map(_linear))

        return interp_coll
