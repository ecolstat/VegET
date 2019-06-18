"""
Defines the formula for running VegET on inputs. As defined here the function can be
run iteratively over an Earth Engine imageCollection.
"""

import ee
from VegET import utils
ee.Initialize()

# TODO: update docstring
def init_image_create(ref_imgColl, whc_img, effppt):
    """
    Create necessary images with predifined initial values. Serve as input to first step in VegET run.
    :param ref_imgColl: ee.ImageCollection
        Reference imageCollection for spatial scale and time-stamp. Initially using GRIDMET image.
    :param whc_img: ee.Image
        Water holding capacity static image for creating SWI
    :return: ee.Image
        Image with bands for swi, swe and snowpack initial values.
    """

    swe = ee.Image(utils.const_imageColl(ref_imgColl, 0))
    snowpack = ee.Image(utils.const_imageColl(ref_imgColl, 0))

    # TODO: Adding swe is unnecessary since it is 0 valued for the initial state
    swi = ee.Image(utils.const_image(whc_img, 0.5)).multiply(effppt).add(swe)

    dynamic_imgs = swi.addBands([swe, snowpack]).rename(['swi', 'swe', 'snowpack'])\
        .set({
        'system:index': ref_imgColl.get('system:index'),
        'system:time_start': ref_imgColl.get('system:time_start')
    })

    return ee.Image(dynamic_imgs)


def eff_intercept_precip(image):
    """
    Calculate effective precipitation and interception
    :param image: ee.Image
        Image with precipitation and canopy interception bands

    :return: ee.Image
        Image with bands for effective precip and intercepted precip
    """
    # TODO: This is hardcoded for the GRIDMET precip band name 'pr'. Generalize if needed
    effppt = image.expression(
        'PRECIP * (1 - (INTERCEPT/100))', {
            'PRECIP': image.select('pr'),
            'INTERCEPT': image.select('intercept')
        }
    )
    intppt = image.expression(
        'PRECIP * (INTERCEPT/100)', {
            'PRECIP': image.select('pr'),
            'INTERCEPT': image.select('intercept')
        }
    )

    effppt = effppt.set('system:time_start', image.get('system:time_start'))
    intppt = intppt.set('system:time_start', image.get('system:time_start'))

    eff_int_img = effppt.addBands(intppt).double().rename(['effppt', 'intercept'])

    return ee.Image(eff_int_img)


# TODO: this hardcodes the tmeanC band name and threshold values. Possible user input?
def rain_frac_calc(image, geometry):
    """
    Calculate rain fraction (used to scale effective precip as snow water equivalent or rain depending on temperature.
    :param geometry: ee.Feature, ee.FeatureCollection, ee.Geometry
        Bounding region. Expressions do not respect image bounds, so it needs to be clipped.
    :param image: ee.Image
        Image with mean temperature band
    :return: ee.Image
        Image representing proportion of effective precip that should be considered rain
    """

    rain_frac = image.expression(
        "(b('tmeanC') <= 6.0) ? 0" +
        ": (b('tmeanC') > 6.0) && (b('tmeanC') < 12.0) ? (b('tmeanC') * 0.0833)" +
        ": 1").clip(geometry)

    return ee.Image(rain_frac).double()



# TODO: update the docstring.
def vegET_model(daily_imageColl, whc_grid_img, bbox, start_date):
    """
    Calculate Daily Soil Water Index (SWI)
    :param start_date: ee.Date
        First date for analysis. Used to calculate initial SWI and then removed from collection.
    :param daily_imageColl: ee.ImageCollection
        Collection of daily images with bands for ndvi, precip, pet, canopy intercept
    :param whc_grid_img: ee.Image
        Static water holding capacity image
    :return: ee.ImageCollection
        imageCollection of daily Soil Water Index
    """
    # TODO: Verify if these should be user inputs
    # Define constant variables
    VARA = ee.Number(1.25)
    VARB = ee.Number(0.2)

    # Calculate initial values where necessary
    init_effppt = eff_intercept_precip(daily_imageColl.first())
    initial_images = init_image_create(daily_imageColl, whc_grid_img, init_effppt.select('effppt'))

    # Create list for dynamic variables to be used in .iterate()
    outputs_list = ee.List([initial_images])

    # Create constant image for calculations in daily_vegET_calc()
    const_img = ee.Image(1.0)

