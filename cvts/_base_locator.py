#!/user/bin/env python

import numpy as np
from ._grid import Grid, MINLAT, MAXLAT, MINLON, MAXLON, CELLSIZE



KERNEL = [[0.5, 0.5, 0.5],
          [0.5, 1.0, 0.5],
          [0.5, 0.5, 0.5]]

TARGET_CELL_SIZES_IN_DEG = (.5, .05, .003)



class EmptyCellsException(Exception): pass



def locate_base(lons, lats, speeds,
        minlat = MINLAT,
        maxlat = MAXLAT,
        minlon = MINLON,
        maxlon = MAXLON,
        cellsizes = TARGET_CELL_SIZES_IN_DEG,
        maxspeed = 1.):

    lats = np.array(lats)
    lons = np.array(lons)
    valid_lls = np.array(speeds) <= maxspeed
    lats = np.array(lats)[valid_lls]
    lons = np.array(lons)[valid_lls]

    # we loop to try and keep the amount of memory allocated in the grid to
    # something that will be manageable everywhere.
    for cellsize in cellsizes:
        g = Grid(
            minlat   = minlat,
            minlon   = minlon,
            maxlat   = maxlat,
            maxlon   = maxlon,
            cellsize = cellsize)

        rowcols, lons, lats = g.increment_many(lons, lats)

        if len(lats) == 0:
            raise EmptyCellsException('no latitudes left')
        if len(lons) == 0:
            raise EmptyCellsException('no longitudes left')

        c = g.convolve(KERNEL)
        largest_index = np.unravel_index(np.argmax(c), c.shape)

        rows = np.arange(largest_index[0]-1, largest_index[0]+2)
        rows = rows[np.all(np.vstack((0 <= rows, rows < c.shape[0])), 0)]

        cols = np.arange(largest_index[1]-1, largest_index[1]+2)
        cols = cols[np.all(np.vstack((0 <= cols, cols < c.shape[1])), 0)]

        inds = np.all(np.vstack((
            np.in1d(rowcols[:,0], rows),
            np.in1d(rowcols[:,1], cols))), axis=0)

        lons = lons[inds]
        lats = lats[inds]

        meanlon, meanlat = np.mean(lons), np.mean(lats)

        if cellsize > cellsizes[-1]:
            # centers the cells on the average of what's left
            minlat = meanlat - 2.0 * cellsize
            maxlat = meanlat + 2.0 * cellsize
            minlon = meanlon - 2.0 * cellsize
            maxlon = meanlon + 2.0 * cellsize

        else:
            return meanlon, meanlat
