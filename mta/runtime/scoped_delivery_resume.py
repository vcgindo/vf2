"""Schema-authorized delivery of an already released BPR; never calculation."""
import hashlib
import json

from django.db import connection, transaction
from mta.serialization import digest


def frozen_request(frozen, current, previous_release, phase_recipe):
    if (type(frozen) is not dict or type(current) is not dict
            or set(frozen) != set(current)
            or any(frozen[k] != current[k] for k in current if k != 'compatibility_digest')
            or frozen['compatibility_digest'] != digest(dict(
                release=previous_release, phase_recipe=phase_recipe))):
        raise ValueError('Delivery resume cannot change frozen scope request or phase recipe')
    return frozen


def resolve(raw, input_sha256, current, arguments, *, specification, specification_sha256):
    """Return the original request only after authenticating the supported DDL.

    The caller must subsequently take advance's RELEASED branch. No failed or
    active attempt, capture, claim or calculation is admitted by this function.
    """
    from pathlib import Path
    from release.native_identity import require_current
    from mta.mdm.initialization_contract import object_pairs
    from mta.runtime import ingestion_authority as authority, scoped_action_transition
    from mta.runtime.ingestion_admission import _admit, _activation_metadata
    from mta.runtime.models import CalculationRun
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_daily import decode
    from mta.runtime.phase_state import recipe_digest
    from mta.runtime.scoped_pick_files import _accepted
    from mta.runtime.scope_execution import head
    if not transaction.get_autocommit():
        raise ValueError('Delivery resume owns its admission snapshot')
    with Path(specification).open('rb') as stream:
        spec_raw = stream.read(262145)
    if len(spec_raw) > 262144 or hashlib.sha256(spec_raw).hexdigest() != specification_sha256:
        raise ValueError('Independent scoped delivery transition specification differs')
    spec = json.loads(spec_raw, object_pairs_hook=object_pairs)
    scoped_action_transition.require_specification(spec)
    release = require_current()
    if spec['target_release'] != release or spec['initialization_id'] != str(arguments['initialization_id']):
        raise ValueError('Scoped delivery transition target differs')
    day = decode(raw, input_sha256)['day']['business_date']
    candidates = list(CalculationRun.objects.filter(kind='DAILY_CHAIN', business_date=day,
        execution_revision=arguments['execution_revision'],
        mdm_input_capture__source__digest=arguments['source_digest'])[:2])
    if len(candidates) != 1:
        raise ValueError('Delivery resume requires its existing unique scoped run')
    run = candidates[0]
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        cursor.execute('SELECT current_database()')
        if not cursor.fetchone()[0].lower().startswith('vftest_fresh_'):
            raise ValueError('This delivery resume requires the owned test namespace')
        _admit(cursor, spec['initialization_id'], release, pending=True)
        current_authority = authority.read(cursor, spec['initialization_id'], release['manifest_sha256'])
        extension = authority.read_schema_transition(cursor, current_authority)
        previous = authority.read(cursor, spec['initialization_id'], spec['previous_release']['manifest_sha256'])
        cert = _activation_metadata(cursor, current_authority)
        if (extension is None or extension['contract'] != authority.SCHEMA_CONTRACT
                or extension['previous_release'] != spec['previous_release']['manifest_sha256']
                or extension['migration_pins'] != spec['migration_pins']
                or extension['catalogue_delta_digest'] != digest(spec['catalogue_delta'])
                or extension['previous_authority_digest'] != digest(previous)
                or _activation_metadata(cursor, previous) != cert
                or previous['target_commit'] != spec['previous_release']['source_commit']
                or any(previous[k] != current_authority[k]
                       for k in authority.FIELDS - {'target_commit', 'target_release'})):
            raise ValueError('Scoped delivery transition authority differs')
        frozen = read_input(run, components=('scope_request',))['scope_request']
        frozen_request(frozen, current, spec['previous_release'], recipe_digest())
        latest = run.scope_attempts.order_by('-created_at', '-id').first()
        if (run.status != 'RUNNING' or latest is None or latest.status != 'RELEASED'
                or latest.scope != 'UptoBPR' or latest.command_key != frozen['command_key']
                or latest.compatibility_digest != frozen['compatibility_digest']
                or latest.input_digest != run.input_digest
                or latest.input_manifest_digest != run.input_manifest_digest
                or run.scope_attempts.filter(status='ACTIVE').exists()):
            raise ValueError('Delivery-only resume requires its latest released UptoBPR')
        phase = run.phase_acceptances.get(phase='BPR', state_sealed=True)
        _accepted(phase.pk, phase.digest)
        if head(run.pk) != ('BPR', phase.digest):
            raise ValueError('Delivery-only resume cannot advance another phase')
    return frozen