# TODO: Update docstring
    def daily_vegET_calc(daily_img, outputs_list):
        """
        Function to run imageCollection.iterate(). Takes latest value from swi_list as previous
            time-step SWI, current day whc_image and daily_image
        :param swi_list:
        :param whc_image:
        :param daily_image:
        :return:
        """

        # Outputs from previous day as inputs to current day.
        # NOTE: needs to be cast to list then image. see: https://developers.google.com/earth-engine/ic_iterating
        prev_outputs = ee.Image(ee.List(outputs_list.get(-1)))

        # Calculate rain_frac
        rain_frac = rain_frac_calc(daily_img, bbox)

        # Calculate effective precipitation and intercepted precip
        effective_precip = eff_intercept_precip(daily_img)

        # Calculate amount of effective precipitation as rain
        rain = rain_frac.multiply(effective_precip.select('effppt'))

        # TODO: Double check this is ok. Essentially skips first run as is in the esri version

        swe = ee.Image(const_img.subtract(rain_frac)).multiply(effective_precip.select('effppt'))

        def melt_rate_calc(image):
            """
            Calculate melt_rate
            :param image: ee.Image
                Image with max and min temp bands
            :return: ee.Image

            """
            melt_rate = image.expression(
                 '0.06 * ((tmax * tmax) - (tmax * tmin))', {
                    'tmax': image.select('tmmxC'),
                    'tmin': image.select('tmmnC')
                }
            )
            melt_rate = melt_rate.set('system:time_start', image.get('system:time_start'))
            return melt_rate

        melt_rate = melt_rate_calc(daily_img)

# TODO: Update docstring
        def snow_melt_calc(melt_rate_img, swe_img):
            """
            Calculate snow melt from melt rate and soil water equivalent
            :param melt_rate_img:
            :param swe_img:
            :return:
            """

            # Combine images to allow for band selection in expression
            snow_melt_img = melt_rate_img.addBands(swe_img).rename(['melt_rate', 'swe'])
            snow_melt = snow_melt_img.expression(

            )



        swi_current = ee.Image(prev_swi.select('swi').add(effective_precip))


        def rfi_calc(image1, image2):
            """
            Calculate runoff as swi - whc
            :param image1: ee.Image
                Soil Water Index image
            :param image2: ee.Image
                Water holding capacity image
            :return: ee.Image
                Runoff as only positive valued image
            """

            rf = image1.subtract(image2)

            # Set value to 0 if rf < 0
            rfi = rf.where(rf.lt(0), 0)

            rfi = rfi.set('system:time_start', image1.get('system:time_start'))

            return ee.Image(rfi)

        rfi = rfi_calc(swi_current, whc_grid_img)

        etasw1A = ee.Image(daily_image.select('NDVI').multiply(VARA).add(VARB)).multiply(daily_image.select(
            'PotEvap_tavg'))
        etasw1B = ee.Image(daily_image.select('NDVI').multiply(VARA).multiply(daily_image.select('PotEvap_tavg')))

        # TODO: consider ee.Algorithms.If() for conditional statements
        # DS This may fail since it's calling on values in multiple images
        etasw1 = etasw1A.where(daily_image.select('NDVI').gt(0.4), etasw1B)

        etasw2 = etasw1.multiply(swi_current.divide(whc_grid_img.multiply(0.5)))
        etasw3 = etasw1.where(swi_current.gt(whc_grid_img.multiply(0.5)), etasw2)
        etasw4 = swi_current.where(etasw3.gt(swi_current), etasw3)
        etasw = whc_grid_img.where(etasw4.gt(whc_grid_img), etasw4)

        swf1 = swi_current.subtract(etasw)
        whc_diff = ee.Image(whc_grid_img.subtract(etasw))

        swf = whc_diff.where(swi_current.gt(whc_grid_img), ee.Image(0.0).where(swf1.gt(0.0), swf1))

        return ee.List(swi_list).add(swf)
