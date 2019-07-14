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
        'system:index': ref_imgColl.first().get('system:index'),
        'system:time_start': ref_imgColl.first().get('system:time_start')
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
        ": 1").clip(geometry).rename('rain_frac')

    return ee.Image(rain_frac).double()



# TODO: update the docstring.
def vegET_model(daily_imageColl, bbox):
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

    # Define whc_grid
    whc_grid_img = ee.Image(daily_imageColl.first().select('whc'))

    # Drainage Coefficient (ee.Image to add as band for .expression())
    dc_coeff = ee.Image(0.65)

    # rf coefficient (ee.Image to add as band for .expression())
    rf_coeff = ee.Image(1.0).subtract(dc_coeff)

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
        Function to run imageCollection.iterate(). Takes latest value from outputs_list as previous
            time-step SWI, current day whc_image and daily_image
        :param swi_list:
        :param whc_image:
        :param daily_image:
        :return:
        """

        # Outputs from previous day as inputs to current day.
        # NOTE: needs to be cast to list then image. see: https://developers.google.com/earth-engine/ic_iterating
        prev_outputs = ee.Image(ee.List(outputs_list).get(-1))

        # Calculate rain_frac
        rain_frac = rain_frac_calc(daily_img, bbox)

        # Calculate effective precipitation and intercepted precip
        effective_precip = eff_intercept_precip(daily_img)

        # Calculate amount of effective precipitation as rain
        rain = rain_frac.multiply(effective_precip.select('effppt')).rename('rain')

        # TODO: Double check this is ok. Essentially skips first run as is in the esri version
        # TODO: This will be combined with snowpack and swf at end of run to make new outputs_list append
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
                    'tmax': image.select('tmaxC'),
                    'tmin': image.select('tminC')
                }
            )
            melt_rate = melt_rate.set('system:time_start', image.get('system:time_start')).rename('melt_rate')
            return melt_rate

        melt_rate = melt_rate_calc(daily_img)

# TODO: Update docstring
        def snow_melt_calc(melt_rate_img, swe_current, prev_sw_image, geometry):
            """
            Calculate snow melt
            :param melt_rate_img: ee.Image
                Melt rate image
            :param swe_current: ee.Image
                Current time-step calculation of swe
            :param prev_sw_image: ee.Image
                Snowpack band from previous timestep list
            :return: ee.Image
            """

            # Combine images to allow for band selection in expression
            snow_melt_img = melt_rate_img.addBands([swe_current, prev_sw_image.select('snowpack')]).rename(['melt_rate',
                                                                                                     'swe', 'snowpack'])

            snow_melt = snow_melt_img.expression(
                "(b('melt_rate') <= (b('swe') + b('snowpack'))) ? (b('melt_rate'))" +
                ": (b('swe') + b('snowpack'))").clip(geometry).rename(['snowmelt'])
            return snow_melt

        snow_melt = snow_melt_calc(melt_rate, swe, prev_outputs.select('snowpack'), bbox)

        def snowpack_calc(prev_sw_image, swe_current, snow_melt):
            """
            Calculate snowpack
            :param prev_sw_image: ee.Image
                image with band for snowpack at previous timestep
            :param swe_current: ee.Image
                current swe
            :param snow_melt: ee.Image
                current snowmelt
            :return: ee.Image
            """

            snwpk1 = prev_sw_image.add(swe_current).subtract(snow_melt)
            snowpack = snwpk1.where(snwpk1.lt(0.0), 0.0)
            return snowpack

        snowpack = snowpack_calc(prev_outputs.select('snowpack'), swe, snow_melt)

        swi_current = ee.Image(prev_outputs.select('swi').add(rain).add(snow_melt))

        sat_fc = daily_img.select('soil_sat').subtract(daily_img.select('fcap'))

        rf1 = swi_current.subtract(whc_grid_img)

        rf = rf1.where(rf1.lt(0.0), 0.0)

        def srf_calc(rf_img, sat_fc_img, rf_coeff, geometry):
            """
            Calculate srf
            :param rf_img: ee.Image 
                image for rf
            :param sat_fc_img: ee.Image
                sat_fc_image
            :param rf_coeff: ee.Image
                rf coefficient
            :return: ee.Image
            """

            # add bands to make single image for .expression
            srf_input_img = rf_img.addBands([sat_fc_img, rf_coeff]).rename(['rf', 'sat_fc', 'rf_coeff'])

            srf = srf_input_img.expression(
                "(b('rf') <= b('sat_fc')) ? (b('rf') * b('rf_coeff'))" +
                ": (b('rf') - b('sat_fc')) + b('rf_coeff') * b('sat_fc')").clip(geometry).rename('srf')
            return srf

        srf = srf_calc(rf, sat_fc, rf_coeff, bbox)


        # Deep drainage
        ddrain = rf.subtract(srf).double().rename('ddrain')


# TODO: Verify if this is still needed
        # def rfi_calc(image1, image2):
        #     """
        #     Calculate runoff as swi - whc
        #     :param image1: ee.Image
        #         Soil Water Index image
        #     :param image2: ee.Image
        #         Water holding capacity image
        #     :return: ee.Image
        #         Runoff as only positive valued image
        #     """
        #
        #     rf = image1.subtract(image2)
        #
        #     # Set value to 0 if rf < 0
        #     rfi = rf.where(rf.lt(0), 0)
        #
        #     rfi = rfi.set('system:time_start', image1.get('system:time_start'))
        #
        #     return ee.Image(rfi)
        #
        # rfi = rfi_calc(swi_current, whc_grid_img)

        etasw1A = ee.Image(daily_img.select('ndvi').multiply(VARA).add(VARB)).multiply(daily_img.select(
            'eto')).rename('etasw1A')
        etasw1B = ee.Image(daily_img.select('ndvi').multiply(VARA).multiply(daily_img.select('eto'))).rename('etasw1B')

        # TODO: consider ee.Algorithms.If() for conditional statements
        # If ndvi is > 0.4, return etasw1A pixel value, otherwise, return etasw1B
        etasw1 = etasw1B.where(daily_img.select('ndvi').gt(0.4), etasw1A).rename('etasw1')

        etasw2 = etasw1.multiply(swi_current.divide(whc_grid_img.multiply(0.5))).rename('etasw2')
        # use etasw1 pixel when swi_current > whc*0.5, use etasw2 pixel otherwise
        etasw3 = etasw2.where(swi_current.gt(whc_grid_img.multiply(0.5)), etasw1).rename('etasw3')
        # use swi_current pixel where etasw3 > swi_current, use etasw3 pixel otherwise
        etasw4 = etasw3.where(etasw3.gt(swi_current), swi_current).rename('etasw4')
        # use whc pixel where etasw4 is > whc, use etasw4 otherwise
        etasw = etasw4.where(etasw4.gt(whc_grid_img), whc_grid_img).rename('etasw')

        swf1 = swi_current.subtract(etasw).rename('swf1')
        bigswi = ee.Image(whc_grid_img.subtract(etasw)).rename('bigswi')

        swf = bigswi.where(swi_current.gt(whc_grid_img), ee.Image(0.0).where(swf1.lt(0.0), swf1)).rename('swf')

        # TODO: This could be generalized with init_image_create
        def output_image_create(ref_img, swf_img, swe_img, snowpack_img):
            """
            Combine images to create single output image with multiple bands
            :param daily_img: ee.Image
                reference image for timestamp
            :param swf_img: ee.Image
            :param swe_img: ee.Image
            :param snowpack_img: ee.Image
            :return: ee.Image
            """

            output_img = swf_img.addBands([swe_img, snowpack_img]).rename(['swi', 'swe', 'snowpack']) \
                .set({
                'system:index': ref_img.get('system:index'),
                'system:time_start': ref_img.get('system:time_start')
            })

            return ee.Image(output_img)

        # Create output image
        output_image = output_image_create(daily_img, swf, swe, snowpack)

        return ee.List(outputs_list).add(output_image)

    return ee.ImageCollection(ee.List(daily_imageColl.iterate(daily_vegET_calc, outputs_list)))

