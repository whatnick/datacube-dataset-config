from parse import parse, compile
from pathlib import Path
import yaml
import click


@cli.command()
@click.argument('path')
@click.option('--product', help='Which product?')
@click.option('--template_path', help='Dataset yaml template file')
@click.pass_obj
def transform_metadata(path, product, template_path):
    file_paths = find_file_paths(Path(path))

    with open(str(template_path)) as fd:
        yaml_template = fd.read()

    for file_path in file_paths:
        print(file_path)
        with open(str(file_path)) as fd:
            dataset = fd.read()
        coordinates = get_coordinates(dataset)
        measurement_paths = get_measurement_paths(dataset)
        properties = get_properties(dataset)
        lineage = get_lineage(dataset)
        values = {**coordinates, **measurement_paths, **properties, **lineage}
        write_transformed_dataset(yaml_template, values)


def write_transformed_dataset(yaml_template, output_file, values):

    filled_template = yaml_template.format(**values)

    # validate and write out
    try:
        new_dataset = yaml.load(filled_template)
    except yaml.YAMLError as err:
        print(err)
    else:
        with open(output_file, 'w') as out_file:
            yaml.dump(new_dataset, out_file, default_flow_style=False)


def find_file_paths(path: Path):
    """
    Return a list of metadata yaml file path objects.
    :param path:
    :return: A generator of path objects.
    """
    for afile in path.rglob('ga-metadata.yaml'):
        yield afile


def get_coordinates(dataset):
    """
    Extract and return geometry coordinates as a list in a dictionary:

    returns

    {
      'geometry': {
                    'type' : 'Polygon',
                    'coordinates': [...]
                  }
    }

    or

    empty dictionary
    """
    pass


def get_measurements(dataset, band_grids=None):
    """
    Extract and return measurement paths in a dictionary:

    Returns

    {
      'measurements':
      {
        'coastal_aerosol': {
                             'path': path_name1,
                             'band': band_number,
                             'layer': null or 'layer_name'
                             'grid': 'ir'
                           },
        ...
      }
    }
    """
    grids_map = {m: grid for grid in band_grids for m in grid}
    measurements = dataset.measurements
    for m in measurements:
        if grids_map.get(m):
            measurements[m]['grid'] = grids_map[m]

    return {'measurements': measurements}


def get_properties(dataset, property_offsets=None):
    """
    Extract properties and return values in a dictionary:
    {
      'properties':
      {
        'datetime': time,
        'odc:creation_datetime': creation_time,
        ...
      }
    }
    """
    props = dict()
    props['datetime'] = dataset.time
    props['odc:creation_datetime'] = dataset.indexed_time

    return {'properties': props}


def get_immediate_parents(index, id):
    from datacube.drivers.postgres._fields import NativeField
    from datacube.drivers.postgres._schema import DATASET_SOURCE
    from sqlalchemy import select

    source_id = NativeField('source_id', 'source_id', DATASET_SOURCE.c.source_dataset_ref)
    classifier = NativeField('classifier', 'classifier', DATASET_SOURCE.c.classifier)

    with index._db.connect() as connection:
        results = connection.execute(
            select(
                [source_id, classifier]
            ).where(
                DATASET_SOURCE.c.dataset_ref == id
            )
        )
    return results


def get_lineage(dataset, sources):
    """
    Extract immediate parents.
    {
      'lineage':
      {
        'nbar': [id1, id2],
        'pq': [id3]
        ...
      }
    }
    """
    lineage = dict()
    for source in sources:
        lineage.get(source.classifier, []).append(source.source_id)
    return {'lineage': lineage}
