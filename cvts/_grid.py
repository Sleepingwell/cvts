from math import floor, ceil
import numpy as np



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



class Grid:
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
        try:
            row = self.nrow - int(floor((lat - self.minlat) / self.cellsize)) - 1
            col =             int(floor((lon - self.minlon) / self.cellsize))
            if 0 <= col < self.ncol and 0 <= row < self.nrow:
                self.cells[row, col] += 1
            return row, col
        except ValueError as e:
            logger.warning('value error: {} at ({:.2f}, {:.2f})'.format(e, lat, lon))
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
