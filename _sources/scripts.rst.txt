*******
Scripts
*******

Python scripts used in CVTS. These are installed with the python package.




Utilities for Individual Files
==============================

csv2json
--------

Python script for converting CSVs to JSON appropriate for feeding to the
`trace_attributes`_ service of Valhalla. This is convenient for converting
single files when testing/playing/etc.

json2geojson
------------

Python script for converting the json files produced by the `trace_attributes`_
service of Valhalla to GeoJSON files. This is also useful for
testing/playing/ect.

anonymizeregos
--------------

Script for anonymizing regos in the raw data.

User will be prompted for salt, which is then added to the rego and hashed
using sha256. Note that this while this is not recommended for passwords, it
should be adequate for this case should (I think that if you can access the
data, then looking at the trace will be a much easier way to determine the rego
than brute forcing the hash).

**Note that the salt must be kept secret**.




Entry Points for the (`Luigi`_) Workflow
========================================

These scripts ensure that various `tasks`_ are complete.

The results of these scripts are saved in sub-folders of the

processtraces
-------------

Script for matching all raw data to the road network.

regioncounts
------------

Script for extracting:

- stops by region,
- stops on a (0.1 degree) raster, and
- source and destination counts.

speed
-----

Script for calculating speed by road segment by time of day for each vehicle.
What we would really like, is to have the results of this summarised for all
vehicles. We have not yet got to doing that, which would be best done with a
DB, Hadoop or some other thing that would be more suited than straight Python
code.


.. _trace_attributes: https://valhalla.readthedocs.io/en/latest/api/map-matching/api-reference/#outputs-of-trace_attributes

.. _Luigi: https://github.com/spotify/luigi

.. _tasks: https://luigi.readthedocs.io/en/stable/tasks.html
