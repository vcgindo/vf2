"""Finite code-only recovery of the owned25Oct archive-prefix failure.

Authenticate the old frozen request; never rewrite it or widen worker authority.
All native code except this adapter and its two entry files must be unchanged.
"""
import json
from pathlib import Path
from django.db import connection,transaction
from mta.serialization import digest

RUN='2d44682e-524f-4657-8847-fd2cab5ee7bc'
FAILED='174c7588-40f1-4665-aaf9-d22341d57a66'
INITIALIZATION='ed6ce944-372d-4038-aec4-89f91131648c'
BPR='19d1f6a2-e250-4199-a69b-6a362f390b81'
BPR_DIGEST='13bd908a4683df2c8b8ed82859cbb5ff294d39711fddfda7e16b3200daf057b0'
INPUT='504edbee7e69fcbcd7252e4e0479642992eac1a748eeb87ef5285b7b42d0528d'
INPUT_MANIFEST='228d56aea55a0122bb1921460d7bc9bd932497a24da75fb14aa8cbd36a12e741'
COMPATIBILITY='53741529ad8d462bb3e61aeafb6df35ba8afa2a6c11190ea697242841d5ba3b0'
PREVIOUS=dict(schema='vectorflow-native-release-source-v1',
    source_commit='0fbcd5e8b82f4b8449065fbd6e665bd4cf02d63d',
    manifest_sha256='bc48a8129fbb52c9271725ac8d665d3855a7a29f8d32295dc63af9862d5e02bd',
    source_files_digest='17ed7de28fbef5be201e7e570203619308853c2dde7d2fa921fc65b37cdcb12c',
    migrations_digest='769b73d976ad8b4c2e28ca0dbbdb6dac9e937554a13f14fa66ff8277c58bd67d',
    implementation_sha256='9a6b0f781076eaceb4ee43b39ade2de08ad80a500636873a96c4fd124bcd48a4')
ENTRY_FILES=frozenset(('mta/runtime/production_upto_dbm.py',
    'mta/runtime/scoped_dbm_archive_recovery.py',
    'mta/runtime/management/commands/run_production_upto_dbm.py'))
PROTECTED='6081a7198d7db5c6e7ac77b912cbbe6bab6dd6b45ef4c87710f08c6c814c6e2d'


def unchanged_sources(files):
    if (not ENTRY_FILES<=files.keys()
            or digest({name:pin for name,pin in files.items() if name not in ENTRY_FILES})!=PROTECTED):
        raise ValueError('Archive recovery cannot change other native source or migration bytes')


def frozen_request(frozen,current,phase_recipe):
    if (type(frozen) is not dict or set(frozen)!=set(current)
            or any(frozen[k]!=current[k] for k in current if k!='compatibility_digest')
            or frozen.get('compatibility_digest')!=COMPATIBILITY
            or digest(dict(request={k:v for k,v in frozen.items() if k!='compatibility_digest'},
                release=PREVIOUS,phase_recipe=phase_recipe))!=COMPATIBILITY):
        raise ValueError('Archive recovery cannot change its frozen request or phase recipe')
    return frozen


def resolve(current,*,recovery_of,initialization_id):
    from release.native_identity import require_current,MANIFEST
    from mta.runtime import ingestion_authority as authority,scoped_dbm_transition
    from mta.runtime.ingestion_admission import _admit,effective_schema
    from mta.runtime.models import CalculationRun,RunScopeAttempt
    from mta.runtime.input_reader import read_input
    from mta.runtime.phase_state import recipe_digest
    from mta.runtime.scope_execution import _source_lock,head
    from mta.runtime.scoped_pick_files import _accepted
    if str(initialization_id)!=INITIALIZATION or not transaction.get_autocommit():
        raise ValueError('Exact owned archive recovery initialization/transaction required')
    release=require_current()
    if release==PREVIOUS:raise ValueError('Corrected archive entry release required')
    unchanged_sources(json.loads((Path(__file__).resolve().parents[2]/MANIFEST).read_bytes())['files'])
    with transaction.atomic(),connection.cursor() as cursor:
        _source_lock(RUN)
        run=CalculationRun.objects.select_for_update().get(pk=RUN)
        if (run.status!='RUNNING' or run.input_digest!=INPUT or run.input_manifest_digest!=INPUT_MANIFEST
                or run.scope_attempts.filter(status='ACTIVE').exists()):
            raise ValueError('Retained archive recovery owner differs')
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
                or new_schema[2:4]!=(scoped_dbm_transition.AFTER_SCHEMA,scoped_dbm_transition.AFTER_GUARD)):
            raise ValueError('Archive recovery requires unchanged certified code-only authority')
        frozen=frozen_request(read_input(run,components=('scope_request',))['scope_request'],current,recipe_digest())
        failed=RunScopeAttempt.objects.get(pk=FAILED,run=run)
        if (failed.status!='FAILED' or failed.compatibility_digest!=COMPATIBILITY
                or failed.failure!={'type':'ValueError','message':'Exclusive Fresh SQL Importer label required'}):
            raise ValueError('Exact preserved archive failure required')
        bpr=_accepted(BPR,BPR_DIGEST)
        if bpr.run_id!=run.pk:raise ValueError('Archive recovery BPR owner differs')
        latest=run.scope_attempts.order_by('-created_at','-id').first()
        boundary=head(run.pk)
        first=(latest.pk==failed.pk and str(recovery_of)==FAILED and boundary==('BPR',BPR_DIGEST)
            and not run.phase_acceptances.filter(phase='DBM').exists() and not run.commands.exists())
        repeated=(latest.recovery_of_id==failed.pk and latest.status=='RELEASED' and recovery_of is None
            and latest.compatibility_digest==COMPATIBILITY and boundary[0]=='DBM')
        if not (first or repeated):raise ValueError('Archive recovery requires its failed BPR or released recovered DBM')
    return frozen
