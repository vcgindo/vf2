"""Eight-report publication under existing phase and day-completion owners.

Only the new explicitly captured request can enter this registrar. Original
PostBPR receipts keep their unchanged registrar/recipe. Files are private until
this owner's transaction commits; no scope attempt is invented for Full.
"""
from contextlib import ExitStack,contextmanager
from copy import deepcopy
from pathlib import Path

from django.db import DatabaseError,connection,transaction
from mta.serialization import digest
from mta.runtime import runtime_report_request as request_contract
from mta.runtime import runtime_report_stage_work as stages
from mta.runtime import runtime_report_stage_storage as images
from mta.runtime.runtime_report_publication import _body,_request_node

SCHEMA='fresh-runtime-report-placement-publication-v1'
PLACEMENTS=images.PLACEMENTS


def configuration(run):
    from mta.runtime.input_reader import read_input
    from mta.runtime.scope_runtime_reports import require_test_database
    raw=read_input(run,components=('scope_request','profile','pick_output_root','initialization_binding'))
    request=request_contract.validate_read_request(raw.get('scope_request'))
    require_test_database()
    config,hook,anchor,policy=request_contract.configuration(request['runtime_reports'])
    binding=raw.get('initialization_binding')
    if (run.kind!='DAILY_CHAIN' or run.evidence_mode!='production'
            or request['report_hooks']!=hook or request['dispositions']!=policy
            or raw['profile'].get('delivery',{}).get('site_code')!=policy['site_code']
            or raw['profile'].get('daily_publication') is not True
            or anchor['kind']!='INITIALIZATION' or anchor['catalogue']!={}
            or not binding or anchor['identity']!=binding['id']
            or anchor['evidence']!={'authority':request['runtime_reports']['authority_sha256'],
                                   'source':binding['source_digest']}):
        raise ValueError('Captured placement installation/configuration authority differs')
    return raw,request,config,anchor


def root(run,raw):
    from mta.application.operational_io import owned_path
    return owned_path(Path(raw['pick_output_root']),str(run.pk)+'/runtime-reports')


def variables(run):
    return dict(ReportsDownloadLoc='download',TotalReqReport='TotalReqReport_'+run.business_date.isoformat())


def owner(run,placement,*,phase=None,action_revision=0,cut):
    """Describe an authenticated caller's cut; registration rechecks its owner."""
    raw,request,_config,_anchor=configuration(run)
    if (placement not in PLACEMENTS or type(action_revision) is not int or action_revision<0
            or type(cut) is not dict or not cut):
        raise ValueError('Explicit completed report stage cut required')
    if request['scope']=='Full':
        if phase is not None or action_revision or run.scope_attempts.exists():
            raise ValueError('Full report publication cannot fabricate scoped ownership')
        kind='FULL_COMPLETION'
    else:
        if phase is None or phase.run_id!=run.pk:
            raise ValueError('Scoped placement requires its accepted phase owner')
        expected={'PostImporter':'PRE_BPR','PostBPR':'BPR','PostDBM':'DBM',
                  'PostBTR':'DBM','Final':'DBM'}[placement]
        if phase.phase!=expected or not phase.state_sealed:
            raise ValueError('Scoped placement source cut differs')
        kind='SCOPED_PHASE' if placement in PLACEMENTS[:3] else 'SCOPED_FINAL'
    hook_name={'PostBPR':'PostBPR','PostDBM':'PostDBM','PostBTR':'PostBTR','Final':'SiteFinal'}.get(placement)
    return dict(schema=SCHEMA,kind=kind,run_id=str(run.pk),placement=placement,
        input_digest=run.input_digest,input_manifest_digest=run.input_manifest_digest,
        profile_digest=digest(raw['profile']),request_digest=digest(request),
        phase_id=None if phase is None else str(phase.pk),
        phase_digest=None if phase is None else phase.digest,action_revision=action_revision,
        hook=None if hook_name is None else request_contract.hook_for(request['runtime_reports'],hook_name),
        cut=deepcopy(cut))


def previous(run,placement,anchor):
    index=PLACEMENTS.index(placement)
    if not index:return None,anchor['catalogue'],anchor['last_generated']
    row=read(run.pk,placement=PLACEMENTS[index-1],verify_bytes=False)
    return row,row.metadata['catalogue'],row.metadata['candidate']['last_generated_after']


