"""Finite code-only recovery of the retained PostDBM publication failure.

The failed command keeps its original compatibility identity. Only its terminal
source-publication adapter and this entry's recovery code may change; accepted
phases, calculations, SQL, migrations and every other native source stay pinned.
"""
import json
from pathlib import Path
from django.db import connection
from mta.serialization import digest

INITIALIZATION='dcfa9a34-18d1-4b00-b1a6-973fade774b2'
FAILED='41b725fc-9890-4c98-a602-29e33bec9e4c'
COMMAND='owned-postdbm25-20261026'
COMPATIBILITY='8f9b676cb9fbb7f1329c8022ba79e5380f6fef6569b8e0984399a0a7cb47fd5e'
PREVIOUS=dict(schema='vectorflow-native-release-source-v1',
    source_commit='c21850c8668d8cd0d86d0c18004950a821fc0d4f',
    manifest_sha256='1bbfc92e87d9b66d94c8a8acd9d50d42453b0f81b8158b86609a387b7e2eb44c',
    source_files_digest='a0fcd237d1325b1f7be19217b3e04c62abfbbd5c4b35683e5b2c5fb54ca096c8',
    migrations_digest='853464044b4d0e6892bd63ddd8fb4f4e54a61bbd21399edd935e2cb0056af859',
    implementation_sha256='12580cb13cb532927b38da248fafe8339553fc579aed35355abccfea1d666d92')
ENTRY_FILES=frozenset(('mta/runtime/production_post_dbm.py',
    'mta/runtime/scoped_postdbm_recovery.py',
    'mta/presentation/production_reports.py','mta/presentation/daily_sources.py'))
PROTECTED='ff7de7409eb7478f407315d057d1b940da10b2020f1df71bb3803e7d5da1af2c'
SCHEMA='0fab95b7876642f0d4027bd382c0df96afa08f9200030aef82340ced8fd01451'
GUARD='ad6b00d71e9dc772bea7bb8fb10b335af4eb4c553d8a002ee705c8ce2ac67c8c'


def unchanged_sources(files):
    if (not ENTRY_FILES<=files.keys()
            or digest({name:pin for name,pin in files.items() if name not in ENTRY_FILES})!=PROTECTED):
        raise ValueError('PostDBM recovery cannot change other native source or migration bytes')


def frozen_request(current,phase_recipe):
    value={key:item for key,item in current.items() if key!='compatibility_digest'}
    if (value.get('command_key')!=COMMAND
            or digest(dict(request=value,release=PREVIOUS,phase_recipe=phase_recipe))!=COMPATIBILITY):
        raise ValueError('PostDBM recovery cannot change its frozen request or phase recipe')
    return dict(value,compatibility_digest=COMPATIBILITY)


def require_chain(run,value):
    """Fence/retry can read the same chain; execution still checks its latest owner."""
    from mta.runtime.models import RunScopeAttempt
    failed=RunScopeAttempt.objects.get(pk=FAILED,run=run)
    if (failed.status!='FAILED' or failed.failure!={
            'type':'ValueError','message':'Captured production report population roster differs'}):
        raise ValueError('Exact preserved PostDBM publication failure required')
    attempt=run.scope_attempts.order_by('-created_at','-id').first()
    seen=set()
    while attempt is not None:
        if (attempt.pk in seen or attempt.run_id!=run.pk or attempt.scope!='PostDBM'
                or attempt.command_key!=COMMAND or attempt.compatibility_digest!=COMPATIBILITY
                or attempt.expected_phase!='DBM' or attempt.expected_receipt_digest!=value['dbm_digest']
                or attempt.action_revision!=value['action_revision']
                or attempt.input_digest!=value['input_digest']
                or attempt.input_manifest_digest!=value['input_manifest_digest']):
            raise ValueError('PostDBM recovery chain changed its original command owner')
        if attempt.pk==failed.pk:return
        seen.add(attempt.pk)
        parent=attempt.recovery_of
        if parent is None or parent.status!='FAILED' or attempt.attempt_no!=parent.attempt_no+1:
            break
        attempt=parent
    raise ValueError('PostDBM recovery requires its exact failed-command ancestry')


def resolve(run,current,release,phase_recipe):
    from release.native_identity import MANIFEST
    from mta.runtime import ingestion_authority as authority
    from mta.runtime.ingestion_admission import _admit,effective_schema
    from mta.runtime.input_reader import read_input
    value=frozen_request(current,phase_recipe)
    unchanged_sources(json.loads((Path(__file__).resolve().parents[2]/MANIFEST).read_bytes())['files'])
    binding=read_input(run,components=('initialization_binding',))['initialization_binding']
    if binding.get('id')!=INITIALIZATION:
        raise ValueError('PostDBM recovery initialization differs')
    with connection.cursor() as cursor:
        _admit(cursor,INITIALIZATION,release,pending=True)
        _admit(cursor,INITIALIZATION,PREVIOUS,pending=True)
        new=authority.read(cursor,INITIALIZATION,release['manifest_sha256'])
        old=authority.read(cursor,INITIALIZATION,PREVIOUS['manifest_sha256'])
        extension=authority.read_schema_transition(cursor,new)
        old_schema=effective_schema(cursor,old);new_schema=effective_schema(cursor,new)
        if (extension is None or extension['contract']!=authority.CODE_SCHEMA_CONTRACT
                or old['target_commit']!=PREVIOUS['source_commit']
                or any(new[k]!=old[k] for k in authority.FIELDS-{'target_commit','target_release'})
                or old_schema[0]!=new_schema[0] or old_schema[2:4]!=new_schema[2:4]
                or new_schema[2:4]!=(SCHEMA,GUARD)):
            raise ValueError('PostDBM recovery requires unchanged certified code-only authority')
    require_chain(run,value)
    return value
