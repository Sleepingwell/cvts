#!/usr/bin/env python3

import os
import json
import pickle
from multiprocessing import Pool
from functools import partial
from datetime import timezone, timedelta
from math import floor, ceil
import numpy as np
from tqdm import tqdm
import luigi
from .. import (
    read_shapefile,
    points_to_polys,
    distance)
from ..settings import (
    OUT_PATH,
    STOP_PATH,
    SRC_DEST_PATH,
    BOUNDARIES_PATH)
from ._valhalla import MatchToNetwork



_geom_fields_map_path = os.path.join(
    BOUNDARIES_PATH,
    'geography-geom-field-names.json')

if os.path.exists(_geom_fields_map_path):
    with open(_geom_fields_map_path, 'r') as f:
        GEOM_ID_COLUMN = json.load(f)
else:
    GEOM_ID_COLUMN = {}

#: Distance in meters between two points for them to be considered itdentical
#: with respect to the end of one trip and the beginning of the next.
MAGIC_DISTANCE = 50

#: Timezone for Vietnam.
TZ             = timezone(timedelta(hours=7), 'ITC')

#: Minimum latitude of the raster 'covering' Vietnam.
MINLAT   =   7.8584

#: Approximate maximum latitude of the raster 'covering' Vietnam.
MAXLAT   =  23.8882

#: Minimum latitude of the raster 'covering' Vietnam.
MINLON   = 101.9988

#: Approximate maximum longitude of the raster 'covering' Vietnam.
MAXLON   = 109.3325

#: Cellsize of the raster 'covering' Vietnam.
CELLSIZE =   0.1

#: NA value to use for the raster 'covering' Vietnam.
NA_VALUE = -9999

STOP_POINTS_LON_LAT_FILE             = 'stop_points_lon_lat.pkl'
STOP_POINTS_GEOM_IDS_FILE            = 'stop_points_geom_ids.pkl'
STOP_POINTS_GEOM_COUNTS_FILE         = 'stop_points_geom_counts.pkl'
STOP_POINTS_GEOM_COUNTS_CSV_FILE     = 'stop_points_geom_counts.csv'

SRC_DEST_POINTS_LON_LAT_FILE         = 'src_dest_points_lon_lat.pkl'
SRC_DEST_POINTS_GEOM_IDS_FILE        = 'src_dest_points_geom_ids.pkl'
SRC_DEST_POINTS_GEOM_COUNTS_FILE     = 'src_dest_points_geom_counts.pkl'
SRC_DEST_POINTS_GEOM_COUNTS_CSV_FILE = 'src_dest_points_geom_counts.csv'



class _Grid:
    """Raster used for accumulating stop points."""

    def __init__(
            self,
            minlat   = MINLAT,
            minlon   = MINLON,
            maxlat   = MAXLAT,
            maxlon   = MAXLON,
            cellsize = CELLSIZE,
            na_value = NA_VALUE):
        self.minlat = minlat
        self.minlon = minlon
        self.cellsize = cellsize
        self.na_value = na_value
        self.ncol = int(ceil((maxlon - self.minlon) / self.cellsize))
        self.nrow = int(ceil((maxlat - self.minlat) / self.cellsize))
        self.cells = np.zeros((self.nrow, self.ncol), int)

    def increment(self, lon, lat):
        """Increment the count in cell containing the point (*lon*, *lat*)."""
        row = self.nrow - int(floor((lon - self.minlon) / self.cellsize)) - 1
        col =             int(floor((lat - self.minlat) / self.cellsize))
        if 0 <= col < self.ncol and 0 <= row < self.nrow:
            self.cells[row, col] += 1
        # TODO: warning here?

    def save(self, fn):
        """Save as ASCII grid."""
        with open(fn, 'w') as f:
            f.write('ncols        {}\n'.format(self.ncol))
            f.write('nrows        {}\n'.format(self.nrow))
            f.write('xllcorner    {}\n'.format(self.minlon))
            f.write('yllcorner    {}\n'.format(self.minlat))
            f.write('cellsize     {}\n'.format(self.cellsize))
            f.write('NODATA_value {}\n'.format(self.na_value))
            f.write(' '.join([str(i) for i in self.cells.flatten()]))



def _ends(end, start):
    """Generator over stop points at the intersection of two trips.

    Given trips, use just one point if the end of the first trip is close enough
    to the beginning of the next trip, otherwise, use both the end of the first
    trip and the start of the second trip.

    Not sure why we would ever see the start of the second trip not be at the
    same location as the end of the first trip; my guess this implies some sort
    of missing data.
    """

    x1, y1 = start['lon'], start['lat']
    x0, y0 =   end['lon'],     end['lat']
    d = distance(x0, y0, x1, y1)
    yield x0, y0
    if d > MAGIC_DISTANCE:
        yield x1, y1

