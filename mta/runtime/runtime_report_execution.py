"""New placement request attachments to the existing daily/phase owners.

Original requests keep their original engine path. This module arranges only
the released stage cuts and no-op hooks; calculation producers are unchanged.
Final registration is called by services.finish_run after its real writers.
"""
from dataclasses import dataclass,replace
from copy import deepcopy
from weakref import WeakKeyDictionary

from django.db import transaction
from mta.serialization import digest
from mta.application import runtime_report_bpr_inputs as bpr_inputs
from mta.application import runtime_report_postbtr_inputs as btr_inputs
from mta.application import runtime_report_btr_stage as btr_stage
from mta.application.stage_calculation_sources import capture_bpr,CalculationSources
from mta.application.native_output_contracts import native_assignments
from mta.runtime import runtime_report_request as contract
from mta.runtime import runtime_report_placement_publication as publication


class _StageAuthority:
    """Process-local attachment, never a durable owner or user-supplied proof."""
    pass


_stage_authorities=WeakKeyDictionary()


def _stage_digest(owner,sources,descriptors):
    return digest(dict(owner=owner,sources=sources,descriptors=descriptors))


def require_stage_authority(run,work):
    """Compare to the producer cut captured before candidate materialization.

    SQL still owns execution authorization. This prevents an internal caller
    from replacing prepared work with self-consistent but unrelated source
    bags. No populations are retained by the weak attachment registry.
    """
    from mta.runtime.runtime_report_stage_work import StageWork
    if type(work) is not StageWork or type(work._execution_authority) is not _StageAuthority:
        raise ValueError('Execution-issued report stage authority required')
    expected=_stage_authorities.get(work._execution_authority)
    if expected!=(str(run.pk),work.candidate_id,work.candidate['digest'],
                   _stage_digest(work.owner,work.sources,work.descriptors)):
        raise ValueError('Report stage differs from its original producer cut')


@dataclass(frozen=True)
class Completion:
    run_id: str
    request_digest: str
    work: tuple
    sources: CalculationSources
    sources_digest: str
    dbm: object = None
    attempt: object = None


def _remarks(run):
    from mta.presentation import ancillary_live
    path=ancillary_live.PATHS[ancillary_live.BOROA]
    meta=ancillary_live.image_metadata(run,path)
    rows=ancillary_live.image_rows(run,path,include_live=False)
    return rows,dict(path=path,capture=meta,include_live=False)


def _bundle_work(run,placement,bundle,*,phase=None,action_revision=0,cut,previous_work=None,admitted=None):
    admitted = publication.configuration(run) if admitted is None else admitted
    owner=publication.owner(run,placement,admitted=admitted,phase=phase,action_revision=action_revision,cut=cut)
    expected=_stage_digest(owner,bundle['sources'],bundle['descriptors'])
    work=publication.prepare(run,placement,admitted=admitted,sources=bundle['sources'],descriptors=bundle['descriptors'],
        source_owner=owner,previous_work=previous_work)
    authority=_StageAuthority()
    _stage_authorities[authority]=(str(run.pk),work.candidate_id,work.candidate['digest'],expected)
    work=replace(work,_execution_authority=authority)
    require_stage_authority(run,work)
    return work


def calculate_full(run,prior,opening_date,day,profile,execute_calculation,*,opening,
                   report_exceptions=None,prepared_master=None,master_snapshot=None):
    """Called inside execute_day's existing calculation boundary, never an entry."""
    from mta.temporal.chain import prepare_day,produce_bpr,produce_dbm
    from mta.runtime.scope_bpr_histories import complete_sources
    admitted=publication.configuration(run)
    _raw,request,_config,_anchor=admitted
    contract.validate_day(profile,day,request)
    if request['scope']!='Full' or run.scope_attempts.exists():
        raise ValueError('Placement Full requires its original unscoped day owner')
    work=[]
    def emit(placement,bundle,phase,**extra):
        cut=dict(boundaries=list(phase.completed_boundaries),**extra)
        value=_bundle_work(run,placement,bundle,cut=cut,previous_work=work[-1] if work else None,
            admitted=admitted)
        work.append(value)
    with native_assignments(True):
        phase=prepare_day(prior,opening_date,day,profile,str(run.pk),execute_calculation,
            report_exceptions,native_daily=True,prepared_master=prepared_master,master_snapshot=master_snapshot)
        emit('PostImporter',dict(sources={},descriptors={}),phase,stage='prepared-importer')
        phase=produce_bpr(phase)
        sources=complete_sources(run,capture_bpr(phase,opening),opening)
        bundle=bpr_inputs.build(phase)
        emit('PostBPR',bundle,phase,stage='completed-bpr',copies=bundle['copy_descriptors'],
             calculation_digest=sources.calculation_digest,consumer_sources_digest=digest(sources.__dict__))
        contract.hook_for(request['runtime_reports'],'PreDBM')
        phase=produce_dbm(phase)
        emit('PostDBM',dict(sources={},descriptors={}),phase,stage='completed-dbm')
        boundary=btr_stage.prepare_btr_boundary(phase,pick_source_digests=phase.pick_source_digests)
        remarks,remark_cut=_remarks(run)
        bundle=btr_inputs.build(boundary,sources=sources,frozen_remarks=remarks,color_sequence=btr_inputs.native_colours())
        emit('PostBTR',bundle,phase,stage='completed-btr-before-final',remarks=remark_cut,
             history_digest=digest({name:sources.production_reports[name]
                for name in ('BOR_OrderAllocationHistory','RRR_OrderAllocationHistory')}))
        # Private files must be complete before generic final processing starts.
        result=btr_stage.finish_btr_boundary(boundary)
    return result,Completion(str(run.pk),digest(request),tuple(work),sources,digest(sources.__dict__))


