import csv
import json
from math import sqrt, radians, cos
from typing import Dict, Any, Generator, Union, Iterable
from functools import reduce as reduce
from ._polyline import decode
from .settings import (
    MIN_STOP_TIME,
    MIN_MOVING_SPEED,
    MIN_MOVE_DISTANCE,
    EARTH_RADIUS)



def distance(x0, y0, x1, y1):
    """Quick and adequate distance calculation for for small distances in meters
    between two lon/lats.

    This should be adequate for the purpose of measuring points between points
    in the kinds of GPS traces we are working with, where the typical sampling
    interval is around 15 seconds (i.e., differences in latitude between *y0*
    and *y1* are (very) small).

    :param float x0: First longitude.
    :param float y0: First latitude.
    :param float x1: Second longitude.
    :param float y1: Second latitude.

    :return: Approximate distance between the two points in meters.
    """

    yd = radians(y1 - y0)
    xd = radians(x1 - x0) * cos(radians(y0) + .5*yd)
    return EARTH_RADIUS * sqrt(yd*yd + xd*xd)



def _trip_slices(locs):
    """Generator over sequential slices of *locs* that form trips."""

    if len(locs) == 0:
        yield slice(0, 0)

    else:
        getter = lambda l: (l['time'], l['speed'], l['lat'], l['lon'])
        zi = enumerate(getter(l) for l in locs)
        li, (last_moved_time, _, ly, lx) = next(zi)
        last_point_time = last_moved_time
        i = li

        for i, (t, s, y, x) in zi:
            has_moved = s > MIN_MOVING_SPEED or distance(lx, ly, x, y) > MIN_MOVE_DISTANCE

            if has_moved:
                if t - last_moved_time > MIN_STOP_TIME:
                    if t - last_point_time <= MIN_STOP_TIME:
                        yield slice(li, i-1)
                        li = i-1
                    else:
                        yield slice(li, i)
                        li = i
                lx, ly, last_moved_time = x, y, t

            last_point_time = t

        # TODO: Should we be doing this only when vehicle has moved?
        yield slice(li, i+1)



def _loadcsv(csvfile):
    """Load a raw GeoJSON file and start preparing it for input into Valhalla
    (preparation is finalissed in :py:func:`_prepjson`)."""

    with open(csvfile, 'r') as cf:
        reader = csv.DictReader(cf)
        return [{
            # yes, Longitude and Latitude are back to front.
            'lat': float(row['Longitude']),
            'lon': float(row['Latitude']),
            'time': float(row['Time']),
            'heading': float(row['Orientation']),
            'speed': float(row['speed']),
            'heading_tolerance': 45,
            'type': 'via'} for row in reader]



def _prepjson(locs, split_trips):
    """Finish preparing data for input into Valhalla and return the results as a
    generator over trip(s)."""

    locs.sort(key=lambda l: l['time'])
    if split_trips:
        for split in _trip_slices(locs):
            clocs = locs[split]
            if len(clocs) == 0:
                continue
            clocs[0]['type'] = 'break'
            clocs[-1]['type'] = 'break'
            yield {'shape': clocs, 'costing': 'auto', 'shape_match': 'map_snap'}
    else:
        locs[0]['type'] = 'break'
        locs[-1]['type'] = 'break'
        yield {'shape': locs, 'costing': 'auto', 'shape_match': 'map_snap'}



def mongodoc2jsonchunks(
        doc: Dict[str, Any],
        split_trips: bool) -> Generator[Dict[str, Any], None, None]:
    """Create a generator over all the data for a single vehicle from data in a
    CSV or iterable of CSVs.

    :param doc: A document containing all the documents (each containing a
        GPS point) for a vehicle.

    :param split_trips: if `True`, then split into :term:`trips<trip>`,
        otherwise return all points as a single 'trip'.

    :return: A geenerator over a dicts that contain information about each GPS
        point. Each dict looks like::

            {
                'lat':     doc['y'],
                'lon':     doc['x'],
                'time':    doc['datetime'],
                'heading': doc['heading'],
                'speed':   doc['speed'],
                'heading_tolerance': 45,
                'type':    'via'
            }
    """

    raw_locs = [{
        'lat': d['y'],
        'lon': d['x'],
        'time': d['datetime'],
        'heading': d['heading'],
        'speed': d['speed'],
        'heading_tolerance': 45,
        'type': 'via'} for d in doc]

    return _prepjson(raw_locs, split_trips)



def rawfiles2jsonchunks(
        csv_file: Union[str, Iterable[str]],
        split_trips: bool) -> Generator[Dict[str, Any], None, None]:
    """Create a generator over all the data for a single vehicle from data in a
    csv or iterable of csvs.

    :param csv_file: Either the name of a
        :ref:`GPS data<gps-data>` file or an iterable of names of such files.

    :param split_trips: if `True`, then split into :term:`trips<trip>`,
        otherwise return all points as a single 'trip'.

    :return: A geenerator over a dicts that contain information about each GPS
        point. Each dict looks like::

            {
                'lat':     float(row['Longitude']),
                'lon':     float(row['Latitude']),
                'time':    float(row['Time']),
                'heading': float(row['Orientation']),
                'speed':   float(row['speed']),
                'heading_tolerance': 45,
                'type':    'via'
            }
    """

    raw_locs = _loadcsv(csv_file) \
        if isinstance(csv_file, str) \
        else reduce(lambda a, b: a + _loadcsv(b), csv_file, [])
    return _prepjson(raw_locs, split_trips)



def rawfiles2jsonfile(
        csv_file: Union[str, Iterable[str]],
        out_file: str):
    """Call :py:func:`rawfiles2jsonchunks`, passing *csv_files* and *False*, and
    write the result to *out_file*.

    :param csv_file: Either the name of a
        :ref:`GPS data<gps-data>` file or an iterable of names of such files.

    :param out_file: The path of the file to write the trip to.
    """

    chunks = rawfiles2jsonchunks(csv_file, False)
    with open(out_file, 'w') as jf:
        json.dump(next(chunks), jf, indent=4)



def json2geojson(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert the output from Valhalla to a GeoJSON object.

    On the command line, the call would look like::


        valhalla_service <config-file> trace_attributes <input-file>

    :param data: Output of a call to Valhalla (as described above).

    :return: TODO
    """

    edges = data['edges']

    def _point_feature(matched_point, index):
        lat = matched_point.pop('lat')
        lon = matched_point.pop('lon')

        edge_index = matched_point.get('edge_index')
        matched_point['point_index'] = index
        if edge_index is not None:
            names = ', '.join(edges[edge_index].get("names", ["NA"]))
            matched_point['osname'] = names
            matched_point['way_id'] = edges[edge_index].get("way_id", "NA")

        return {
            'type': 'Feature',
            'properties': matched_point,
            'geometry': {
                'type': 'Point',
                'coordinates': [lon, lat]}}

    shape = [{
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': [[p[0]/10., p[1]/10.] for p in decode(data['shape'])]}}]

    return {
        'type': 'FeatureCollection',
        'features': [_point_feature(mp, i) for i, mp in enumerate(data['matched_points'])] + shape}



def jsonfile2geojsonfile(infile, outfile):
    with open(infile, 'r') as jf, open(outfile, 'w') as gf:
        json.dump(json2geojson(json.load(jf)), gf, indent=4)
