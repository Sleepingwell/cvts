import os
import json
import pickle
from multiprocessing import Pool
from functools import partial as _partial
from datetime import timezone, timedelta
import logging
import numpy as np
from tqdm import tqdm
import luigi
from .. import (
    read_shapefile,
    points_to_polys,
    distance)
from .._grid import Grid
from ..settings import (
    OUT_PATH,
    STOP_PATH,
    SRC_DEST_PATH,
    BOUNDARIES_PATH)
from ._valhalla import MatchToNetwork

logger = logging.getLogger(__name__)

# contains a dicionary mapping geography names to the name of the geometry id
# column in the attribute table.
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

POINTS_GEOM_IDS_FILE_POSTFIX        = 'points_geom_ids.pkl'
POINTS_LON_LAT_FILE_POSTFIX         = 'points_lon_lat.pkl'
POINTS_GEOM_COUNTS_FILE_POSTFIX     = 'points_geom_counts.pkl'
POINTS_GEOM_COUNTS_CSV_FILE_POSTFIX = 'points_geom_counts.csv'



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

def partial(doer, pth, nm):
    res = _partial(_trip_iter, doer, pth)
    res.__name__ = nm
    return res

_stops = partial(_do_stops, STOP_PATH, 'stop')
_source_dests = partial(_do_source_dest, SRC_DEST_PATH, 'src_dest')



def _name_to_name_with_geom(metric_name, geog_name, postfix):
    return os.path.join(
        OUT_PATH,
        '{}_{}_{}'.format(metric_name, geog_name, postfix))

#-------------------------------------------------------------------------------
# Luigi tasks
#-------------------------------------------------------------------------------
class _LocationPoints(luigi.Task):
    """Collects points for all trips of all vehicles."""

    #: A callable that will be passed the name of a file containing the trips
    #: for a vehicle, and must return a list of lists of lon/lat pairs. This
    #: must have an attribute *__name__*, which will be used for
    #: naming output files.
    point_extractor      = luigi.Parameter()

    @property
    def pickle_file_name(self):
        """The full path of the (pickle) file in which to save the list of
        files created by this task.
        """
        return os.path.join(
            OUT_PATH,
            '{}_{}'.format(
                self.point_extractor.__name__,
                POINTS_LON_LAT_FILE_POSTFIX))

    def requires(self):
        return MatchToNetwork()

    def run(self):
        """:meta private:"""
        with open(self.input()['seq'].fn, 'rb') as sf:
            all_seq_files = pickle.load(sf)

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
    point_extractor = luigi.Parameter()

    #: The name of the :term:`geography`. This must correspond to a shape file
    #: located in :data:`BOUNDARIES_PATH`.
    geometries_name = luigi.Parameter()

    @property
    def pickle_file_name(self):
        return _name_to_name_with_geom(
            self.point_extractor.__name__,
            self.geometries_name,
            POINTS_GEOM_IDS_FILE_POSTFIX)

    def requires(self):
        return _LocationPoints(self.point_extractor)

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
            self.METRIC.__name__, # METRIC must be defined on base classes.
            self.geometries_name,
            POINTS_GEOM_COUNTS_FILE_POSTFIX)

    @property
    def csv_file_name(self):
        """The full path of the (CSV) file in which to save the list of
        files created by this task.
        """
        return _name_to_name_with_geom(
            self.METRIC.__name__, # METRIC must be defined on base classes.
            self.geometries_name,
            POINTS_GEOM_COUNTS_CSV_FILE_POSTFIX)

    def requires(self):
        """:meta private:"""
        return _PointsToRegions(self.METRIC, self.geometries_name)

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(self.pickle_file_name)



class RegionCounts(_CountsTask):
    """Counts the number of stop points in each region."""

    #: The name of the metric we are using.
    METRIC = _stops

    def run(self):
        """:meta private:"""
        # get the counts in each region
        with open(self.input().fn, 'rb') as pf:
            poly_points = pickle.load(pf)
            vcs = np.unique(poly_points, return_counts=True)

        # and write them to a CSV
        with open(self.csv_file_name, 'w') as of:
            of.write('{},count\n'.format('geom_id'))
            for vc in zip(*vcs):
                of.write('{},{}\n'.format(*vc))

        # write them to a pickle
        with open(self.output().fn, 'wb') as of:
            pickle.dump(vcs, of)



class SourceDestinationCounts(_CountsTask):
    """Counts the number of stop points in each region."""

    #: The name of the metric we are using.
    METRIC = _source_dests

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

    ASCII_GRID_FILE_NAME = os.path.join(OUT_PATH, 'grid_points.asc')

    def requires(self):
        """:meta private:"""
        return _LocationPoints(_stops)

    def run(self):
        """:meta private:"""
        # load the stop points
        with open(self.input().fn, 'rb') as inf:
            stop_points = pickle.load(inf)

        # construct and save the grid counts
        grid = Grid()
        for p in stop_points:
            grid.increment(*p)
        grid.save(self.output().fn)

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(self.ASCII_GRID_FILE_NAME)
