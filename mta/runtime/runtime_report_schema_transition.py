"""Finite 0228 -> 0230 publication extension; original seals are never replaced.

The trusted provisioner supplies an independently reviewed catalogue delta.
Existing schema-transition authority authenticates its namespace, predecessor,
target release, actual delta and preserved rows. This module limits the changed
surface and migration bytes; it is not a generic schema upgrade permission.
"""
import hashlib
from pathlib import Path

NAMES=('0229_runtime_report_publication','0230_runtime_report_publication_guards')
# Django truncates this generated FK index name; catalogue() also describes
# index columns. These are exact observed names, not a broader prefix grant.
INDEX_OBJECTS=frozenset((
    'index:mta.runtime_report_run_placement',
    'column:mta.runtime_report_run_placement.placement',
    'column:mta.runtime_report_run_placement.run_id',
    'index:mta.fresh_mta_runtimereportpub_operational_attempt_id_e7ad0287',
    'column:mta.fresh_mta_runtimereportpub_operational_attempt_id_e7ad0287.operational_attempt_id',
))


def migration_pins():
    root=Path(__file__).parent/'migrations'
    return [[name,hashlib.sha256((root/(name+'.py')).read_bytes()).hexdigest()] for name in NAMES]


def require_specification(spec):
    if spec['migration_pins']!=migration_pins():
        raise ValueError('Exact released publication migration bytes required')
    delta=spec['catalogue_delta']
    if not isinstance(delta,dict) or not delta:
        raise ValueError('Independently reviewed publication catalogue delta required')
    for name,change in delta.items():
        if (type(change) is not dict or set(change)!={'before','after'}
                or change['after'] is None):
            raise ValueError('Publication extension cannot remove existing objects')
        addition=('runtimereportpublication' in name or 'runtime_report_publication' in name
                  or name in INDEX_OBJECTS)
        bootstrap=('fresh_control.ingestion_schema_compatibility' in name
                   or 'fresh_control.ingestion_schema_transition' in name)
        replaced=name in ('functions:mta.ingestion_watch()', 'functions:mta.guard_scope_read_reference()')
        if not (addition or bootstrap or replaced):
            raise ValueError('Outside the finite publication catalogue extension: '+name)
        if (addition or bootstrap) and change['before'] is not None:
            raise ValueError('Publication extension cannot replace an existing object: '+name)


def require_start(cursor):
    from importlib import import_module
    cursor.execute("SELECT name FROM mta.django_migrations WHERE app='fresh_mta' ORDER BY name DESC LIMIT 1")
    if cursor.fetchone()!=('0228_scope_read_action_ownership',):
        raise ValueError('Publication upgrade requires the exact admitted0228 start')
    cursor.execute("SELECT prosrc FROM pg_proc WHERE oid='mta.ingestion_watch()'::regprocedure")
    if cursor.fetchone()!=(import_module('mta.runtime.migrations.0228_scope_read_action_ownership').NEW,):
        raise ValueError('Publication predecessor ingestion guard differs')
    cursor.execute("SELECT prosrc FROM pg_proc WHERE oid='mta.guard_scope_read_reference()'::regprocedure")
    if cursor.fetchone()!=(import_module('mta.runtime.migrations.0228_scope_read_action_ownership').BODY,):
        raise ValueError('Publication predecessor read guard differs')
    from mta.runtime.ingestion_ownership import migration_history_guard
    if not migration_history_guard(cursor):raise ValueError('Publication migration history guard differs')


def approved_receipt(value):
    # Namespace/original certificate, old/new schema/security hashes and the
    # provisioner-owned append-only receipt are checked by effective_schema.
    return value.get('migration_pins')==migration_pins()
