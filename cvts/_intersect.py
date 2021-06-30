"""Intersect shapefiles with GNAF data."""

from multiprocessing import Pool
from typing import Tuple

import numpy as np
from nptyping import NDArray
from shapely.geometry import box, Point, polygon
from tqdm import tqdm

from .settings import DEBUG



MULTI_CORE = not DEBUG



def points_to_polys(
        points: NDArray,
        shapedata: str) -> NDArray:
    """Calculate which geometry each point in *points* lie within.

    :param points: Two column numpy array containing the longitudes and
        latitudes of the address points.

    :param shapedata: tuple containing geometry IDs, polygions and bounding boxes
        for a geography.

    :return: The geometry ID for each point.
    """

    # Remove points containing NaNs.
    points = points[~np.any(np.isnan(points), 1),]

    # Compute inds, but map back to keys
    keys = np.hstack((shapedata[0], [-1]))
    meshblock_inds = _points_to_shapes(points, shapedata)

    return keys[meshblock_inds]




def _points_to_shapes(
        points: NDArray,
        shapedata: Tuple[NDArray, polygon.Polygon, NDArray, NDArray]
    ) -> NDArray[str]:
    """Intersect points in *points* and geometries in *shapedata*.

    Applies a tree search to prune possible intersections,
    and a worker pool to evaluate the shortlisted candidates.

    :param points: Two column numpy array containing the longitudes and
        latitudes of the address points.

    :param shapedata: tuple containing geometry IDs, polygions and bounding boxes
        for a geography.

    :return: Geometry id of every point in *points*.
    """

    keys, polys, boxes = shapedata
    rows = np.arange(len(keys))[:, None]

    # Partitioning points spatially
    print("Shortlisting Intersections")

    # Augment Points and Boxes with their row index
    P = np.hstack((points, np.arange(points.shape[0])[:, None]))
    B = np.hstack((boxes, np.arange(rows.shape[0])[:, None]))

    chunksize = 200  # tune based on cost of searching
    n = points.shape[0]
    partsize = n
    n_parts = 1
    while partsize > chunksize:
        partsize /= 2
        n_parts *= 2

    # Build search tree
    _parts = _tree_search(P, B, polys, chunksize)

    # Preload for higher multi-core usage
    parts = []
    for part in tqdm(_parts, total=n_parts):
        parts.append(part)

    print("Step 2: intersections.")
    if MULTI_CORE:
        workers = Pool()
        work = workers.imap_unordered(_intercept_block, parts, chunksize=5)
    else:
        work = map(_intercept_block, parts)

    # start with a vector of -1 in the result, so that when indexing the list
    # of meshblock IDs with an appropirate no dagta value tacked on the end,
    # points that overlap with no meshblock get that no data value (see
    # implementation of point_to_poly).
    alloc = np.zeros(n, dtype=int) - 1

    # Here is the multiprocessed bit:
    for points, keys in tqdm(work, total=n_parts):
        alloc[points] = keys

    if MULTI_CORE:
        workers.close()

    print("{:.0f}% present".format(100 * (alloc > 0).mean()))

    return alloc



def _tree_search(points, boxes, polys, maxsize):
    """Divide and conquer approach to handling large point sets."""

    # Intersect Polys to point bounding box:
    L, B, R, T, _ = boxes.T
    p = points[:, :2]
    bl, bb = p.min(axis=0)
    br, bt = p.max(axis=0)
    clip = (
        (np.maximum(L, bl) < np.minimum(R, br)) &
        (np.maximum(B, bb) < np.minimum(T, bt)))
    boxes = boxes[clip]

    if points.shape[0] < maxsize:
        # Yield something we can multiprocess
        BIndx = boxes[:, 4].astype(int)
        shapes = [polys[b] for b in BIndx]
        yield (points, boxes, shapes)
    else:
        # Branch:
        axis = ((bt - bb) > (br - bl)).astype(int)
        cutoff = int(points.shape[0] / 2)
        order = np.argpartition(points[:, axis], cutoff)
        splits = [
            order[:cutoff],
            order[cutoff:]]

        for inds in splits:
            for retval in _tree_search(points[inds], boxes, polys, maxsize):
                yield retval

    return



def _intercept_block(inps):
    """Run a slow and accurate check between points and shapes.

    Of the 20 cpu minutes of work, only about 30 seconds is spent outside this
    call (including calling overhead).
    """
    points, boxes, shapes = inps

    # Is it stopping too early? hmm

    # apparently some points are intersecting more than one meshblock
    # simultaneously.. how?

    # Vectorised bounding box check:
    L, B, R, T, BID = boxes.T
    X, Y, PID = points.T
    BID = BID.astype(int)
    PID = PID.astype(int)
    X = X[None, :]
    Y = Y[None, :]

    # Shortlist possible overlap - a numpy broadcast is ok:
    cond = (
        (X > L[:, None]) &
        (X < R[:, None]) &
        (Y > B[:, None]) &
        (Y < T[:, None]))

    # Make points inside the job.
    s_points = [Point(v) for v in points[:, :2]]

    # intersect shapes with bounding boxes of points once now to save on
    # repeats (could significantly speed up the check)

    # If we cut the polys to exactly the bounding box, then the points on the
    # bound will always get removed (so thats at least 2, probably 4, possibly
    # more per chunk)
    pad = 1e-7
    b = box(X.min() - pad, Y.min() - pad,
            X.max() + pad, Y.max() + pad)
    shapes = [s.intersection(b) for s in shapes]

    i, j = np.where(cond)
    intersects = [shapes[_i].contains(s_points[_j])
                  for _i, _j in zip(i, j)]
    PIDs = PID[j[intersects]]
    BIDs = BID[i[intersects]]

    return (PIDs, BIDs)