def _do_stops(filename):
    """Generator over the stop points for all trips taken by a vehicle.

    See :py:func:`_ends` for how the end/start of successive trips is handled.
    """
    rego = os.path.splitext(os.path.basename(filename))[0]

    with open(filename) as fin:
        stops = json.load(fin)

    stopiter = iter(stops)
    try:
        t0 = next(stopiter)
    except StopIteration:
        return
    p0 = t0['start']['loc']
    yield p0['lon'], p0['lat']
    for t1 in stopiter:
        for e in _ends(t0['end']['loc'], t1['start']['loc']):
            yield e
        t0 = t1
    p0 = t0['start']['loc']
    p1 = t0['end']['loc']
    if distance(p0['lon'], p0['lat'], p1['lon'], p1['lat']) > MAGIC_DISTANCE:
        yield p1['lon'], p1['lat']

def _do_source_dest(filename):
    """Generator over the source/dest points for a trip."""
    with open(filename) as fin:
        trips = json.load(fin)

    for trip in trips:
        loc = trip['start']['loc']
        yield loc['lon'], loc['lat']
        loc = trip['end']['loc']
        yield loc['lon'], loc['lat']

def _trip_iter(doer, out_path, filename):
    """Iterates over all trips for a vehicle."""
    out = [t for t in doer(filename)]
    out_file_name = os.path.join(out_path, os.path.basename(filename))
    with open(out_file_name, 'w') as out_file:
        json.dump(out, out_file)
    return np.array(out)

_stops = partial(_trip_iter, _do_stops, STOP_PATH)
_source_dests = partial(_trip_iter, _do_source_dest, SRC_DEST_PATH)



def _name_to_name_with_geom(name, geog_name, out_dir=OUT_PATH):
    rego, ext = os.path.splitext(name)
    return os.path.join(
        out_dir,
        '{}_{}{}'.format(rego, geog_name, ext))

#-------------------------------------------------------------------------------
# Luigi tasks
#-------------------------------------------------------------------------------
class _LocationPoints(luigi.Task):
    """Collects points for all trips of all vehicles."""

    #: The name of the file, relative to :data:`cvts.settings.OUT_PATH`, to save the list
    #: files generated by this task in.
    pickle_file_basename = luigi.Parameter()

    #: A callable that will be passed the name of a file containing the trips
    #: for a vehicle, and must return a list of lists of lon/lat pairs.
    point_extractor      = luigi.Parameter()

    @property
    def pickle_file_name(self):
        """The full path of the (pickle) file in which to save the list of
        files created by this task.
        """
        return os.path.join(OUT_PATH, self.pickle_file_basename)

    def requires(self):
        return MatchToNetwork()

    def run(self):
        """:meta private:"""
        with open(self.input()['seq'].fn, 'rb') as seq_files_file:
            all_seq_files = pickle.load(seq_files_file)

        with Pool() as p:
            workers = p.imap_unordered(self.point_extractor, all_seq_files)
            pnts = tqdm(workers, total=len(all_seq_files))
            stop_points = np.vstack([p for p in pnts if len(p) > 0])

        with open(self.output().fn, 'wb') as of:
            pickle.dump(stop_points, of)

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(self.pickle_file_name)



class _PointsToRegions(luigi.Task):
    """Maps a list of lon/lat pairs to polygons in a :term:`geography`."""

    #: A callable that will be passed the name of a file containing the trips
    #: for a vehicle, and must return a list of lists of lon/lat pairs.
    point_extractor            = luigi.Parameter()

    #: The name of the :term:`geography`. This must correspond to a shape file
    #: located in :data:`BOUNDARIES_PATH`.
    geometries_name            = luigi.Parameter()

    #: The name of the file, relative to :data:`cvts.settings.OUT_PATH`, to load a list
    #: of lists of lon/lat pairs.
    input_pickle_file_basename = luigi.Parameter()

    #: The name of the file, relative to :data:`cvts.settings.OUT_PATH`, to save the list
    #: files generated by this task in.
    pickle_file_basename       = luigi.Parameter()

    @property
    def pickle_file_name(self):
        return _name_to_name_with_geom(
            self.pickle_file_basename,
            self.geometries_name)

    def requires(self):
        return _LocationPoints(
            self.input_pickle_file_basename,
            self.point_extractor)

    def run(self):
        """:meta private:"""
        # load the geometries
        polys = read_shapefile(
            os.path.join(BOUNDARIES_PATH, self.geometries_name + '.shp'),
            GEOM_ID_COLUMN[self.geometries_name])

        # load the stop points
        with open(self.input().fn, 'rb') as inf:
            stop_points = pickle.load(inf)

        # map the points to the polygons and save
        poly_points = points_to_polys(stop_points, polys)
        with open(self.output().fn, 'wb') as of:
            pickle.dump(poly_points, of)

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(self.pickle_file_name)



