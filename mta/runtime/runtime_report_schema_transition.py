"""Finite 0228 -> 0230 publication extension; original seals are never replaced.

The trusted provisioner supplies an independently reviewed catalogue delta.
Existing schema-transition authority authenticates its namespace, predecessor,
target release, actual delta and preserved rows. This module limits the changed
surface and migration bytes; it is not a generic schema upgrade permission.
"""
import hashlib
from pathlib import Path

NAMES=('0229_runtime_report_publication','0230_runtime_report_publication_guards')
# Complete reviewed 0229/0230 + compatibility-table bootstrap catalogue.
# Includes generated index columns/constraints, function bodies, trigger
# bindings and ACLs. Only the registered namespace role names are portable.
# No substring/prefix can authorize an extra object or changed definition.
CATALOGUE_DELTA_DIGEST='e15845b188a2ec37bfce8e032f250be5fefb86157a437a90889b35106ab7d7a6'


def catalogue_contract(delta):
    from mta.serialization import digest
    import re
    owner=delta['functions:mta.ingestion_watch()']['before']['owner']
    consumers=[item['after']['grantee'] for name,item in delta.items()
        if name.startswith('grants:mta.fresh_mta_runtimereportpublication:')
        and item['after']['privilege']=='SELECT' and item['after']['grantee']!=owner]
    if (len(consumers)!=1 or owner==consumers[0] or
            any(not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}',role) for role in (owner,*consumers))):
        raise ValueError('Exact namespace owner and SELECT-only consumer required')
    mapping={owner:'<namespace-owner>',consumers[0]:'<namespace-consumer>'}
    def normalized(value):
        if isinstance(value,dict):return {normalized(k):normalized(v) for k,v in value.items()}
        if isinstance(value,list):return [normalized(v) for v in value]
        if isinstance(value,str):
            if value in mapping:return mapping[value]
            if value.startswith('grants:'):
                return ':'.join(mapping.get(part,part) for part in value.split(':'))
        return value
    return digest(normalized(delta))


def migration_pins():
    root=Path(__file__).parent/'migrations'
    return [[name,hashlib.sha256((root/(name+'.py')).read_bytes()).hexdigest()] for name in NAMES]


def require_specification(spec):
    if spec['migration_pins']!=migration_pins():
        raise ValueError('Exact released publication migration bytes required')
    delta=spec['catalogue_delta']
    if not isinstance(delta,dict) or not delta:
        raise ValueError('Independently reviewed publication catalogue delta required')
    try:matches=catalogue_contract(delta)==CATALOGUE_DELTA_DIGEST
    except (KeyError,TypeError,ValueError):matches=False
    if not matches:
        raise ValueError('Exact reviewed publication catalogue, guards and ACLs required')


def require_start(cursor):
    from importlib import import_module
    cursor.execute("SELECT to_regclass('fresh_control.ingestion_schema_compatibility')")
    if cursor.fetchone()!=(None,):
        raise ValueError('This publication upgrade requires the qualified unextended0228 namespace')
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
