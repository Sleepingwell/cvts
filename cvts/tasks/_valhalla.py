#!/usr/bin/env python3

import os
import json
import pickle
import tempfile
import logging
from glob import glob
from collections import defaultdict
from multiprocessing import Pool
import luigi
from ..settings import (
    RAW_PATH,
    OUT_PATH,
    MM_PATH,
    SEQ_PATH,
    VALHALLA_CONFIG_FILE)
from .. import rawfiles2jsonchunks, json2geojson



logger = logging.getLogger(__name__)



POINT_KEYS = ('lat', 'lon', 'time', 'heading', 'speed', 'heading_tolerance')
TMP_DIR = tempfile.gettempdir()
EDGE_KEYS = ('way_id', 'speed', 'speed_limit')
EDGE_ATTR_NAMES = ('way_id', 'valhalla_speed', 'speed_limit')
NAS = ('NA',) * len(EDGE_KEYS)



def _getpointattrs(point):
    return tuple(point[k] for k in POINT_KEYS)



def _getedgeattrs(edge):
    return tuple(edge.get(k, 'NA') for k in EDGE_KEYS)



def _run_valhalla(fn, trip, trip_index):
    tmp_file_in  = os.path.join(TMP_DIR, str(trip_index) + '_in_'  + fn)
    tmp_file_out = os.path.join(TMP_DIR, str(trip_index) + '_out_' + fn)

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



def _process_files(fns):
    fn          = fns[0]
    input_files = fns[1]
    rego        = os.path.splitext(fn)[0]

    assert(fn.endswith('.csv'))

    pnt_file = os.path.join(MM_PATH, fn)
    seq_file = os.path.join(SEQ_PATH, '{}.json'.format(rego))

    if os.path.exists(pnt_file) and os.path.exists(seq_file):
        logger.info('skipping: {} (done)'.format(rego))
        return

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
                snapped = _run_valhalla(fn, trip, trip_index)

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
        with open(pnt_file, 'w') as resultsfile, open(seq_file , 'w') as seqfile:

            # write the header (to the mm file)
            resultsfile.write(','.join(
                POINT_KEYS + \
                ('status', 'trip_index') + \
                EDGE_ATTR_NAMES + \
                ('message',)) + '\n')

            def write_trips(trip_desc, result):
                resultsfile.writelines('{}\n'.format(
                    ','.join(str(t) for t in tup)) for tup in result)
                return trip_desc

            trips = rawfiles2jsonchunks(input_files, True)
            results = (run_trip(trip, ti) for ti, trip in enumerate(trips))
            json.dump([write_trips(*r) for r in results], seqfile)

    except Exception as e:
        logger.exception('processing {} failed...'.format(rego))

    else:
        logger.info('processing {} passed'.format(rego))



#-------------------------------------------------------------------------------
# Luigi tasks
#-------------------------------------------------------------------------------
class ListRawFiles(luigi.Task):
    """Gather information about input files."""

    pickle_file_name = os.path.join(OUT_PATH, 'raw_files.pkl')

    def run(self):
        """:meta private:"""
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
        with Pool() as p:
            p.map(_process_files, input_files.items())

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
