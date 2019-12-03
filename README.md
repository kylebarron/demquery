# demquery


[![Pypi](https://img.shields.io/pypi/v/demquery.svg)](https://pypi.python.org/pypi/demquery) [![Downloads](https://img.shields.io/travis/kylebarron/demquery.svg)](https://travis-ci.org/kylebarron/demquery) [![Supported Python Versions](https://img.shields.io/pypi/pyversions/demquery.svg)](https://pypi.org/project/demquery/#supported-versions)

Wrapper around rasterio to query points on a Digital Elevation Model.

## Features

- Use multiple raster files without having to merge them into a new file
- Query many points at once
- Optional 2D interpolation (linear, cubic, or quintic)
- Reasonably performant by reading the minimal data required from raster

## Install

I recommend first installing dependencies with Conda, then installing demquery
itself with pip.

```
conda install gdal rasterio numpy scipy -c conda-forge
```

```
pip install demquery
```

## Documentation

```py
from demquery import Query

dem_paths = ['dem1.tif', 'dem2.tif']
query = Query(dem_paths)

# Points must be in longitude, latitude order!
# These points are in Manhattan, not Antarctica
points = [(-73.985564, 40.757965), (-73.968520, 40.778912)]
elevations = query.query_points(points, interp_kind='linear')
```

## Data Download

For a great visual tool to download worldwide SRTM data, check out these sites:

- 30m resolution: http://dwtkns.com/srtm30m/
- 90m resolution: http://dwtkns.com/srtm/