class _CountsTask(luigi.Task):

    #: The name of the :term:`geography`. This must correspond to a shape file
    #: located in :data:`BOUNDARIES_PATH`.
    geometries_name  = luigi.Parameter()

    @property
    def pickle_file_name(self):
        """The full path of the (pickle) file in which to save the list of
        files created by this task.
        """
        return _name_to_name_with_geom(
            self.pickle_file_basename,
            self.geometries_name)

    @property
    def csv_file_name(self):
        """The full path of the (CSV) file in which to save the list of
        files created by this task.
        """
        return _name_to_name_with_geom(
            self.csv_file_basename,
            self.geometries_name)

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(self.pickle_file_name)



class RegionCounts(_CountsTask):
    """Counts the number of stop points in each region."""

    #: The name of the (pickle) file, relative to :data:`cvts.settings.OUT_PATH`, to save
    #: the table of counts of stop points by region in.
    pickle_file_basename = STOP_POINTS_GEOM_COUNTS_FILE

    #: The name of the (CSV) file, relative to :data:`cvts.settings.OUT_PATH`, to save
    #: the table of counts of stop points by region in.
    csv_file_basename    = STOP_POINTS_GEOM_COUNTS_CSV_FILE

    def requires(self):
        """:meta private:"""
        return _PointsToRegions(
            _stops,
            self.geometries_name,
            STOP_POINTS_LON_LAT_FILE,
            STOP_POINTS_GEOM_IDS_FILE)

    def run(self):
        """:meta private:"""
        # get the counts in each region
        with open(self.input().fn, 'rb') as pf:
            poly_points = pickle.load(pf)
            vcs = np.unique(poly_points, return_counts=True)

        # write them to a pickle
        with open(self.output().fn, 'wb') as of:
            pickle.dump(vcs, of)

        # and write them to a CSV
        with open(self.csv_file_name, 'w') as of:
            of.write('{},count\n'.format('geom_id'))
            for vc in zip(*vcs):
                of.write('{},{}\n'.format(*vc))



class SourceDestinationCounts(_CountsTask):
    """Counts the number of stop points in each region."""

    #: The name of the (pickle) file, relative to :data:`cvts.settings.OUT_PATH`, to save
    #: the table of counts of source/destination counts by region pairs in.
    pickle_file_basename = SRC_DEST_POINTS_GEOM_COUNTS_FILE

    #: The name of the (CSV) file, relative to :data:`cvts.settings.OUT_PATH`, to save
    #: the table of counts of source/destination counts by region in.
    csv_file_basename    = SRC_DEST_POINTS_GEOM_COUNTS_CSV_FILE

    def requires(self):
        """:meta private:"""
        return _PointsToRegions(
            _source_dests,
            self.geometries_name,
            SRC_DEST_POINTS_LON_LAT_FILE,
            SRC_DEST_POINTS_GEOM_IDS_FILE)

    def run(self):
        """:meta private:"""
        with open(self.input().fn, 'rb') as pf:
            gids  = pickle.load(pf)

            froms = gids[0::2]
            tos   = gids[1::2]

            ids   = np.array(['{}-{}'.format(*ft) for ft in zip(froms, tos)])
            _, indices, counts = np.unique(
                ids,
                return_index  = True,
                return_counts = True)

            froms = froms[indices]
            tos   =   tos[indices]

        # write them to a pickle
        with open(self.output().fn, 'wb') as of:
            pickle.dump((froms, tos, counts), of)

        # and write them to a CSV
        with open(self.csv_file_name, 'w') as of:
            of.write('from,to,count\n')
            for trip in zip(froms, tos, counts):
                of.write('{},{},{}\n'.format(*trip))



class RasterCounts(luigi.Task):
    """Counts the number of stop points in each cell of a raster."""

    ascii_grid_file_name = os.path.join(OUT_PATH, 'grid_points.asc')

    def requires(self):
        """:meta private:"""
        return _LocationPoints(STOP_POINTS_LON_LAT_FILE, _stops)

    def run(self):
        """:meta private:"""
        # load the stop points
        with open(self.input().fn, 'rb') as inf:
            stop_points = pickle.load(inf)

        # construct and save the grid counts
        grid = _Grid()
        for p in stop_points:
            grid.increment(*p)
        grid.save(self.output().fn)

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(self.ascii_grid_file_name)
