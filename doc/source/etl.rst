**************
Data ingestion
**************

The raw data provided by HANEL comes in a format that is inadequate for most, if not all, analytics tasks performed
with the data. For this reason,  processing the data into a format apropriate for our use is the first step in the
generation of any analytical outputs.

This process is commonly known as `Extract, Transform & Load <https://en.wikipedia.org/wiki/Extract,_transform,_load>`_
and can (should) be designed with the analytics use cases in mind. However, there is absolutely no need to run this
process more than once on the raw data

.. _hanel_data:

HANEL's raw data
================

The data received

::

    vehicle,datetime,speed,x,y,heading,VehicleType
    bOGJIXjzWD29JY24y3gT/g==,1585780315,10.0,106.63020324707031,10.768750190734863,181.1,Xe chưa phân loại
    jKYkHRwBCATrWl4DkdWKFg==,1585780321,41.0,106.79299926757812,10.86571979522705,130.0,Xe chưa phân loại
    LtonCPx/mO94YI9Kilaslg==,1585766618,44.0,105.91528,21.0087483333,38.0,Xe chưa phân loại
    r9uDV7PxFpDQCxafwlWM4Q==,1585780310,0.0,106.88480377197266,10.93822956085205,226.5,Xe chưa phân loại
    sERvntCTgLHdiG4PVypveA==,1585780318,0.0,106.80950164794922,10.780980110168457,338.6,Xe chưa phân loại
    dS3IR9PjBoe3TXfTXM0g3Q==,1585776052,0.0,105.819625,10.134875,296.0,Xe chưa phân loại
    nsqu7D3lW41PTR5h3syr+g==,1585780336,44.0,106.11979675292969,20.91621971130371,78.5,Xe chưa phân loại
    n3sdB/si5JemE8XMifymLA==,1585766618,0.0,105.2251966667,21.1300333333,272.0,Xe chưa phân loại


.. _backup:

Backup
======

Since the process of obtaining data from HANEL was expensive and time-consuming, it was reasonable to
safeguard our processes by backing up the raw data received in a format closest to the original so we
could begin the processing from scratch at any point in time.

Backing up the data in its original CSV format would require an unreasonable amount of disk space, so
we did a little investigation on different formats we could use for such task, for which the results
are shown below.

All these tests were done with Pandas, as it provides a simple interface for loading the original CSV
and saving in all of these formats and the times are for converting a single 10 million row CSV.

.. image:: images/compression.png
    :width: 960
    :alt: Compression performance

All all these formats, Zip, GZ and BZ2 are dominated by other alternatives, and therefore were discarded
from further consideration.  Feather provided amazing compression speed (~1.5s), but the level of
compression was too low, at about 42% of the original size.

On the other end of the spectrum, LZMA was able to compress the data to roughly 12% of its original size,
but took in excess of 800 seconds to do so, which would require over a day of processing time to compress
one day of data (single threaded).

We have then settled on using Parquet with Brotli compression, which was able to compress the data to
just under 20% of its original size (19.7%), doing that in about 33s.


.. _etl:

Extract, Load & Transform
=========================

.. _daily_processing:
Separating traces per vehicle
-----------------------------

.. _monthly_processing:
Monthly data
------------


Reference database
==================


