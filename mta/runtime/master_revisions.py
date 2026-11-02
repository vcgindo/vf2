"""Accepted static-master generations reference existing committed typed owners.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from uuid import uuid4
from django.db import connection
from django.db.models import F
from mta.serialization import digest
from mta.runtime.ingestion_admission import receipt, REVISION_FIELDS

CONTRACT = 'vectorflow-static-master-partitions-v1'
PHASE_CONTRACT = 'vectorflow-phase-master-partitions-v1'
STATIC_TABLES = ('MasterData','SKUDescriptionTbl','SiteDescriptionTbl',
                 'SkuAttributeData','LocationAttributeData','SkuLocAttributeData')


def validate(value, initialization_id):
    """Validate bounded roots without reconstructing any population."""
    from mta.runtime.execution_settings import PARTITION_CONTRACT, validate_partition
    if isinstance(value,dict) and value.get('contract') == PARTITION_CONTRACT:
        return validate_partition(value,initialization_id)
    if isinstance(value,dict) and value.get('contract') == PHASE_CONTRACT:
        return _validate_phase(value,initialization_id)
    from mta.runtime.models import CalculationRun
    from mta.runtime.receipt_integrity import verify_root
    if (not isinstance(value,dict) or set(value) != {'contract','run_id','source_digest',
            'output_digest','input_manifest_digest','production_digest','roots'}
            or value['contract'] != CONTRACT or set(value['roots']) != set(STATIC_TABLES)):
        raise ValueError('Static master revision partition contract differs')
    run=CalculationRun.objects.select_related('mdm_input_capture__source').get(pk=value['run_id'])
    verify_root(run)
    from mta.runtime.models import ProductionInitialization
    owner=ProductionInitialization.objects.get(pk=initialization_id)
    if (run.mdm_input_capture.source_id != owner.source_id
            or value['source_digest'] != owner.source.digest
            or run.output_digest != value['output_digest']
            or run.input_manifest_digest != value['input_manifest_digest']
            or run.production_digest != value['production_digest']):
        raise ValueError('Static master revision source/run differs')
    for name in STATIC_TABLES:
        image=run.production_manifest['images']['closing/importer/'+name]
        expected=dict(image=image['image'], count=image['count'], digest=image['digest'],
            fields=[field for field, *_ in image['fields'] if field != 'Norm'])
        if value['roots'][name] != expected:
            raise ValueError('Static master immutable partition differs: '+name)
    return run


def _phase_roots(phase):
    result={}
    for name in STATIC_TABLES:
        path=phase.snapshot.manifest['state']['importer'][name]['image']
        if path!='phase/'+phase.phase+'/importer/'+name:
            raise ValueError('Prepared master logical image differs')
        image=phase.snapshot.manifest['images'][path]
        allowed=('phase/PRE_BPR/','phase/BPR/')+(('phase/DBM/',) if phase.phase=='DBM' else ())
        if image['table']!='Importer/'+name or not image['image'].startswith(allowed):
            raise ValueError('Prepared master physical image differs')
        result[name]=dict(image=image['image'],count=image['count'],digest=image['digest'],
            fields=[field for field,*_ in image['fields'] if field!='Norm'])
    return result


def _validate_phase(value,initialization_id):
    from mta.runtime.scoped_pick_files import _accepted
    from mta.runtime.models import ProductionInitialization
    if (set(value)!={'contract','run_id','source_digest','input_manifest_digest',
                     'phase_id','phase_digest','snapshot_digest','revision_cut','roots'}):
        raise ValueError('Prepared master partition contract differs')
    phase=_accepted(value['phase_id'],value['phase_digest'])
    owner=ProductionInitialization.objects.select_related('source').get(pk=initialization_id)
    if (phase.phase not in ('PRE_BPR','BPR','DBM') or phase.source_id!=owner.source_id
            or str(phase.run_id)!=value['run_id'] or value['source_digest']!=owner.source.digest
            or value['input_manifest_digest']!=phase.run.input_manifest_digest
            or value['snapshot_digest']!=phase.snapshot.state_digest
            or value['revision_cut']!=phase.metadata.get('revision_after')
            or phase.snapshot.manifest['references']['profile']!=owner.configuration_digest
            or value['roots']!=_phase_roots(phase)):
        raise ValueError('Prepared master accepted owner differs')
    return phase.run


def accept_phase(phase,*,released_dbm=False):
    """Publish static-master metadata in the same accepted preparation transaction."""
    from mta.runtime.input_reader import read_input
    from mta.runtime.models import ProductionInitialization
    raw=read_input(phase.run,components=('initialization_binding',))
    binding=raw.get('initialization_binding')
    if binding is None:
        return None
    owner=ProductionInitialization.objects.select_related('source').get(pk=binding['id'])
    expected=dict(id=str(owner.pk),source_digest=owner.source.digest,input_sha256=owner.input_sha256,
                  content_digest=owner.input_digest,configuration_digest=owner.configuration_digest)
    if binding!=expected:
        raise ValueError('Prepared master initialization binding differs')
    return _accept_phase(phase,owner,released_dbm=released_dbm)


def _accept_phase(phase,owner,*,released_dbm=False):
    from mta.runtime.ingestion_models import IngestionRevisionState,MasterInputRevision
    if not connection.in_atomic_block or phase.phase not in ('PRE_BPR','BPR','DBM') or not phase.state_sealed:
        raise ValueError('Prepared master acceptance requires its sealed phase transaction')
    value=dict(contract=PHASE_CONTRACT,run_id=str(phase.run_id),source_digest=owner.source.digest,
        input_manifest_digest=phase.run.input_manifest_digest,phase_id=str(phase.pk),
        phase_digest=phase.digest,snapshot_digest=phase.snapshot.state_digest,
        revision_cut=phase.metadata.get('revision_after'),roots=_phase_roots(phase))
    _validate_phase(value,owner.pk)
    from mta.runtime import scope_revisions
    captured=scope_revisions.identity(phase.run)
    cut=scope_revisions.require_current(phase.run)
    if released_dbm:
        _require_released_dbm(phase)
    if (captured is None or captured['initialization_id']!=str(owner.pk)
            or cut is None or (cut[:2]!=value['revision_cut'][:2] if released_dbm else cut!=value['revision_cut'])):
        raise ValueError('Prepared master requires its exact owned acceptance cut')
    state=IngestionRevisionState.objects.select_for_update().get(initialization_id=owner.pk)
    revisions=MasterInputRevision.objects.filter(initialization_id=owner.pk,status='ACCEPTED')
    parent=revisions.filter(master_epoch__lte=state.master_epoch,
        configuration_epoch__lte=state.configuration_epoch).order_by('-master_epoch','-configuration_epoch').first()
    if (parent is None or [state.master_epoch,state.configuration_epoch]!=cut[:2]):
        raise ValueError('Prepared master accepted configuration basis differs')
    if (parent.master_epoch,parent.configuration_epoch)==(state.master_epoch,state.configuration_epoch):
        return parent
    body=dict(id=uuid4(),initialization_id=owner.pk,parent_id=parent.pk,run_id=phase.run_id,
        master_epoch=state.master_epoch,configuration_epoch=state.configuration_epoch,partitions=value)
    candidate=MasterInputRevision.objects.create(**body,receipt_digest=receipt(body))
    candidate.status='ACCEPTED';candidate.save(update_fields=['status'])
    return candidate


def _require_released_dbm(phase):
    """A released head can complete metadata only at its own unchanged cut."""
    from mta.runtime.scope_execution import head
    latest=phase.run.scope_attempts.order_by('-created_at','-id').first()
    if (phase.phase!='DBM' or phase.run.status!='RUNNING' or latest is None
            or latest.status!='RELEASED' or latest.pk!=phase.attempt_id
            or latest.scope!='UptoDBM' or head(phase.run_id)!=('DBM',phase.digest)
            or phase.run.scope_attempts.filter(status='ACTIVE').exists()):
        raise ValueError('Master metadata completion requires its released current UptoDBM head')


def complete_dbm_metadata(phase_id,*,expected_digest):
    """Operator-only metadata append; retained phases/outputs are never rewritten.

    Normal DBM acceptance publishes this in its phase transaction. This handles
    an already released stop from the older implementation and is idempotent.
    """
    from django.db import transaction
    from mta.runtime.production_scope import authorize
    from mta.runtime.scope_execution import _source_lock
    from mta.runtime.scoped_pick_files import _accepted
    from mta.runtime.models import CalculationRun,ProductionInitialization
    from mta.runtime.input_reader import read_input
    from mta.runtime.ingestion_admission import _admit
    from release.native_identity import require_current
    if not transaction.get_autocommit():raise ValueError('Master metadata completion owns its transaction')
    authorize()
    phase=_accepted(phase_id,expected_digest)
    with transaction.atomic(),connection.cursor() as cursor:
        _source_lock(phase.run_id)
        CalculationRun.objects.select_for_update().get(pk=phase.run_id)
        phase=_accepted(phase_id,expected_digest)
        _require_released_dbm(phase)
        binding=read_input(phase.run,components=('initialization_binding',))['initialization_binding']
        owner=ProductionInitialization.objects.select_related('source').get(pk=binding['id'])
        _admit(cursor,owner.pk,require_current(),pending=True)
        return accept_phase(phase,released_dbm=True)


def accept(run, initialization_id, parent_id):
    """Called after successful typed publication, inside the SAME day commit."""
    if not connection.in_atomic_block or run.status != 'SUCCEEDED':
        raise ValueError('Static master acceptance requires atomic successful publication')
    from mta.runtime.ingestion_models import IngestionRevisionState, MasterInputRevision
    state=IngestionRevisionState.objects.select_for_update().get(initialization_id=initialization_id)
    old=MasterInputRevision.objects.get(pk=parent_id,initialization_id=initialization_id,status='ACCEPTED')
    producer=run.production_manifest.get('master_preparation',{})
    if producer.get('placement_execution_provenance') is not None:
        from mta.runtime.placement_master_publication import terminal_master_parent
        old=terminal_master_parent(run,initialization_id,parent_id,state)
    elif producer.get('scoped_execution_provenance') is not None:
        from mta.runtime.scoped_postdbm_recovery import terminal_master_parent
        old=terminal_master_parent(run,initialization_id,parent_id,state)
    if (state.master_epoch,state.configuration_epoch)==(old.master_epoch,old.configuration_epoch):
        if old.run_id is not None and old.partitions.get('contract')!=PHASE_CONTRACT:
            return old
        # First canonical producer qualification establishes a new immutable
        # input representation. This metadata generation is not business DML.
        IngestionRevisionState.objects.filter(pk=initialization_id).update(master_epoch=F('master_epoch')+1)
        state.refresh_from_db()
    from mta.runtime.models import ProductionInitialization
    owner=ProductionInitialization.objects.select_related('source').get(pk=initialization_id)
    roots={}
    for name in STATIC_TABLES:
        image=run.production_manifest['images']['closing/importer/'+name]
        roots[name]=dict(image=image['image'],count=image['count'],digest=image['digest'],
            fields=[field for field,*_ in image['fields'] if field!='Norm'])
    partitions=dict(contract=CONTRACT,run_id=str(run.pk),source_digest=owner.source.digest,
        output_digest=run.output_digest,input_manifest_digest=run.input_manifest_digest,
        production_digest=run.production_digest,roots=roots)
    body=dict(id=uuid4(),initialization_id=owner.pk,parent_id=old.pk,run_id=run.pk,
        master_epoch=state.master_epoch,configuration_epoch=state.configuration_epoch,partitions=partitions)
    candidate=MasterInputRevision.objects.create(**body,receipt_digest=receipt(body))
    candidate.status='ACCEPTED'
    candidate.save(update_fields=['status'])
    return candidate
