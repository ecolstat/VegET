# VegET
VegET: daily ET modeling
Testing a Google Earth Engine (GEE) implementation of the VegET daily evapotranspiration model originally described in [Senay (2008)](https://www.mdpi.com/1999-4893/1/2/52). Original VegET model development and code created and shared by G. Senay, S. Kagone and M. Velpuri. This repository contains initial attempts to transition VegET to running on GEE for testing purposes. The project relies heavily on work by the [openet](https://github.com/Open-ET) group to enable GEE processing. 

Required static input files provided by S. Kagone, and M. Velpuri.

## Contents:
### VegET directory:
-  __veg_et_model.py__:  main functions used in running VegET. Functions were defined in the original VegET implementation code shared by G. Senay, S. Kagone, and M. Velpuri, and were changed as little as possible to allow for GEE data/algorithms.
- __utils.py__: utility functions for various band additions, date calculations, etc. Original code source: [openet](https://github.com/Open-ET). 
- __Interpolate.py__: functions for creating daily image data for NDVI and climate variables (e.g., precipitation, temperature, etc.). Original code source: [openet](https://github.com/Open-ET). 
- __daily_aggregate.py__: Script for aggregating sub-daily data to daily values. Original code source: [openet](https://github.com/Open-ET). 
- __veg_et.py__: Testing script for running VegET components in an interactive Python console.

### testing_notebooks directory:
*Note*: all Jupyter notebooks in this directory were created for testing various model runs/visualizations, etc. They are largely outdated and only kept for reference. Visualization approaches by the [openet](https://github.com/Open-ET) group are far more advanced. 

### Static input files (not included):
Static, gridded input files provided by G. Senay, S. Kagone, and M. Velpuri are necessary to run VegET, and are not included in this repository. Necessary files include: canopy interception, soil grid and snow grid. These files have been converted into GEE assets. 
