import logging
from functools import reduce
from pymongo import MongoClient
from .settings import MONGO_CONNECTION_STRING, MONGO_COLLECTION_NAMES
from ._timer import Timer

_client = None
_db = None
_collection_names = None

logger = logging.getLogger(__name__)

def _init_db_connection():
    global _client, _db, _collection_names
    _client = MongoClient(MONGO_CONNECTION_STRING)
    _db=_client.wb
    _collection_names = _db.list_collection_names()
    if MONGO_COLLECTION_NAMES is not None:
        _collection_names = list(set(_collection_names) & set(MONGO_COLLECTION_NAMES))



def _check_init():
    global _collection_names
    if _collection_names is None:
        _init_db_connection()



def _check_or_create_index(collection_name, db=None):
    def doer(db):
        col = getattr(db, collection_name)
        indexes = col.index_information()
        if 'vehicle_1' not in indexes:
            logger.info('creating index on collection "{}"'.format(collection_name))
            with Timer(logger.info) as t:
                col.create_index([('vehicle', 1)])

    if db is None:
        with MongoClient(MONGO_CONNECTION_STRING) as client:
            doer(client.wb)
    else:
        doer(db)



def all_collection_names():
    with MongoClient(MONGO_CONNECTION_STRING) as client:
        db=client.wb
        return db.list_collection_names()



def _vehicle_ids_for_collection(collection_name, db, limit):
    # Should pay attention to the $group stage description at
    # https://docs.mongodb.com/manual/core/aggregation-pipeline/,
    # which states the conditions required for this to use the index (on
    # vehicle). I tried this but it seemed to make no difference to the
    # performance... not sure why. Given that I had and index for
    # { 'vehicle': 1 }, here is what I did (adapted from
    # https://docs.mongodb.com/manual/reference/operator/aggregation/group/#optimization-to-return-the-first-document-of-each-group)...
    #
    #stages = [
    #    { '$sort': { 'vehicle': 1 } },
    #    { '$group': {
    #        '_id': { 'vehicle': '$vehicle' },
    #        'vehicle_id': { '$first': '$vehicle' }
    #        }}
    #    ]
    stages = [{ '$group': { '_id': '$vehicle' }}]
    if limit is not None:
        stages.insert(0, { '$limit': limit })
    logger.info('retrieving unique vehicle ids in collection "{}"'.format(collection_name))
    with Timer(logger.info) as t:
        vehicle_ids_iter = getattr(db, collection_name).aggregate(stages)
        return [v['_id'] for v in vehicle_ids_iter]



def create_indexes():
    with MongoClient(MONGO_CONNECTION_STRING) as client:
        db=client.wb
        cns = db.list_collection_names()
        if MONGO_COLLECTION_NAMES is not None:
            cns = list(set(cns) & set(MONGO_COLLECTION_NAMES))
        for cn in cns:
            _check_or_create_index(cn, db)



def vehicle_ids(limit=None):
    res = set()
    with MongoClient(MONGO_CONNECTION_STRING) as client:
        db=client.wb
        cns = db.list_collection_names()
        if MONGO_COLLECTION_NAMES is not None:
            cns = list(set(cns) & set(MONGO_COLLECTION_NAMES))
        for cn in cns:
            # does not seem to improve the performance of listing the vehicle
            # ids, but is a convenient place to create the index
            _check_or_create_index(cn, db)
            res.update(_vehicle_ids_for_collection(cn, db, limit))
        return list(res)



def _docs_for_vehicle_for_collection(vehicle_id, collection_name):
    return [d for d in getattr(_db, collection_name).find({'vehicle': vehicle_id})]



def docs_for_vehicle(vehicle_id):
    _check_init()
    # perhaps better done with $unionWith (which is only available from version 4.4)
    # https://docs.mongodb.com/manual/reference/operator/aggregation/unionWith
    return reduce(
        lambda a, cn: a + _docs_for_vehicle_for_collection(vehicle_id, cn),
        _collection_names,
        [])



if __name__ == '__main__':
    from pprint import pprint
    _check_init()
    pprint(_docs_for_vehicle_for_collection(next(iter(vehicle_ids(1))), _collection_names[0]))
    pprint(_docs_for_vehicle(next(iter(vehicle_ids(1)))))
