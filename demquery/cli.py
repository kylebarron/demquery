import json
from pathlib import Path

import click
import cligj
import geojson

from .demquery import NoDataException, Query


@click.command()
@cligj.features_in_arg
@click.option(
    '-d',
    '--dem',
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True),
    required=True,
    help='Paths to DEM files.')
@click.option(
    '-g',
    '--dem-glob',
    type=str,
    required=False,
    default=None,
    help='Glob expression for DEM paths if folder is provided.')
@click.option(
    '-b',
    '--band',
    type=int,
    required=False,
    default=1,
    show_default=True,
    help='Band of rasters to use')
@click.option(
    '-i',
    '--interp-kind',
    type=str,
    required=False,
    default=None,
    show_default=True,
    help=
    'either None, "linear", "cubic", or "quintic". None will do no interpolation and choose the value in the DEM closest to the provided point. linear creates a 3x3 grid and runs linear interpolation; cubic creates a 5x5 grid and runs cubic interpolation; quintic creates a 7x7 grid and runs quintic interpolation.'
)
def main(features, dem, dem_glob, band, interp_kind):
    """Assign elevations to GeoJSON
    """
    dem_path = Path(dem)
    if dem_path.is_dir():
        if dem_glob is not None:
            dem_paths = list(dem_path.glob(dem_glob))
        else:
            dem_paths = list(dem_path.iterdir())
    else:
        dem_paths = [dem_path]

    query = Query(dem_paths=dem_paths, band=band)
    click.echo(
        json.dumps({
            'type': 'FeatureCollection',
            'features': list(process_features(features, query, interp_kind))
        }))


def process_features(features, query, interp_kind):
    """Assign elevations to individual GeoJSON features
    """
    for feature in features:
        f = geojson.loads(json.dumps(feature))
        yield geojson.utils.map_tuples(
            lambda t: _add_elevation_to_tuple(
                t, query=query, interp_kind=interp_kind), f)


def _add_elevation_to_tuple(t, query, interp_kind):
    try:
        ele = query.query_points([t], interp_kind=interp_kind)[0]
    except NoDataException:
        if len(t) == 3:
            ele = t[2]
        else:
            ele = -9999

    return (t[0], t[1], ele)


if __name__ == '__main__':
    main()
