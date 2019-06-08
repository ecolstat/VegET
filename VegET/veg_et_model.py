"""
Defines the formula for running VegET on inputs. As defined here the function can be
run iteratively over an Earth Engine imageCollection.
"""

import ee

ee.Initialize()

# Using imageCollection.iterate() to make a collection of Soil Water Flux images.



def vegET_model(daily_image, whc_grid_img):
    """
    Calculate Daily Soil Water Index (SWI)
    :param daily_image: ee.Image
        Daily image with bands for ndvi, precip, pet, canopy intercept
    :param whc_grid_img: ee.Image
        Static water holding capacity image
    :return: ee.Image
        image of daily Soil Water Index
    """
    # TODO: Verify if these should be user inputs
    # Define constant variables
    VARA = 1.25
    VARB = 0.2

    # DS: moved to swi initial calculations. If that works, delete these
    # Get the date for daily_image
    #time0 = daily_image.first().get('system:time_start')

    # Create empty list for swi images to store results of iterate()
    #first_day = ee.List([
    #    ee.Image(0).set('system:time_start', time0).select([0], ['SWI'])
    #])


    def effec_precip(image):
        """
        Calculate effective precipitation
        :param image: ee.Image
            Image with precip and intercept bands

        :return: ee.Image
            Effective precipitation accounting for canopy intercept
        """

        effppt = image.expression(
            'PRECIP * (1 - (INTERCEPT/100))', {
                'PRECIP': image.select('pr'),
                'INTERCEPT': image.select('Ei')
            }
        )
        effppt = effppt.set('system:time_start', image.get('system:time_start'))

        return ee.Image(effppt)

    effect_ppt = effec_precip(daily_image)

    #    DS: This doesn't appear to be used in the demo model
    #    def intercepted_precip(image):
    #        """
    #        Calculate intercepted precipitation
    #
    #        :param image: ee.Image
    #            Image with precipitation and canopy interception bands
    #        :return: ee.Image
    #            Intercepted precipitation
    #        """
    #
    #        intppt = image.expression(
    #            'PRECIP * (INTERCEPT/100)', {
    #                'PRECIP': image.select('pr'),
    #                'INTERCEPT': image.select('Ei')
    #            }
    #        )
    #
    #        return ee.Image(intppt)

    def swi_init_calc(whc_img, effective_ppt):
        """
        Calculate soil water index initial value
        :param whc_img: ee.Image
            Static image of water holding capacity
        :param effective_ppt: ee.Image
            Effective precipitation as calculated in effec_precip()
        :return: ee.Image
            Soil water index
        """
        swi = whc_img.multiply(0.5).add(effective_ppt)

        swi = swi.set('system:time_start', effective_ppt.get('system:time_start'))

        return ee.Image(swi)

    swi_init = swi_init_calc(whc_grid_img, effect_ppt)

    # Create empty list for imageCollection.iterate()
    first_day = ee.List([
        ee.Image(swi_init).set('system:time_start', swi_init.get('system:time_start')).select([0], ['SWI'])
    ])


    def daily_swi_calc(swi_list, whc_image, daily_image):
        """
        Function to run imageCollection.iterate(). Takes latest value from swi_list as previous
            time-step SWI, current day whc_image and daily_image
        :param swi_list:
        :param whc_image:
        :param daily_image:
        :return:
        """

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

        rfi = rfi_calc(swi, whc_grid_img)

        def eta_calc(image):
            """
            Calculate effective precipitation
            :param image: ee.Image
                Image with precip and intercept bands

            :return: ee.Image
                Effective precipitation accounting for canopy intercept
            """

            effppt = image.expression(
                'PRECIP * (1 - (INTERCEPT/100))', {
                    'PRECIP': image.select('pr'),
                    'INTERCEPT': image.select('Ei')
                }
            )

            effppt = effppt.set('system:time_start', image.get('system:time_start'))

            return ee.Image(effppt)


