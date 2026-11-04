"""Current pre-DBM control inputs, not a fresh DBM calculation or history grid."""
from copy import deepcopy
from types import SimpleNamespace

from django.core.exceptions import ObjectDoesNotExist

from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request
from mta.presentation import scoped_sources, scoped_inherited_btr
from mta.runtime import opening_storage, relational_state as typed, phase_state
from mta.runtime.scoped_pick_files import _accepted
from mta.runtime import scoped_actions
from mta.serialization import digest, storage

ATTRIBUTES = ('SKUDescriptionTbl', 'SiteDescriptionTbl', 'SkuAttributeData',
              'SkuLocAttributeData', 'LocationAttributeData')


def _fail():
    raise PublicationUnavailable('phase_dbm_source_owner_differs')


def _opening_rows(sources, name, *, pair=None):
    inherited = sources.inherited_btr
    if inherited is None:
        _fail()
    owner = inherited.owner
    table = 'DBM/' + name
    if inherited.locator['owner_kind'] == 'PREDECESSOR':
        # A terminal action can change pending Sleep after publication. Do not
        # mistake the original output image for its verified command result.
        if owner.commands.filter(phase_acceptance__isnull=True).exists():
            raise PublicationUnavailable('phase_dbm_predecessor_actions_unprepared')
        path = 'closing/dbm/' + name
        node = owner.production_manifest['closing']['dbm']['tables'].get(name)
        if node != {'image': path}:
            _fail()
        item = owner.production_manifest['images'].get(path)
    else:
        from mta.runtime.captured_input import SCHEMAS, origin
        physical = origin(sources.run) if sources.run.input_payload.get('schema') in SCHEMAS else sources.run
        path = 'input/opening/state/dbm/' + name
        found = scoped_inherited_btr._node(physical, path)
        if (found is None or type(found[0]) is not type(owner) or found[0].pk != owner.pk
                or found[0].input_manifest_digest != inherited.locator['owner_digest']):
            _fail()
        node = found[1]
        if node == {'empty': True}:
            return []  # Explicit captured empty table, never a missing owner.
        path += '/values'
        if node.get('children') != [] or node.get('records') != path:
            _fail()
        item = owner.input_payload['images'].get(path)
    if (type(item) is not dict or item.get('image') != path or item.get('table') != table
            or type(item.get('count')) is not int or item['count'] < 0
            or not isinstance(item.get('fields'), list)):
        _fail()
    columns = dict(typed.STORAGE_TABLES[table])
    seen = set()
    for field in item['fields']:
        if (not isinstance(field, (list, tuple)) or len(field) != 3
                or field[0] != field[1] or field[0] not in columns or field[0] in seen
                or field[2] not in ('str', 'int', 'float', 'bool')):
            _fail()
        seen.add(field[0])
    if inherited.locator['owner_kind'] == 'PREDECESSOR':
        from mta.runtime import dated_history_reader
        if dated_history_reader.owns(item):
            if pair is None:
                return dated_history_reader.load_image(owner, item)
            from mta.presentation.dbm_read import _selected_rows
            location = next((field for field in ('WhCode', 'WHCode', 'LocCode') if field in seen), 'WhCode')
            if item['count'] and location not in seen:
                _fail()
            return _selected_rows(owner, path, {'SKUCode': pair[0], location: pair[1]}, metadata=item)
    if item['count'] == 0 and item['digest'] != digest([]):
        _fail()
    reader = opening_storage.load_image if inherited.locator['owner_kind'] == 'INITIALIZATION' else typed.load_image
    return reader(owner, deepcopy(item))


@once_per_request
def bind(phase_id, *, expected_digest, action_revision):
    """Bind only this accepted BPR and its current validated action revision."""
    from mta.temporal.chain import native_rows, EMPTY_NATIVE_FIELDS
    from mta.application.native_output_contracts import control_fields
    try:
        sources = scoped_sources.bind(phase_id, expected_digest=expected_digest,
            action_revision=action_revision, include_inherited_btr=True)
        phase = _accepted(phase_id, expected_digest)
        if phase.phase != 'BPR' or phase.run_id != sources.run.pk:
            _fail()
        manifest = phase.snapshot.manifest
        state = {}
        for key, name in (('dbm_master', 'DBMMaster'), ('suggestions', 'Suggestions'),
                          ('acceptance', 'NormAcceptanceTbl')):
            path = manifest['state']['control_final'][key]['image']
            if path != 'phase/BPR/controls/' + key:
                _fail()
            item = scoped_sources._checked(manifest['images'].get(path))
            if item['table'] != 'DBM/' + name:
                _fail()
            state[name] = native_rows(typed.load_image(phase.run, item, table_registry=phase_state.REGISTRY),
                                     EMPTY_NATIVE_FIELDS.get(name) or control_fields(name))
        state['NormsInSleepModeTbl'] = _opening_rows(sources, 'NormsInSleepModeTbl')
        state = scoped_actions._state_after(phase.run, phase, storage(state),
            manifest['metadata'].get('action_revision', 0), expected_revision=action_revision)
        state['ReasonCodes'] = _opening_rows(sources, 'ReasonCodes')
        for name in ATTRIBUTES:
            state[name] = sources.rows('closing/importer/' + name)
        # Same SQL BIT representation as the existing pre-DBM import consumer.
        for row in state['SkuLocAttributeData']:
            if row['NonNMS'] is not None:
                row['NonNMS'] = bool(row['NonNMS'])
        if scoped_actions.revision(phase.run) != action_revision:
            _fail()
        return SimpleNamespace(run=phase.run, business_date=phase.run.business_date, dbm=state)
    except (ValueError, KeyError, TypeError, AttributeError, ObjectDoesNotExist) as error:
        if isinstance(error, PublicationUnavailable):
            raise
        raise PublicationUnavailable('phase_dbm_source_owner_differs') from error
