#!/usr/bin/env python
"""Tests for `demquery` package."""

from urllib.request import urlretrieve
from zipfile import ZipFile

from demquery import Query

# Download sample data
stubs = ['USGS_NED_13_n33w117_IMG', 'USGS_NED_13_n34w117_IMG']
for stub in stubs:
    url = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/IMG/'
    url += stub
    url += '.zip'
    urlretrieve(url, stub + '.zip')

    # Extract file
    with ZipFile(stub + '.zip') as z:
        z.extractall('.')


def test_create_query():
    dem_paths = [x + '.img' for x in stubs]
    query = Query(dem_paths)
