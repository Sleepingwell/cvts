import os
import json
import pickle
import tempfile
import logging
from glob import glob
from collections import defaultdict
from multiprocessing import Pool
from hashlib import sha256 as _hasher
from tqdm import tqdm
import luigi
from .. import (
    rawfiles2jsonchunks,
    json2geojson,
    mongodoc2jsonchunks)
from ..settings import (
    DEBUG,
    DEBUG_DOC_LIMIT,
    RAW_PATH,
    OUT_PATH,
    MM_PATH,
    SEQ_PATH,
    MONGO_CONNECTION_STRING,
    RAW_FROM_MONGO,
    VALHALLA_CONFIG_FILE)

if RAW_FROM_MONGO:
    from ..mongo import (
        vehicle_ids,
        docs_for_vehicle,
        _init_db_connection)
else:
    def _init_db_connection(): pass



logger = logging.getLogger(__name__)



MONGO_VALUE = 'mongo'
POINT_KEYS = ('lat', 'lon', 'time', 'heading', 'speed', 'heading_tolerance')
TMP_DIR = tempfile.gettempdir()
EDGE_KEYS = ('way_id', 'speed', 'speed_limit')
EDGE_ATTR_NAMES = ('way_id', 'valhalla_speed', 'speed_limit')
NAS = ('NA',) * len(EDGE_KEYS)



def hasher(rego):
    return _hasher(rego.encode('utf-8')).hexdigest()[:24]



def _getpointattrs(point):
    return tuple(point[k] for k in POINT_KEYS)



def _getedgeattrs(edge):
    return tuple(edge.get(k, 'NA') for k in EDGE_KEYS)



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



def _process_trips(rego, trips, mm_file_name, seq_file_name):
    def run_trip(trip, trip_index):
        try:
            way_ids = {
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

            # convert the output from Valhalla into our outputs (seq and mm files).
            edges = snapped['edges']
            match_props = ((p.get('edge_index'), p['type']) for p in snapped['matched_points'])
            way_ids['way_ids'] = [e['way_id'] for e in edges]
            way_ids['geojson'] = json2geojson(snapped)
            way_ids['status'] = 'success'

            return way_ids, [_getpointattrs(p) + \
                ('success', trip_index) + \
                (_getedgeattrs(edges[ei]) if ei is not None else NAS) + \
                (mt,) for p, (ei, mt) in zip(trip['shape'], match_props)]

        except Exception as e:
            e_str = '{}: {}'.format(e.__class__.__name__, str(e))
            way_ids['status'] = 'failure'
            way_ids['message'] = e_str
            return way_ids, [_getpointattrs(p) + \
                ('failure', trip_index) + \
                NAS + \
                (e_str,) for p in trip['shape']]

    try:
        with open(mm_file_name, 'w') as mmfile, open(seq_file_name , 'w') as seqfile:

            # write the header (to the mm file)
            mmfile.write(','.join(
                POINT_KEYS + \
                ('status', 'trip_index') + \
                EDGE_ATTR_NAMES + \
                ('message',)) + '\n')

            # write a trip (to the mm file)
            def write_trips(trip_desc, result):
                mmfile.writelines('{}\n'.format(
                    ','.join(str(t) for t in tup)) for tup in result)
                return trip_desc

            results = (run_trip(trip, ti) for ti, trip in enumerate(trips))
            json.dump([write_trips(*r) for r in results], seqfile)

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

    mm_file_name  = os.path.join(MM_PATH,  '{}.csv'.format(rego))
    seq_file_name = os.path.join(SEQ_PATH, '{}.json'.format(rego))

    if os.path.exists(mm_file_name) and os.path.exists(seq_file_name):
        logger.debug('skipping: {} (done)'.format(rego))
        return

    # Can't do this in the block above if we want to check that we must proceed
    # first.
    if isinstance(input_files, str) and input_files == MONGO_VALUE:
        doc   = docs_for_vehicle(fn)
        trips = mongodoc2jsonchunks(doc, True)
    else:
        trips = rawfiles2jsonchunks(input_files, True)

    return _process_trips(rego, trips, mm_file_name, seq_file_name)

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
    mm_file_name     = os.path.join(OUT_PATH, 'mm_files.pkl')

    def requires(self):
        """:meta private:"""
        return ListRawFiles()

    def run(self):
        """:meta private:"""
        # load the input file data
        with open(self.input().fn, 'rb') as input_files_file:
            input_files = pickle.load(input_files_file)

        # do the jobby
        with Pool(initializer = _init_db_connection) as workers:
            work = workers.imap_unordered(_process_files, input_files.items())
            # wrap in list so we wait for jobby to finish.
            list(tqdm(work, total=len(input_files)))

        # list the (seq) output files
        seq_output_files = glob(os.path.join(SEQ_PATH, '*'))
        with open(self.output()['seq'].fn, 'wb') as pf:
            pickle.dump(seq_output_files, pf)

        # list the (mm) output files
        mm_output_files = glob(os.path.join(MM_PATH, '*'))
        with open(self.output()['mm'].fn, 'wb') as pf:
            pickle.dump(mm_output_files, pf)

    def output(self):
        """:meta private:"""
        return {
            'seq': luigi.LocalTarget(self.pickle_file_name),
            'mm' : luigi.LocalTarget(self.mm_file_name)}
