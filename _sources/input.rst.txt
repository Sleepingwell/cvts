******
Inputs
******



.. _gps-data:

GPS data
========

The system expects to find raw data in the directory specified by
:py:data:`cvts.settings.RAW_PATH`. The name of each file is *<vehicle-id>.csv*,
and the vehicle id is inferred from the file name. So far, we have on file
per vehicle per day, and the data for each day is contained in a subdirectory.
All files for a vehicle are concatenated and the GPS points sorted by the time
stamp. An input CSV looks like::

    Index,PlateNumber,Latitude,Longitude,speed,Orientation,VehicleType,Weight,Time
    1,1,108.189498901367,11.0894994735718,17,32,1,1,1501545628
    2,1,108.189796447754,11.0899000167847,9,302.5,1,1,1501545658
    3,1,108.189796447754,11.0899295806885,0,95.5,1,1,1501545779



.. _geographies-data:

Geographic Data
===============

The system expects to find shape files for any geographies providing regionalisations
of interest in the directory :py:data:`cvts.settings.BOUNDARIES_PATH`.

That directory is expected to contain a file named
*geography-geom-field-names.json* that contains a (JSON serialized) dictionary
mapping from the names of the geographies to the fields that contain their
geometry ids. For example::

    {"District": "DistrictID", "trans_cities": "OBJECTID"}
