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
    'mta/presentation/production_reports.py','mta/presentation/daily_sources.py',
    'mta/runtime/capture_preparation.py','mta/runtime/master_revisions.py',
    'mta/presentation/terminal_scoped_remarks.py','mta/presentation/selective.py'))
PROTECTED='0fdcd60c623f15618e0b20182655000ae5f08a50401f93437d5492e6181ef12e'
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


def publication_master(run,capture,producer):
    """Record actual accepted execution without changing the derived-input seal.

    Read-only retained-run comparison proved all seven PRE master populations
    exactly equal to the qualified frozen reuse basis. Intake selected reuse;
    this scoped PRE instead ran the canonical full producer. Neither fact is
    rewritten, and no ordinary Full publication acquires this exception.
    """
    from mta.runtime.production_post_dbm import AUTHORITY
    from mta.runtime.scoped_final import accepted_prefix
    from mta.runtime import scope_revisions
    from mta.runtime.master_revisions import STATIC_TABLES
    from mta.application.persistent_master import CONTRACT
    if (str(run.pk)!=AUTHORITY['run'] or run.input_digest!=AUTHORITY['input_digest']
            or run.input_manifest_digest!=AUTHORITY['input_manifest_digest']
            or capture.get('receipt_digest')!='067ffb189928dbd9bf7f54394ee5263038a7b7411dbfbdea1969c7dec2806c7d'
            or capture.get('qualified_master_reuse') is not True
            or producer!=dict(contract=CONTRACT,qualified=True,reused=False,
                configuration_digest=AUTHORITY['profile_digest'],full_master_producer_calls=1,changed_work=None)
            or producer.get('reused') is not False or producer.get('qualified') is not True
            or type(producer.get('full_master_producer_calls')) is not int):
        raise ValueError('Scoped terminal master execution provenance differs')
    _pending_owner(run)
    prefix,_=accepted_prefix(run)
    if (scope_revisions.identity(run)!=capture
            or prefix[0].digest!='64657436bc1b291ce93a62427b8593d95d4b7b88722333a3476f597eeb544452'
            or str(prefix[-1].pk)!=AUTHORITY['dbm'] or prefix[-1].digest!=AUTHORITY['dbm_digest']):
        raise ValueError('Scoped terminal master accepted provenance differs')
    for phase in prefix:
        manifest=phase.snapshot.manifest;metadata=manifest['metadata']
        if (manifest['references']['profile']!=AUTHORITY['profile_digest']
                or metadata['master_reused'] is not False or metadata['master_work'] is not None
                or metadata['master_outcome']!='APPLIED'):
            raise ValueError('Scoped terminal master producer disagrees with accepted execution')
    manifest=prefix[-1].snapshot.manifest
    roots={}
    for name in STATIC_TABLES:
        source=manifest['images'][manifest['state']['importer'][name]['image']]
        if name=='SkuLocAttributeData':
            source=terminal_pair_metadata(run,source)
        target=run.production_manifest['images']['closing/importer/'+name]
        if any(source[key]!=target[key] for key in ('count','digest','fields')):
            raise ValueError('Scoped terminal master population differs from accepted DBM: '+name)
        roots[name]=source['digest']
    return dict(producer,scoped_execution_provenance=dict(
        schema='fresh-scoped-master-execution-v1',capture_receipt=capture['receipt_digest'],
        capture_selected_reuse=True,accepted_master_reused=False,
        accepted_phases=[dict(id=str(p.pk),digest=p.digest) for p in prefix],
        terminal_static_roots=roots))


def _pending_owner(run):
    from mta.runtime.production_post_dbm import AUTHORITY
    from mta.runtime.scoped_final import require_pending_final
    from mta.runtime.models import RunPhaseAcceptance
    if str(run.pk)!=AUTHORITY['run']:
        raise ValueError('Scoped terminal master publication owner differs')
    require_pending_final(run)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_phase',true)")
        receipt_id=cursor.fetchone()[0]
    final=RunPhaseAcceptance.objects.select_related('attempt').get(pk=receipt_id,run=run,
        phase='DAY_FINAL',state_sealed=False,snapshot__isnull=True)
    attempt=final.attempt
    if (attempt.status!='ACTIVE' or attempt.scope!='PostDBM' or attempt.command_key!=COMMAND
            or attempt.compatibility_digest!=COMPATIBILITY or attempt.action_revision!=AUTHORITY['action_revision']
            or attempt.expected_phase!='DBM' or attempt.expected_receipt_digest!=AUTHORITY['dbm_digest']):
        raise ValueError('Scoped terminal master publication owner differs')
    return final


