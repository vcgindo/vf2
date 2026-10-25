"""Exact processed input exports from an accepted BPR, without a completed day.

These four SQLCMD-shaped exports are only one part of InputData.zip. Physical
intake files, the applicable download setting, hook and archive owner remain
separate requirements; this reader cannot declare the scope ready.
"""
import re

from django.db import connection

from mta.application.operational_capture import CAPTURE_POLICY
from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY, capture_input_tables
from mta.application.operational_inputs import PHYSICAL_TABLES
from mta.application.operational_sqlcmd import input_table_bytes
from mta.application.operational_upload_logs import _schema
from mta.runtime import phase_state
from mta.runtime.input_reader import read_input
from mta.runtime.operational_input_source import STORAGE_BINDINGS
from mta.runtime.relational_state import load_image
from mta.runtime.scoped_actions import revision
from mta.runtime.scoped_pick_files import _accepted


def exports(phase_id, *, expected_digest, action_revision, importer_database):
    """Read all four producer bags; do not infer them from intake or later state."""
    if (type(importer_database) is not str
            or not re.fullmatch(r'VFTEST_Fresh_[A-Za-z0-9_]+', importer_database)):
        raise ValueError('Explicit owned input-export database label required')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        database = cursor.fetchone()[0]
    if importer_database.casefold() != database.casefold():
        raise ValueError('Input-export database owner differs')
    phase = _accepted(phase_id, expected_digest)
    if (phase.phase != 'BPR' or type(action_revision) is not int
            or action_revision < 0 or revision(phase.run) != action_revision):
        raise ValueError('Processed input export requires its accepted BPR action cut')
    profile = read_input(phase.run, components=('profile',))['profile']
    if (profile.get('operational_sources') != CAPTURE_POLICY
            or profile.get('operational_input_sources') != INPUT_CAPTURE_POLICY):
        raise ValueError('Explicit processed input capture policies required')
    manifest = phase.snapshot.manifest
    nodes = manifest['state'].get('operational_input_tables')
    if type(nodes) is not dict or set(nodes) != set(PHYSICAL_TABLES):
        raise ValueError('Complete accepted processed input capture required')
    populations = {}
    for name in PHYSICAL_TABLES:
        node = nodes[name]
        if type(node) is not dict or set(node) != {'image'}:
            raise ValueError('Processed input image reference differs')
        path = 'phase/BPR/operational_input_tables/' + name
        item = manifest['images'].get(node['image'])
        if (node['image'] != path or type(item) is not dict
                or item.get('image') != path or item.get('table') != STORAGE_BINDINGS[name]):
            raise ValueError('Processed input image owner differs')
        populations[name] = load_image(phase.run, item, table_registry=phase_state.REGISTRY)
    # Reuse the producer's exact field/type contract. No defaulting, deduplication
    # or reconstruction from a current master or physical input file occurs.
    checked = capture_input_tables(controls={'raw_master': populations['MasterDataRaw']},
        daily={'DailyDataRaw': populations['DailyDataRaw']}, supplier=populations)
    result = {importer_database + '_' + name + '.CSV':
        input_table_bytes(_schema['tables']['Importer/' + name], checked[name])
        for name in PHYSICAL_TABLES}
    if revision(phase.run) != action_revision:
        raise ValueError('Processed input export action cut changed')
    return result