def publish_phase(attempt,receipt,value):
    """Publish exactly an accepted PRE/BPR/DBM source before advancing/releasing."""
    from mta.runtime.scope_execution import require_claim
    from mta.runtime.runtime_report_phase_sources import bind
    from mta.runtime.runtime_report_bpr_sources import bind_post_bpr
    from mta.application.runtime_report_configuration import plan
    from mta.runtime.models import RuntimeReportPublication
    contract.validate_request(value,run=attempt.run)
    placement={'PRE_BPR':'PostImporter','BPR':'PostBPR','DBM':'PostDBM'}[receipt.phase]
    with transaction.atomic():
        _current,run=require_claim(attempt.pk,attempt.worker_token,compatibility_digest=value['compatibility_digest'])
        if receipt.run_id!=run.pk:raise ValueError('Foreign report phase')
        if RuntimeReportPublication.objects.filter(run=run,placement=placement).exists():
            return publication.read(run.pk,placement=placement,verify_bytes=True)
        admitted=publication.configuration(run)
        raw,request,config,_anchor=admitted
        if request!=value:raise ValueError('Captured placement request differs')
    bound=bind(receipt.pk,expected_digest=receipt.digest,expected_phase=receipt.phase,
        expected_action_revision=attempt.action_revision,expected_profile_digest=digest(raw['profile']),
        expected_request_digest=digest(request))
    sources={};descriptors={}
    for definition in next(row['RuntimeReports'] for row in plan(config,'Full') if row['placement']==placement):
        rows,provenance=bind_post_bpr(bound,definition=definition)
        for name,bag in rows.items():
            if name in sources and digest(sources[name])!=digest(bag):raise ValueError('Shared phase source differs')
            sources[name]=bag;descriptors[name]=provenance['sources'][name]
    work=_bundle_work(run,placement,dict(sources=sources,descriptors=descriptors),
        phase=receipt,action_revision=attempt.action_revision,admitted=admitted,
        cut=dict(stage='accepted-'+receipt.phase,snapshot_digest=receipt.snapshot.state_digest))
    with transaction.atomic():
        return publication.register(run,work,attempt=attempt,worker_token=attempt.worker_token)


def calculate_tail(run,dbm,attempt,phase,sources):
    """After existing final_phase applies the exact accepted action revision."""
    admitted=publication.configuration(run)
    _raw,request,_config,_anchor=admitted
    if request['scope'] not in ('UptoBPR','UptoDBM'):
        raise ValueError('Scoped placement tail requires its captured source scope')
    # Read all required accepted reports before any new BTR work.
    for placement in ('PostImporter','PostBPR','PostDBM'):
        publication.read(run.pk,placement=placement,verify_bytes=True)
    with native_assignments(True):
        boundary=btr_stage.prepare_btr_boundary(phase,sources=sources,pick_source_digests=phase.pick_source_digests)
        remarks,remark_cut=_remarks(run)
        bundle=btr_inputs.build(boundary,sources=sources,frozen_remarks=remarks,color_sequence=btr_inputs.native_colours())
        work=_bundle_work(run,'PostBTR',bundle,phase=dbm,action_revision=attempt.action_revision,admitted=admitted,
            cut=dict(stage='completed-btr-before-final',boundaries=list(phase.completed_boundaries),
                remarks=remark_cut,action_revision=attempt.action_revision,
                dbm_state_digest=digest(phase.final_dbm)))
        result=btr_stage.finish_btr_boundary(boundary)
    return result,Completion(str(run.pk),digest(request),(work,),sources,digest(sources.__dict__),dbm,attempt)


def validate_completion(run,completion,*,scoped,sources=None):
    _raw,request,_config,_anchor=publication.configuration(run)
    if (type(completion) is not Completion or completion.run_id!=str(run.pk)
            or completion.request_digest!=digest(request)
            or type(completion.sources) is not CalculationSources
            or completion.sources_digest!=digest(completion.sources.__dict__)
            or tuple(work.placement for work in completion.work)!=
                (('PostBTR',) if scoped else ('PostImporter','PostBPR','PostDBM','PostBTR'))
            or scoped!=(request['scope']!='Full')
            or scoped and (completion.dbm is None or completion.attempt is None or completion.sources is not sources)
            or not scoped and (completion.dbm is not None or completion.attempt is not None)):
        raise ValueError('Exact placement completion calculation owner required')
    for work in completion.work:require_stage_authority(run,work)
    return completion


def register_completion(run,completion,*,final_unit=None):
    """Existing finish_run calls this after consumption/current/audit writers."""
    validate_completion(run,completion,scoped=final_unit is not None,
                        sources=completion.sources if final_unit is not None else None)
    options=({} if final_unit is None else dict(attempt=completion.attempt,
        worker_token=completion.attempt.worker_token,final_unit=final_unit))
    for work in completion.work:publication.register(run,work,**options)
    cut=dict(stage='after-native-final-writers',production_images_digest=digest(run.production_manifest['images']))
    final=_bundle_work(run,'Final',dict(sources={},descriptors={}),phase=completion.dbm,
        action_revision=0 if completion.attempt is None else completion.attempt.action_revision,cut=cut)
    return publication.register(run,final,**options)
