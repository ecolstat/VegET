"""
Defines the formula for running VegET on inputs. As defined here the function can be
run iteratively over an Earth Engine imageCollection.
"""


# Function to calculate Soil Water Index (SWI)
def vegET_model (ndvi_coll, ppt_coll, pet_coll, canop_int_coll, whc_grid_coll):
    """
    Calculate VegET results and return imageCollection
    :param ndvi_coll: Collection of daily ndvi images
    :param ppt_coll: Collection of daily precipitation images
    :param pet_coll: Collection of daily potential evapotranspiration images
    :param canop_int_coll: Collection of daily (or static) canopy interception images
    :param whc_grid_coll: Static image of water holding capacity

    :return: ImageCollection of daily ET estimates
    """

    # Define initial soil water
    sw_0 = whc_grid.multiply(0.5)

    # Define constant variables
    VAR_A = 1.25
    VAR_B = 0.2