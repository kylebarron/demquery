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

## CLI Script

```
> demquery --help
Usage: demquery [OPTIONS] FEATURES...

  Assign elevations to GeoJSON

Options:
  -d, --dem PATH          Paths to DEM files.  [required]
  -g, --dem-glob TEXT     Glob expression for DEM paths if folder is provided.
  -b, --band INTEGER      Band of rasters to use  [default: 1]
  -i, --interp-kind TEXT  either None, "linear", "cubic", or "quintic". None
                          will do no interpolation and choose the value in the
                          DEM closest to the provided point. linear creates a
                          3x3 grid and runs linear interpolation; cubic
                          creates a 5x5 grid and runs cubic interpolation;
                          quintic creates a 7x7 grid and runs quintic
                          interpolation.
  --help                  Show this message and exit.
```

```bash
echo \
    '{"type":"Feature","properties":{"name": "Glacier Peak"},"geometry":{"type":"Point","coordinates":[-121.2436843,48.0163834]}}' \
    | demquery -d /path/to/dem/files
```
Outputs:
```json
{"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [-121.243684, 48.016383, 1431.5755615234375]}, "properties": {"name": "Glacier Peak"}}]}
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

## Releasing

To upload a new release to PyPI

```bash
python setup.py sdist
twine upload dist/demquery-0.3.0.tar.gz
```
