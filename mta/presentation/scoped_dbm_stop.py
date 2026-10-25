"""Current accepted pre-BTR DBM cells and revision-bound pending actions.

Read only the typed DBM snapshot. BPR retains its own attributes/Pick owners;
this primitive neither prepares reports nor admits/selects a serving scope.
"""
from copy import deepcopy
from types import SimpleNamespace

from django.core.exceptions import ObjectDoesNotExist

from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request
from mta.presentation import scoped_sources
from mta.presentation.scoped_dbm import ATTRIBUTES
from mta.runtime import phase_state, relational_state as typed, scoped_actions
from mta.runtime.scoped_pick_files import _accepted
from mta.serialization import storage


def _fail():
    raise PublicationUnavailable('pre_btr_dbm_source_owner_differs')


def _rows(phase, name):
    """Resolve the exact DBM table without accepting a BPR or terminal alias."""
    manifest = phase.snapshot.manifest
    logical = 'phase/DBM/dbm/' + name
    if manifest['state']['final_dbm'].get(name) != {'image': logical}:
        _fail()
    item = manifest['images'].get(logical)
    if (type(item) is not dict or item.get('table') != 'DBM/'+name
            or item.get('image') != logical or type(item.get('count')) is not int
            or item['count'] < 0 or type(item.get('fields')) is not list
            or item['count'] and not item['fields']):
        _fail()
    from mta.runtime.ingestion_context import sha
    sha(item.get('digest'))
    columns = dict(phase_state.REGISTRY[item['table']])
    seen = set()
    for field in item['fields']:
        if (not isinstance(field, (list,tuple)) or len(field) != 3
                or field[0] != field[1] or field[0] not in columns or field[0] in seen
                or field[2] not in ('str','int','float','bool')):
            _fail()
        seen.add(field[0])
    return typed.load_image(phase.run, deepcopy(item), table_registry=phase_state.REGISTRY)


@once_per_request
def bind(phase_id, *, expected_digest, action_revision):
    """Bind the current DBM stop; never restore/recalculate the entire day."""
    from mta.runtime.scope_execution import head
    from mta.runtime.calculation_effects import SCHEMA as EFFECTS
    from mta.temporal.chain import native_rows, EMPTY_NATIVE_FIELDS
    from mta.application.native_output_contracts import control_fields
    try:
        phase = _accepted(phase_id, expected_digest)
        run = phase.run
        if (phase.phase != 'DBM' or run.status != 'RUNNING'
                or phase.attempt.scope != 'UptoDBM'
                or phase.metadata.get('effects',{}).get('schema') != EFFECTS
                or head(run.pk) != ('DBM', phase.digest)):
            _fail()
        parent = phase.snapshot.parent.acceptance
        sources = scoped_sources.bind(parent.pk, expected_digest=parent.digest,
            action_revision=action_revision)
        if sources.run.pk != run.pk:
            _fail()
        state = {name:native_rows(_rows(phase,name), EMPTY_NATIVE_FIELDS.get(name) or control_fields(name))
                 for name in scoped_actions.TABLES}
        state = scoped_actions._state_after(run, phase, storage(state),
            phase.snapshot.manifest['metadata'].get('action_revision',0), expected_revision=action_revision)
        state['ReasonCodes'] = _rows(phase, 'ReasonCodes')
        for name in ATTRIBUTES:
            state[name] = sources.rows('closing/importer/'+name)
        # Match the existing UI SQL BIT representation without altering storage.
        for row in state['SkuLocAttributeData']:
            if row['NonNMS'] is not None: row['NonNMS'] = bool(row['NonNMS'])
        if head(run.pk) != ('DBM',phase.digest) or scoped_actions.revision(run) != action_revision:
            _fail()
        return SimpleNamespace(run=run, business_date=run.business_date, dbm=state,
            phase_id=phase.pk, phase_digest=phase.digest, action_revision=action_revision,
            bpr_sources=sources)
    except (ValueError, KeyError, TypeError, AttributeError, ObjectDoesNotExist) as error:
        if isinstance(error, PublicationUnavailable): raise
        raise PublicationUnavailable('pre_btr_dbm_source_owner_differs') from error