def prepare(run,placement,*,sources,descriptors,source_owner,previous_work=None):
    raw,_request,config,anchor=configuration(run)
    if source_owner.get('run_id')!=str(run.pk) or source_owner.get('placement')!=placement:
        raise ValueError('Placement preparation owner differs')
    if previous_work is None:
        prior,catalogue,names=previous(run,placement,anchor)
        prior_digest=None if prior is None else prior.digest
    else:
        if (type(previous_work) is not stages.StageWork or placement=='PostImporter'
                or previous_work.placement!=PLACEMENTS[PLACEMENTS.index(placement)-1]
                or previous_work.owner.get('run_id')!=str(run.pk)):
            raise ValueError('Pending Full placement predecessor differs')
        catalogue=previous_work.catalogue;names=previous_work.candidate['last_generated_after']
        # Candidate identity binds the still-private sequence; the final receipt
        # parent digest is resolved only by the atomic completion registrar.
        prior_digest=previous_work.candidate['digest']
    folder=root(run,raw);folder.mkdir(parents=True,exist_ok=True)
    return stages.prepare(root=folder,report_configuration=config,placement=placement,
        variables=variables(run),last_generated=names,previous_catalogue=catalogue,
        previous_digest=prior_digest,sources=sources,descriptors=descriptors,owner=source_owner)


@contextmanager
def _image_owner(candidate_id):
    # This private setting does not grant authority: each table/receipt guard
    # also checks captured request, actual run/worker and pending-final context.
    if transaction.get_autocommit():raise ValueError('Atomic report registrar required')
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.runtime_report_candidate',true)")
        before=cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config('fresh.runtime_report_candidate',%s,true)",[candidate_id])
    try:yield
    except DatabaseError:
        transaction.set_rollback(True)
        raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.runtime_report_candidate',%s,true)",[before])


def _context(run,work,request,*,attempt=None,worker_token=None,final_unit=None):
    from mta.runtime.models import RunPhaseAcceptance
    from mta.runtime.scope_execution import require_claim,head
    if not connection.in_atomic_block:raise ValueError('Report registration requires its transaction')
    if (work.owner.get('placement')!=work.placement or work.owner.get('run_id')!=str(run.pk)
            or work.owner.get('kind') not in ('FULL_COMPLETION','SCOPED_PHASE','SCOPED_FINAL')):
        raise ValueError('Exact publication source owner required')
    if work.owner['kind']=='FULL_COMPLETION':
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        if (request['scope']!='Full' or attempt is not None or final_unit is not None
                or worker_token is not None or run.status!='RUNNING' or run.scope_attempts.exists()
                or not MdmDailyInputCapture.objects.filter(run=run,status='CONSUMED').exists()):
            raise ValueError('Full publication requires existing consumed completion owner')
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('fresh.mdm_consuming_run',true)")
            if cursor.fetchone()[0]!=str(run.pk):raise ValueError('Full completion transaction differs')
        return None,None
    if attempt is None or worker_token is None:raise ValueError('Scoped publication requires its worker')
    if final_unit is None:
        current,owned=require_claim(attempt.pk,worker_token,compatibility_digest=request['compatibility_digest'])
    else:
        # Capture has been consumed by finish_run, so require_claim/_frozen is
        # deliberately not reused here. The pending DAY_FINAL guard owns it.
        from mta.runtime.scoped_final import require_pending_final
        require_pending_final(run,receipt_id=final_unit.pk)
        current=type(attempt).objects.select_for_update().get(pk=attempt.pk,run=run,status='ACTIVE')
        owned=run
        if (str(current.worker_token)!=str(worker_token)
                or current.compatibility_digest!=request['compatibility_digest']):
            raise ValueError('Pending final worker identity differs')
    phase=RunPhaseAcceptance.objects.get(pk=work.owner['phase_id'],run=run,state_sealed=True)
    expected={'PostImporter':'PRE_BPR','PostBPR':'BPR','PostDBM':'DBM','PostBTR':'DBM','Final':'DBM'}[work.placement]
    if (owned.pk!=run.pk or phase.digest!=work.owner['phase_digest']
            or phase.phase!=expected
            or current.action_revision!=work.owner['action_revision']
            or head(run.pk)!=(phase.phase,phase.digest)):
        raise ValueError('Scoped publication source/action cut changed')
    if work.owner['kind']=='SCOPED_FINAL':
        if final_unit is None or final_unit.phase!='DAY_FINAL' or final_unit.run_id!=run.pk:
            raise ValueError('PostBTR/Final requires existing DAY_FINAL owner')
        return current,final_unit
    if final_unit is not None or work.placement not in PLACEMENTS[:3]:
        raise ValueError('Wrong scoped publication owner')
    return current,phase