def terminal_pair_metadata(run,source):
    """The existing chain.produce_btr NonNMS wire projection, preserving NULL."""
    from mta.runtime import relational_state as typed,phase_state
    rows=typed.load_image(run,source,table_registry=phase_state.REGISTRY)
    projected=[dict(row,NonNMS=None if row['NonNMS'] is None else bool(row['NonNMS'])) for row in rows]
    columns={name.casefold():(name,kind) for name,kind in phase_state.REGISTRY[source['table']]}
    return typed.describe_rows(projected,columns,'closing/importer/SkuLocAttributeData')[0]


def _master_parent(run,base_id):
    from mta.runtime.production_post_dbm import AUTHORITY
    from mta.runtime.ingestion_models import MasterInputRevision
    from mta.runtime.master_revisions import _validate_phase,PHASE_CONTRACT
    from mta.runtime.ingestion_admission import receipt,REVISION_FIELDS
    if str(base_id)!='69a14402-3b37-45e3-97b1-2ab9fbeeb1d2':
        raise ValueError('Scoped terminal captured master base differs')
    parent=MasterInputRevision.objects.get(pk='4bdbb4a9-5045-43cc-81b6-4621de5da240',
        initialization_id=INITIALIZATION,status='ACCEPTED')
    if (parent.run_id!=run.pk or [parent.master_epoch,parent.configuration_epoch]!=[41,312]
            or parent.partitions.get('contract')!=PHASE_CONTRACT
            or parent.partitions.get('phase_id')!=AUTHORITY['dbm']
            or parent.partitions.get('phase_digest')!=AUTHORITY['dbm_digest']
            or parent.receipt_digest!=receipt({k:getattr(parent,k) for k in REVISION_FIELDS})
            or _validate_phase(parent.partitions,INITIALIZATION).pk!=run.pk):
        raise ValueError('Scoped terminal accepted master parent differs')
    ancestor=parent;seen=set()
    while str(ancestor.pk)!=str(base_id):
        if ancestor.pk in seen or ancestor.parent_id is None:
            raise ValueError('Scoped terminal master parent ancestry differs')
        seen.add(ancestor.pk);ancestor=ancestor.parent
        if (str(ancestor.initialization_id)!=INITIALIZATION or ancestor.status!='ACCEPTED'
                or ancestor.receipt_digest!=receipt({k:getattr(ancestor,k) for k in REVISION_FIELDS})):
            raise ValueError('Scoped terminal master ancestor differs')
    return parent


def promote_master(run,capture,producer,state):
    """Allocate a terminal representation cut before its producer/root is sealed."""
    from django.db.models import F
    from mta.runtime.ingestion_models import IngestionRevisionState
    _pending_owner(run)
    parent=_master_parent(run,capture['base_revision_id'])
    if (not connection.in_atomic_block or str(state.pk)!=INITIALIZATION
            or [state.master_epoch,state.configuration_epoch]!=[41,312]
            or 'scoped_execution_provenance' not in producer):
        raise ValueError('Scoped terminal master promotion cut differs')
    changed=IngestionRevisionState.objects.filter(pk=state.pk,master_epoch=41,configuration_epoch=312).update(
        master_epoch=F('master_epoch')+1)
    if changed!=1:raise ValueError('Scoped terminal master promotion raced')
    state.refresh_from_db()
    if [state.master_epoch,state.configuration_epoch]!=[42,312]:
        raise ValueError('Scoped terminal master promoted cut differs')
    promotion=dict(parent_id=str(parent.pk),captured_base_id=str(capture['base_revision_id']),
        before=[41,312],after=[42,312],parent_receipt=parent.receipt_digest)
    return dict(producer,scoped_execution_provenance=dict(producer['scoped_execution_provenance'],
        master_promotion=promotion))


def terminal_master_parent(run,initialization_id,base_id,state):
    """Revalidate promotion when the common owner accepts the terminal revision."""
    from mta.runtime.receipt_integrity import verify_root
    _pending_owner(run)
    parent=_master_parent(run,base_id)
    producer=run.production_manifest['master_preparation']
    expected=dict(parent_id=str(parent.pk),captured_base_id=str(base_id),before=[41,312],after=[42,312],
                  parent_receipt=parent.receipt_digest)
    if (str(initialization_id)!=INITIALIZATION or str(state.pk)!=INITIALIZATION
            or [state.master_epoch,state.configuration_epoch]!=[42,312]
            or producer.get('master_cut')!=[42,312]
            or producer.get('scoped_execution_provenance',{}).get('master_promotion')!=expected
            or run.production_manifest['ingestion_preparation']['base_revision_id']!=str(base_id)):
        raise ValueError('Scoped terminal master acceptance promotion differs')
    verify_root(run)
    return parent
