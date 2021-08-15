import os
import json
import pickle
import tempfile
import logging
from glob import glob
from collections import defaultdict
from multiprocessing import Pool
from hashlib import sha256 as _hasher
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm
import luigi
from .. import (
    distance,
    rawfiles2jsonchunks,
    json2geojson,
    mongodoc2jsonchunks)
from ..settings import (
    DEBUG,
    DEBUG_DOC_LIMIT,
    RAW_PATH,
    OUT_PATH,
    SEQ_PATH,
    MONGO_CONNECTION_STRING,
    POSTGRES_CONNECTION_STRING,
    RAW_FROM_MONGO,
    VALHALLA_CONFIG_FILE,
    MIN_DISTANCE_BETWEEN_STOPS)
from ..models import Vehicle, Base, Stop, Trip, Traversal
from .._base_locator import EmptyCellsException

if RAW_FROM_MONGO:
    from ..mongo import (
        create_indexes,
        vehicle_ids,
        docs_for_vehicle,
        _init_db_connection as _init_mongo_db_connection)
else:
    def _init_mongo_db_connection(): pass



logger = logging.getLogger(__name__)



TMP_DIR = tempfile.gettempdir()
MONGO_VALUE = 'mongo'
NA_VALUE = 'NA'
POINT_KEYS = ('lat', 'lon', 'time', 'heading', 'speed', 'heading_tolerance')
EDGE_KEYS = ('id', 'speed', 'speed_limit')
EDGE_ATTR_NAMES = ('edge_id', 'valhalla_speed', 'speed_limit')
MM_KEYS = POINT_KEYS + ('status', 'trip_index') + EDGE_ATTR_NAMES + ('message',)
NAS = (NA_VALUE,) * len(EDGE_KEYS)



def hasher(rego):
    return _hasher(rego.encode('utf-8')).hexdigest()[:24]



def _getpointattrs(point):
    return tuple(point[k] for k in POINT_KEYS)



def _getedgeattrs(edge):
    return tuple(edge.get(k, NA_VALUE) for k in EDGE_KEYS)



def _run_valhalla(rego, trip, trip_index):
    tmp_file_in  = os.path.join(TMP_DIR, str(trip_index) + '_in_'  + rego)
    tmp_file_out = os.path.join(TMP_DIR, str(trip_index) + '_out_' + rego)

    try:
        with open(tmp_file_in, 'w') as jf:
            json.dump(trip, jf)

        os.system('valhalla_service {} trace_attributes {} 2>/dev/null > {}'.format(
            VALHALLA_CONFIG_FILE,
            tmp_file_in,
            tmp_file_out))

        with open(tmp_file_out, 'r') as rfile:
            return json.load(rfile)

    finally:
        try: os.remove(tmp_file_in)
        except: pass
        try: os.remove(tmp_file_out)
        except: pass



_engine = create_engine(POSTGRES_CONNECTION_STRING)
_session_maker = None
def _init_db_connections():
    # see: https://docs.sqlalchemy.org/en/13/core/pooling.html#pooling-multiprocessing
    global _engine, _session_maker
    _engine.dispose()
    _session_maker = sessionmaker(bind=_engine)
    _init_mongo_db_connection()

def write_to_db(vehicle, base, stops, trips, traversals):
    global _session_maker
    session = _session_maker()
    session.add(vehicle)
    session.add(base)
    for stop in stops:
        session.add(stop)
    for trip in trips:
        session.add(trip)
    for ts in traversals:
        for traversal in ts:
            session.add(traversal)
    session.commit()



