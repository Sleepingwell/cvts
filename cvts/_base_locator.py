#!/user/bin/env python

import numpy as np
from ._grid import Grid, MINLAT, MAXLAT, MINLON, MAXLON, CELLSIZE



KERNEL = [[0.5, 0.5, 0.5],
          [0.5, 1.0, 0.5],
          [0.5, 0.5, 0.5]]

TARGET_CELL_SIZE_IN_DEG = 0.003



class EmptyCellsException(Exception): pass



def locate_base(lons, lats, speeds,
        minlat = MINLAT,
        maxlat = MAXLAT,
        minlon = MINLON,
        maxlon = MAXLON,
        cellsize = TARGET_CELL_SIZE_IN_DEG,
        maxspeed = 1.):

    rows = None
    cols = None
    lats = np.array(lats)
    lons = np.array(lons)
    conds = np.all(np.array([
        np.array(speeds) <= maxspeed,
        lats > minlat,
        lats < maxlat,
        lons > minlon,
        lons < maxlon]), axis=0)
    lats = np.array(lats)[conds]
    lons = np.array(lons)[conds]

    g = Grid(
        minlat   = minlat,
        minlon   = minlon,
        maxlat   = maxlat,
        maxlon   = maxlon,
        cellsize = cellsize)

    rowcols = g.increment_many(lons, lats)

    convolved = g.convolve(KERNEL)
    largest_index = np.unravel_index(np.argmax(convolved), convolved.shape)

    rows = np.arange(largest_index[0]-1, largest_index[0]+2)
    rows = rows[np.all(np.vstack((0 <= rows, rows < convolved.shape[0])), 0)]

    cols = np.arange(largest_index[1]-1, largest_index[1]+2)
    cols = cols[np.all(np.vstack((0 <= cols, cols < convolved.shape[1])), 0)]

    inds = np.all([
        np.in1d(rowcols[:,0], rows),
        np.in1d(rowcols[:,1], cols)], 0)

    lats = lats[inds]
    lons = lons[inds]

    if len(lats) == 0:
        raise EmptyCellsException('no latitudes left')
    if len(lons) == 0:
        raise EmptyCellsException('no longitudes left')

    return np.mean(lons), np.mean(lats)
