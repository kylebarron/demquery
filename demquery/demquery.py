################################################################################
# Module: demquery.py
# Description: Wrapper around rasterio to query a Digital Elevation Model
# License: MIT, see full license in LICENSE
# Web: https://github.com/kylebarron/demquery
################################################################################

import os
import os.path
import tempfile
from pathlib import Path

import numpy as np
import rasterio
from osgeo import gdal
from scipy.interpolate import interp2d


class NoDataException(Exception):
    pass


class Query:
    def __init__(self, dem_paths, band=1):
        """Query Digital Elevation Model

        Parameters
        ----------
        dem_paths : list
            list of paths to DEM files. DEM files can be any format readable by
            GDAL.
        band : int
            band of DEM file to query data from; 1 by default.
        """
        super(Query, self).__init__()
        self.band = band

        if len(dem_paths) > 1:
            self.dem_path = self._build_vrt(dem_paths=dem_paths)
        else:
            self.dem_path = dem_paths[0]

    def query_points(self, points, interp_kind=None):
        """Query points in DEM

        Parameters
        ----------
        points : list of float or int
            list of tuples **in longitude, latitude order** representing points
            to query from the DEM
        interp_kind : None or str
            one of None, 'linear', 'cubic', 'quintic'. None will do no
            interpolation and choose the value in the DEM closest to the
            provided point. linear creates a 3x3 grid and runs linear
            interpolation; cubic creates a 5x5 grid and runs cubic
            interpolation; quintic creates a 7x7 grid and runs quintic
            interpolation

        Returns
        -------
        List[float]: queried elevation values, in the units of the DEM
        """
        # interp_kind: num_buffer (number of bordering cells required for
        # interpolation)
        interp_allowed = {None: 0, 'linear': 1, 'cubic': 2, 'quintic': 3}
        num_buffer = interp_allowed.get(interp_kind)
        if num_buffer is None:
            msg = (
                'interp_kind must be one of ' +
                ', '.join(map(str, interp_allowed.keys())))
            raise ValueError(msg)

        with rasterio.open(self.dem_path) as dem:
            self._check_bounds(dem, points, num_buffer=num_buffer)

            # This must be a list comprehension and not a generator, because
            # with a generator, when it tries to create the values, the dem
            # object is already closed.
            return [
                self._query_point(
                    dem, point, num_buffer=num_buffer, interp_kind=interp_kind)
                for point in points
            ]

    def _build_vrt(self, dem_paths):
        """Create virtual raster using gdal

        Parameters
        ----------
        dem_paths : list
            list of strings or pathlib.Path to DEM paths

        Returns
        -------
        str : path to virtual raster file
        """
        # Make sure all dem_paths exist
        # An obscure error is given if the files don't exist
        for dem_path in dem_paths:
            if not Path(dem_path).exists():
                raise FileNotFoundError(dem_path)

        tmpdir = tempfile.mkdtemp()
        vrt_path = os.path.join(tmpdir, 'dem.vrt')

        # Setting vrt to None is weird but required
        # https://gis.stackexchange.com/a/314580
        # https://gdal.org/tutorials/raster_api_tut.html#using-createcopy
        # The dem_paths must be str, not pathlib.Path!
        vrt = gdal.BuildVRT(vrt_path, list(map(str, dem_paths)))
        vrt = None

        # Check that vrt_path actually was created
        if not Path(vrt_path).exists():
            raise ValueError('Unable to create virtual raster')

        return vrt_path

    def _check_bounds(self, dem, points, num_buffer):
        """Check lon, lat is within bounds

        Note that this doesn't check that these values are non-missing. With a
        mosaic of tiles, the lon/lat could be within bounds of the virtual
        raster, but have no data.

        Parameters
        ----------
        dem : rasterio.DatasetReader
            open rasterio DatasetReader
        points : List[tuple]
            list of tuples in longitude, latitude order
        num_buffer : int
            number of bordering cells around point to check
        """
        for point in points:
            # Split after for line to allow Z in source points
            lon, lat = point[0], point[1]

            # Find row, column of elevation square inside raster
            # Note that row should be thought of as the "y" value; it's the
            # number  _across_ rows, and col should be thought of as the "y"
            # value _across_ columns.
            row, col = dem.index(lon, lat)
            minrow, maxrow = row - num_buffer, row + num_buffer
            mincol, maxcol = col - num_buffer, col + num_buffer

            msg = 'longitude outside DEM bounds'
            msg += '\npoints should be provided in longitude, latitude order.'
            assert minrow >= 0, msg
            assert maxrow <= dem.height

            msg = 'latitude outside DEM bounds'
            msg += '\npoints should be provided in longitude, latitude order.'
            assert mincol >= 0, msg
            assert maxcol <= dem.width

    def _get_buffer_grid(self, dem, point, num_buffer):
        """Get array of longitude, latitude, and elevation values from DEM file

        Parameters
        ----------
        dem : rasterio.DatasetReader
            open rasterio DatasetReader
        point : tuple
            tuple of int or float representing longitude and latitude
        num_buffer : int
            number of bordering cells around point to retrieve

        Returns
        -------
        array : 3D Numpy array
            (array of longitude values, array of latitude values, array of
            elevation values)
        """
        # Find row, column of elevation square inside raster
        # Note that row should be thought of as the "y" value; it's the number
        # _across_ rows, and col should be thought of as the "y" value _across_
        # columns.
        lon, lat = point[0], point[1]
        row, col = dem.index(lon, lat)

        # Make window include cells around it
        # The number of additional cells depends on the value of num_buffer
        # When num_buffer==1, an additional 8 cells will be loaded and
        # interpolated on;
        # When num_buffer==2, an additional 24 cells will be loaded and
        # interpolated on, etc.
        # When using kind='linear' interpolation, I'm not sure if having the
        # extra cells makes a difference; ie if it creates the plane based only
        # on the closest cells or from all. When using kind='cubic', it's
        # probably more accurate with more cells.
        minrow, maxrow = row - num_buffer, row + num_buffer
        mincol, maxcol = col - num_buffer, col + num_buffer

        # Add +1 to deal with range() not including end
        maxrow += 1
        maxcol += 1

        # Retrieve just this window of values from the DEM
        window = ([minrow, maxrow], [mincol, maxcol])
        val_arr = dem.read(self.band, window=window)

        # Check the nodata value for the given band against retrieved values
        try:
            nodataval = dem.nodatavals[self.band - 1]
            if np.any(val_arr == nodataval):
                msg = (
                    'Raster nodata value found near lon: {}, lat: {}'.format(
                        lon, lat))
                raise NoDataException(msg)
        except IndexError:
            # nodataval is not required to exist for each band
            pass

        # Check shape
        expected_rows = 2 * num_buffer + 1
        expected_cols = 2 * num_buffer + 1
        msg = 'unexpected array shape'
        assert val_arr.shape == (expected_rows, expected_cols), msg

        lons, lats = self._lon_lat_grid(dem, minrow, maxrow, mincol, maxcol)

        # Array with longitudes, latitudes, values
        # I.e. x, y, z
        return np.array([np.array(lons), np.array(lats), val_arr])

    def _lon_lat_grid(self, dem, minrow, maxrow, mincol, maxcol):
        """Create grids of longitude and latitude values from column indices

        Each value corresponds to the center of the given cell.

        Parameters
        ----------
        dem : rasterio.DatasetReader
            open rasterio DatasetReader
        minrow : int
            min row to query
        maxrow : int
            max row to query
        mincol : int
            min col to query
        maxcol : int
            max col to query

        Returns
        -------
        List[float]: queried elevation values, in the units of the DEM
        """
        # Create array of latitude/longitude pairs for each cell center
        lons = []
        lats = []
        for row in range(minrow, maxrow):
            lon_cols = []
            lat_cols = []
            for col in range(mincol, maxcol):
                lon, lat = dem.xy(row, col)
                lon_cols.append(lon)
                lat_cols.append(lat)

            lons.append(lon_cols)
            lats.append(lat_cols)

        return lons, lats

    def _query_point(self, dem, point, num_buffer, interp_kind):
        """Query elevation data for given point

        Parameters
        ----------
        dem : rasterio.DatasetReader
        point : tuple
            tuple of int or float representing longitude and latitude
        num_buffer : int
            number of bordering cells around point to use when interpolating
        interp_kind : str
            kind of interpolation. Passed to scipy.interpolate.interp2d. Can be
            ['linear', 'cubic', 'quintic']. Note that 'cubic' requires
            'num_buffer' of at least 3 and 'quintic' requires 'num_buffer' of at
            least 5.

        Returns
        -------
        value : float
            elevation in terms of the unit of the DEM (usually meters)
        """
        arr = self._get_buffer_grid(dem=dem, point=point, num_buffer=num_buffer)

        # Don't attempt interpolation if not necessary.
        # arr[2, 0, 0] selects the single z value. arr[2] is the 2D array of z
        # values; there's only one value there so it's [0, 0]
        if interp_kind is None:
            return arr[2, 0, 0]

        # Take responses and create lists of lat/lons/values to interpolate over
        x = arr[0].flatten()
        y = arr[1].flatten()
        z = arr[2].flatten()

        # Interpolate over the values
        # fun() returns an array of length 1
        fun = interp2d(x=x, y=y, z=z, kind=interp_kind, bounds_error=True)
        return fun(point[0], point[1])[0]