def _average_speed(rego, results):
    df = pd.DataFrame({k:v for k, v in zip(MM_KEYS, r)} for r in results)
    df.drop(df[(df.status == 'failure') | (df.edge_id == NA_VALUE)].index, inplace=True)
    df.dropna(subset = ['edge_id'], inplace=True)

    if df.shape[0] == 0:
        return None

    df['edge_id'] = df['edge_id'].astype(np.uint64)

    # add date and hour
    dt = pd.to_datetime(df['time'], unit='s').dt
    df['hour']    = dt.hour
    df['weekDay'] = dt.weekday

    # average speed
    def ave_speed(df):
        # average for each trip
        tmp = df.groupby('trip_index').agg({'speed': ['mean', 'size']})

        # average for the edge_id/hour/weekDay
        return pd.Series({
            'speed' : np.average(tmp[('speed', 'mean')], weights=tmp[('speed', 'size')]),
            'weight': np.sum(tmp[('speed', 'size')])})

    #TODO: Do we want to check 'valhalla_speed' also/instead
    speed = df[df.speed > 6].groupby(
        ['edge_id', 'hour', 'weekDay']).apply(ave_speed).reset_index()

    if len(speed) != 0:
        speed["rego"] = rego
        return speed

    return None



def _process_trips(rego, trips, seq_file_name, vehicle, base):
    def run_trip(trip, trip_index):
        try:
            trip_data = {
                'trip_index': trip_index,
                'start': {
                    'time': int(trip['shape'][ 0]['time']),
                    'loc' : {
                        'lat': trip['shape'][ 0]['lat'],
                        'lon': trip['shape'][ 0]['lon']}},
                'end':   {
                    'time': int(trip['shape'][-1]['time']),
                    'loc': {
                        'lat': trip['shape'][-1]['lat'],
                        'lon': trip['shape'][-1]['lon']}}}

            try:
                snapped = _run_valhalla(rego, trip, trip_index)

            except:
                raise Exception('valhalla failure')

            # convert the output from Valhalla into our outputs (seq files).
            edges = snapped['edges']
            match_props = ((p.get('edge_index'), p['type']) for p in snapped['matched_points'])
            trip_data['geojson'] = json2geojson(snapped, True)
            trip_data['edge_to_osmids'] = {e['id']:e['osmids'] for e in edges}
            trip_data['way_ids'] = [e['way_id'] for e in edges]
            trip_data['status'] = 'success'

            return trip_data, [_getpointattrs(p) + \
                ('success', trip_index) + \
                (_getedgeattrs(edges[ei]) if ei is not None else NAS) + \
                (mt,) for p, (ei, mt) in zip(trip['shape'], match_props)]

        except Exception as e:
            e_str = '{}: {}'.format(e.__class__.__name__, str(e))
            trip_data['status'] = 'failure'
            trip_data['message'] = e_str
            return trip_data, [_getpointattrs(p) + \
                ('failure', trip_index) + \
                NAS + \
                (e_str,) for p in trip['shape']]

    try:
        with open(seq_file_name , 'w') as seqfile:

            def gen_stops(td1, td2, n_stationary):
                start_ll = (
                    td1['end']['loc']['lon'],
                    td1['end']['loc']['lat'])
                end_ll = (
                    td2['start']['loc']['lon'],
                    td2['start']['loc']['lat'])
                distance_between_start_and_end = distance(
                    start_ll[0], start_ll[1],
                    end_ll[0], end_ll[1])
                start_time = td1['end']['time']
                end_time   = td2['start']['time']

                return Stop(
                    vehicle = vehicle,
                    start_time = start_time,
                    end_time = end_time,
                    n_stationary = n_stationary,
                    start_end_dist = distance_between_start_and_end,
                    start_lon = start_ll[0],
                    start_lat = start_ll[1],
                    end_lon = end_ll[0],
                    end_lat = end_ll[1])

            def gen_trips(stop1, stop2):
                return Trip(
                    vehicle = vehicle,
                    start   = stop1,
                    end     = stop2)

            def gen_traversals(result, trip):
                speeds =  _average_speed(rego, result)
                if speeds is None:
                    return None

                return [Traversal(
                    vehicle = vehicle,
                    trip    = trip,
                    edge    = str(line['edge_id']),
                    hour    = line['hour'],
                    weekday = line['weekDay'],
                    speed   = line['speed'],
                    count   = line['weight']) for index, line in speeds.iterrows()]

            results = [(run_trip(trip, ti), n_stationary) for \
                    ti, (n_stationary, trip) in enumerate(trips)]

            n_stationary = [r[1] for r in results]
            results = [r[0] for r in results]
            # stops
            s0 = Stop(
                vehicle    = vehicle,
                end_time   = results[0][0]['start']['time'],
                end_lon    = results[0][0]['start']['loc']['lon'],
                end_lat    = results[0][0]['start']['loc']['lat'])
            sn = Stop(
                vehicle    = vehicle,
                start_time = results[-1][0]['end']['time'],
                start_lon  = results[-1][0]['end']['loc']['lon'],
                start_lat  = results[-1][0]['end']['loc']['lat'])
            stops  = [s0] + [gen_stops(td1[0], td2[0], ns) for td1, td2, ns in zip(
                results[:-1], results[1:], n_stationary[1:])] + [sn]

            # trips
            trips = [gen_trips(s1, s2) for s1, s2 in zip(
                stops[:-1], stops[1:])]

            # traversals
            traversals = [t for t in (gen_traversals(r[1], tr) for r, tr in zip(
                results, trips)) if t is not None]

            write_to_db(vehicle, base, stops, trips, traversals)
            json.dump([r[0] for r in results], seqfile)

    except Exception as e:
        logger.exception('processing {} failed...'.format(rego))

    else:
        logger.debug('processing {} passed'.format(rego))



