*******
Outputs
*******

Outputs are created under the directory specified by :py:data:`cvts.settings.OUT_DIR`.



.. _map-matching-output:

Map Matching Outputs
====================

Directory specified by :py:data:`cvts.settings.MM_PATH`.

Contains a CSV for each vehicle. An example of the contents of each CSV is::

    lat,lon,time,heading,speed,heading_tolerance,status,trip_index,way_id,valhalla_speed,speed_limit,message
    10.862250328064,106.928115844727,1501545600.0,180.0,0.0,45,success,0,829395784,20,NA,matched
    10.8622531890869,106.928123474121,1501545727.0,180.0,0.0,45,success,0,829395784,20,NA,interpolated
    10.8622550964355,106.928123474121,1501546327.0,180.0,0.0,45,success,0,829395784,20,NA,interpolated
    ...

Each row corresponds to an input point, and all input points are included.
**Note that the order of the points may not correspond to the order of points
in the input files.**

The fields are:

* *lat*: Latitude of the point (from the GPS trace).

* *lon*: Longitude of the point (from the GPS trace).

* *time*: Timestamp of the point (from the GPS trace).

* *speed*: Speed at the point (from the GPS trace).

* *heading*: Heading at the point (from the GPS trace).

* *heading_tolerance*: Heading tolerance specified for the point. This is
  specified by our software and used internally by Valhalla for calculating
  costs when doing the matching.

* *status*: One of "success" or "failure", denoting whether matching succeeded
  or failed for the point.

* *trip_index*: Index of the trip, which is just a counter (starting at zero)
  which is indexed for every trip (produced by our code).

* *way_id*: Identifier of the way Valhalla matched the point to.

* *valhalla_speed*: Speed reported by Valhalla.

* *speed_limit*: Speed limit on the way reported by Valhalla.

* *message*: Either the match type returned by Valhalla, or an error message
  (the result of `str(e)`, where `e` is the exception thrown in the case where
  *status* is "failure".



.. _trip-output:

Trips
=====

Directory specified by :py:data:`cvts.settings.SEQ_PATH`.

JSON data for each vehicle. The JSON data contains a list of dicts, one for
each trip. Each dict contains:

* *STatus*: "success" if Valhalla succeeded for this trip or "failure" if
  it did not.

* *trip\_index*: Index of the trip.

* *start*:

    * *time*: Timestamp of the point at which the trip started.
    * *loc*:
        * *lat*: Latitude of the point at which the trip started.
        * *lon*: Longitude of the point at which the trip started.

* *way\_ids*: List of way ids of the trip as produced by Valhalla. Only
  present if *status* is "success"

* *geojson*: A GeoJSON representation of the trip (produced by
  *cvts.json2geojson*). Only present if *status* is "success"

* *message*: An error message. The result of `str(e)`, where `e` is the
  exception thrown in the case where *status* is "failure". Only present
  when *status* is "failure".



.. _speed-output:

Average Speeds
==============

Directory specified by :py:data:`cvts.settings.SPEED_PATH`.

For each vehicle, there are two files:

* **\<vehicle-id\>-moving.csv**: Contains the proportion of observations
  where the vehicle with id *vehicle-id* is considered to be moving by hour,
  weekday and way ID (*propMoving*). Example content::

      way_id,hour,weekDay,propMoving,rego
      0,1,0.07692307692307693,11C00211
      1,1,0.0,11C00211
      2,1,0.04938271604938271,11C00211
      ...

* **\<vehicle-id\>-speed.csv**: Contains the average speed of the vehicle
  with id *vehicle-id* over all observations where the vehicle is is
  considered to be moving by hour, weekday and way ID (*speed*). Each observation
  includes a weight describing the number of observations included in the
  average. Example content::

      way_id,hour,weekDay,speed,weight,rego
      135742765,7,3,22.8,15.0,11C00211
      135742765,8,3,23.0,12.0,11C00211
      135742765,11,3,27.88888888888889,18.0,11C00211
      ...



.. _stop-dest-output:

Source Destination
==================

Directory specified by :py:data:`cvts.settings.SRC_DEST_PATH`.

Source/destination lon/lats. Each (JSON) file contains a list
of lists. Each of which is the lon/lat of a stop point corresponding to
either a trips start point, or the trips end point. The even numbered rows
correspond to source points, and the odd numbered rows correspond to
destination points



.. _stop-points-output:

Stops
=====

Directory specified by :py:data:`cvts.settings.STOP_PATH`.

Stop points lon/lats. Each (JSON) file contains a list of lists.
Each of which is a stop point.
