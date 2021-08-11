import os
import pickle
import logging
import csv
from glob import glob
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm
import luigi
from cvts.settings import (
    OUT_PATH,
    SPEED_PATH,
    POSTGRES_CONNECTION_STRING)
from ..models import Traversal
from ._valhalla import MatchToNetwork

AVE_SPEED_FILE = 'ave_speeds.pkl'



def _process_file(filename):
    rego = os.path.splitext(os.path.basename(filename))[0]

    df = pd.read_csv(filename)
    df.drop(df[df.status == 'failure'].index, inplace=True)
    df.dropna(subset = ['way_id'], inplace=True)
    if df.shape[0] == 0:
        return

    # TODO: did I check that int32 was suitable?
    df['way_id'] = df['way_id'].astype(np.int32)

    # add date and hour
    dt = pd.to_datetime(df['time'], unit='s').dt
    df['hour']    = dt.hour
    df['weekDay'] = dt.weekday

    # average speed
    def ave_speed(df):
        # average for each trip
        tmp = df.groupby('trip_index').agg({'speed': ['mean', 'size']})

        # average for the way_id/hour/weekDay
        return pd.Series({
            'speed' : np.average(tmp[('speed', 'mean')], weights=tmp[('speed', 'size')]),
            'weight': np.sum(tmp[('speed', 'size')])})

    #TODO: Do we want to check 'valhalla_speed' also/instead
    speed = df[df.speed > 6].groupby(['way_id', 'hour', 'weekDay']).apply(ave_speed).reset_index()
    if speed.shape[0] != 0:
        speed["rego"] = rego
        speed.to_csv(os.path.join(SPEED_PATH, '{}-speed.csv'.format(rego)), index=False)

    # proportion moving
    def prop_moving(series):
        nzero = np.sum(series <= 6)
        return np.sum(series > 6) / (nzero if nzero > 0 else 1)

    try:
        moving = df.groupby(['hour', 'weekDay']).agg({'speed': [prop_moving]}).reset_index()
        moving.columns = ['hour', 'weekDay', 'propMoving']
        moving["rego"] = rego
        moving.to_csv(os.path.join(SPEED_PATH, '{}-moving.csv'.format(rego)), index=False)
    except:
        moving = None



_engine = create_engine(POSTGRES_CONNECTION_STRING)
_session_maker = None
def _engine_dispose():
    # to be called from the pools initialiser
    # see: https://docs.sqlalchemy.org/en/13/core/pooling.html#pooling-multiprocessing
    global _engine, _session_maker
    _engine.dispose()
    _session_maker = sessionmaker(bind=_engine)

def _trips_to_db(trip_file_name):
    global _session_maker
    rego    = os.path.splitext(os.path.basename(trip_file_name))[0].split('-')[0]
    session = _session_maker()

    with open(trip_file_name, 'r') as csvfile:
        speeds = csv.DictReader(csvfile)
        for line in speeds:
            traversal = Traversal(
                rego    = rego,
                way     = line['way_id'],
                hour    = line['hour'],
                weekday = line['weekDay'],
                speed   = line['speed'],
                weight  = line['weight'])
            session.add(traversal)
    session.commit()

#-------------------------------------------------------------------------------
# Luigi tasks
#-------------------------------------------------------------------------------
class AverageSpeed(luigi.Task):
    """Collects all the stop points for all trips of all vehicles."""

    pickle_file_name = os.path.join(OUT_PATH, AVE_SPEED_FILE)

    def requires(self):
        """:meta private:"""
        return MatchToNetwork()

    def run(self):
        """:meta private:"""
        with open(self.input()['mm'].fn, 'rb') as mm_files_file:
            mm_files = pickle.load(mm_files_file)

        with Pool() as p:
            workers = p.imap_unordered(_process_file, mm_files)
            list(tqdm(workers, total=len(mm_files)))

        with open(self.output().fn, 'wb') as of:
            output_files = glob(os.path.join(SPEED_PATH, '*-speed.csv'))
            with open(self.output().fn, 'wb') as pf:
                pickle.dump(output_files, pf)

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(self.pickle_file_name)




class TripsToDB(luigi.Task):
    def requires(self):
        """:meta private:"""
        return AverageSpeed()

    def run(self):
        """:meta private:"""
        with open(self.input().fn, 'rb') as sf:
            all_seq_files = pickle.load(sf)

        with Pool(initializer=_engine_dispose) as p:
            workers = p.imap_unordered(_trips_to_db, all_seq_files)
            list(tqdm(workers, total=len(all_seq_files)))

        Path(self.output().fn).touch()

    def output(self):
        """:meta private:"""
        return luigi.LocalTarget(os.path.join(OUT_PATH, 'db_dumped'))