def _process_files(fns):
    fn          = fns[0]
    input_files = fns[1]

    if isinstance(input_files, str):
        if input_files == MONGO_VALUE:
            rego = hasher(fn)
        else:
            assert(fn.endswith('.csv'))
            rego = os.path.splitext(fn)[0]
    else:
        rego = os.path.splitext(fn)[0]

    seq_file_name = os.path.join(SEQ_PATH, '{}.json'.format(rego))

    if os.path.exists(seq_file_name):
        logger.debug('skipping: {} (done)'.format(rego))
        return

    # Can't do this in the block above if we want to check that we must proceed
    # first.
    try:
        if isinstance(input_files, str) and input_files == MONGO_VALUE:
            doc = docs_for_vehicle(fn)
            base, trips = mongodoc2jsonchunks(doc, True)
        else:
            base, trips = rawfiles2jsonchunks(input_files, True)

        vehicle = Vehicle(rego = rego)
        base = Base(vehicle = vehicle, lon=base[0], lat=base[1])

        _process_trips(rego, trips, seq_file_name, vehicle, base)

    except EmptyCellsException as e:
        logger.warning('failed to locate base ({}) for: {}'.format(
            str(e), rego))



#-------------------------------------------------------------------------------
# Luigi tasks
#-------------------------------------------------------------------------------
class ListRawFiles(luigi.Task):
    """Gather information about input files."""

    pickle_file_name = os.path.join(OUT_PATH, 'raw_files.pkl')

    def run(self):
        """:meta private:"""
        if RAW_FROM_MONGO:
            limit = DEBUG_DOC_LIMIT if DEBUG else None
            input_files = {v: MONGO_VALUE for v in vehicle_ids(limit)}

        else:
            input_files = defaultdict(list)
            for root, dirs, files in os.walk(RAW_PATH):
                for f in files:
                    input_files[f].append(os.path.join(root, f))

        with open(self.output().fn, 'wb') as pf:
            pickle.dump(input_files, pf)

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(self.pickle_file_name)



class MatchToNetwork(luigi.Task):
    """Match trips to the network."""

    pickle_file_name = os.path.join(OUT_PATH, 'seq_files.pkl')

    def requires(self):
        """:meta private:"""
        return ListRawFiles()

    def run(self):
        """:meta private:"""

        # first, ensure that mongo tables have indexes
        if RAW_FROM_MONGO:
            create_indexes()

        # load the input file data
        with open(self.input().fn, 'rb') as input_files_file:
            input_files = pickle.load(input_files_file)

        # do the jobby
        with Pool(initializer = _init_db_connections) as workers:
            work = workers.imap_unordered(_process_files, input_files.items())
            # wrap in list so we wait for jobby to finish.
            list(tqdm(work, total=len(input_files)))

        # list the (seq) output files
        seq_output_files = glob(os.path.join(SEQ_PATH, '*'))
        with open(self.output().fn, 'wb') as pf:
            pickle.dump(seq_output_files, pf)

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(self.pickle_file_name)