def register(run,work,*,attempt=None,worker_token=None,final_unit=None):
    """Insert only under the existing atomic phase/day owner; never commit here."""
    from mta.runtime.models import CalculationRun,RuntimeReportPublication
    from mta.runtime.production_scope import authorize
    from mta.runtime.scope_runtime_reports import require_publication_writer
    from mta.runtime.scope_execution import _setting
    if type(work) is not stages.StageWork or not connection.in_atomic_block:
        raise ValueError('Prepared work and atomic publication required')
    from mta.runtime.runtime_report_execution import require_stage_authority
    require_stage_authority(run,work)
    require_publication_writer();authorize()
    run=CalculationRun.objects.select_for_update().get(pk=run.pk)
    raw,request,config,anchor=configuration(run)
    current,phase=_context(run,work,request,attempt=attempt,worker_token=worker_token,final_unit=final_unit)
    prior,catalogue,names=previous(run,work.placement,anchor)
    expected_previous=None if prior is None else prior.digest
    # Full and scoped-final work can be assembled before their transaction. Its
    # pending previous candidate must become this exact accepted parent.
    if work.previous_digest not in (expected_previous,None if prior is None else prior.candidate_digest):
        raise ValueError('Placement catalogue predecessor changed')
    stages.verify(work,root=root(run,raw),report_configuration=config,variables=variables(run),
        last_generated=names,previous_catalogue=catalogue,previous_digest=work.previous_digest,owner=work.owner)
    expected_owner=dict(work.owner,input_digest=run.input_digest,input_manifest_digest=run.input_manifest_digest,
                        profile_digest=digest(raw['profile']),request_digest=digest(request))
    if work.owner!=expected_owner or work.owner['run_id']!=str(run.pk):
        raise ValueError('Prepared publication input owner changed')
    existing=RuntimeReportPublication.objects.filter(run=run,placement=work.placement).first()
    if existing is not None:
        # Never adopt a different materialization as this invocation's result.
        if str(existing.pk)!=work.candidate_id or existing.candidate_digest!=work.candidate['digest']:
            raise ValueError('Placement already committed with a different candidate')
        return read(run.pk,placement=work.placement,verify_bytes=True)
    with ExitStack() as context:
        if current is not None:context.enter_context(_setting('fresh.scope_worker',worker_token))
        context.enter_context(_image_owner(work.candidate_id))
        saved=stages.persist_sources(run,work)
        metadata=dict(schema=SCHEMA,candidate=deepcopy(work.candidate),catalogue=deepcopy(work.catalogue),
            anchor=anchor if prior is None else None,previous_digest=expected_previous,
            authority=dict(request_node=_request_node(run),owner=deepcopy(work.owner),images=saved))
        row=RuntimeReportPublication(id=work.candidate_id,run=run,owner_kind=work.owner['kind'],
            phase=phase,scope_attempt=current,operational_attempt=None,catalogue_parent=prior,
            placement=work.placement,input_digest=run.input_digest,input_manifest_digest=run.input_manifest_digest,
            source_digest=digest(metadata['authority']),profile_digest=digest(raw['profile']),
            scope_request_digest=digest(request),configuration_digest=digest(config),
            recipe_digest=request_contract.recipe_digest(),action_revision=work.owner['action_revision'],
            action_digest=digest(dict(phase=work.owner['phase_digest'],revision=work.owner['action_revision'])),
            candidate_digest=work.candidate['digest'],catalogue_digest=digest(work.catalogue),metadata=metadata)
        row.digest=digest(_body(row))
        row.save(force_insert=True)
    return row


def read(run_id,*,placement,verify_bytes=False):
    from mta.runtime.models import RuntimeReportPublication
    from mta.runtime import runtime_report_candidates as candidates
    row=RuntimeReportPublication.objects.select_related('run','phase','scope_attempt').get(run_id=run_id,placement=placement)
    if row.digest!=digest(_body(row)) or row.metadata.get('schema')!=SCHEMA:
        raise ValueError('Placement publication receipt identity differs')
    raw,request,config,_anchor=configuration(row.run)
    authority=row.metadata['authority'];owned=authority['owner']
    if (row.source_digest!=digest(authority) or authority['request_node']!=_request_node(row.run)
            or row.scope_request_digest!=digest(request) or row.configuration_digest!=digest(config)
            or row.profile_digest!=digest(raw['profile']) or row.recipe_digest!=request_contract.recipe_digest()
            or row.input_digest!=row.run.input_digest or row.input_manifest_digest!=row.run.input_manifest_digest
            or row.candidate_digest!=row.metadata['candidate']['digest']
            or row.catalogue_digest!=digest(row.metadata['catalogue'])
            or owned['run_id']!=str(row.run_id) or owned['placement']!=placement
            or owned['kind']!=row.owner_kind or owned['action_revision']!=row.action_revision):
        raise ValueError('Placement captured/source authority differs')
    images.validate_images(authority['images'],candidate_id=str(row.pk),placement=placement)
    with connection.cursor() as cursor:
        cursor.execute('SELECT mta.runtime_report_publication_source(P) FROM mta.fresh_mta_runtimereportpublication P WHERE P.id=%s',[row.pk])
        if cursor.fetchone()!=(True,):raise ValueError('Persistent placement source/custody differs')
    if verify_bytes:
        candidates.verify(root=root(row.run,raw),candidate_id=str(row.pk),expected_digest=row.candidate_digest)
    return row
