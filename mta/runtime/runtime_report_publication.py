"""Trusted PostBPR file registration under the existing scoped claim.

Other schema owner variants are deliberately not executable in this release.
Business phases are never replayed to prepare, register or read these files.
"""
from copy import deepcopy
import hashlib
import inspect
from pathlib import Path
from uuid import uuid4
import zipfile

from django.db import transaction
from mta.serialization import digest
from mta.runtime import runtime_report_candidates as candidates
from mta.runtime import runtime_report_catalogue as catalogue

SCHEMA='fresh-runtime-report-publication-v2'
FIELDS=('id','run_id','owner_kind','phase_id','scope_attempt_id','operational_attempt_id',
        'catalogue_parent_id','placement','input_digest','input_manifest_digest','source_digest',
        'profile_digest','scope_request_digest','configuration_digest','recipe_digest',
        'action_revision','action_digest','candidate_digest','catalogue_digest','metadata')


def recipe_digest():
    from mta.application import runtime_report_projection, runtime_report_encoding, runtime_report_files
    from mta.runtime import runtime_report_bpr_sources, runtime_report_phase_sources
    return digest(dict(schema=SCHEMA,modules={module.__name__:inspect.getsource(module) for module in
        (inspect.getmodule(recipe_digest),catalogue,candidates,runtime_report_projection,
         runtime_report_encoding,runtime_report_files,runtime_report_bpr_sources,runtime_report_phase_sources)}))


def _body(row):
    return {name:(str(getattr(row,name)) if name.endswith('_id') or name=='id' else getattr(row,name))
            if getattr(row,name) is not None else None for name in FIELDS}


def _request_node(run):
    values=[node for key,node in run.input_payload['tree']['object'] if key=='scope_request']
    if len(values)!=1:raise ValueError('Exact physical captured request required')
    return deepcopy(values[0])


def _configuration(run):
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_scope import PUBLICATION_SCHEMA
    from mta.runtime.scope_runtime_reports import publication_configuration,require_test_database
    raw=read_input(run,components=('scope_request','profile','pick_output_root','initialization_binding'))
    request=raw.get('scope_request')
    if (type(request) is not dict or request.get('schema')!=PUBLICATION_SCHEMA
            or request.get('scope')!='UptoBPR' or request.get('publication_recipe')!=recipe_digest()):
        raise ValueError('Captured PostBPR publication implementation required')
    require_test_database()
    config,hook,anchor=publication_configuration(request['runtime_reports'])
    if (request.get('report_hooks')!=hook
            or hook['site_code']!=raw['profile'].get('delivery',{}).get('site_code')):
        raise ValueError('Captured report hook or site differs')
    # This first release admits only the explicitly authorized new TEST seed.
    # A pre-feature nonempty custody anchor needs its own qualified reader.
    binding=raw.get('initialization_binding')
    if (anchor['kind']!='INITIALIZATION' or anchor['catalogue']!={}
            or not binding or anchor['identity']!=binding['id']
            or anchor['evidence']!={'authority':request['runtime_reports']['authority_sha256'],
                                   'source':binding['source_digest']}
            or hook['source_sha256']!=request['runtime_reports']['authority_sha256']):
        raise ValueError('Explicit initialized TEST catalogue seed authority differs')
    return raw,request,config,anchor


def _root(run,raw):
    from mta.application.operational_io import owned_path
    return owned_path(Path(raw['pick_output_root']),str(run.pk)+'/runtime-reports')


def _variables(run):
    return {'ReportsDownloadLoc':'download','TotalReqReport':'TotalReqReport_'+run.business_date.isoformat()}


def _previous(run,placement,anchor):
    if placement=='PostImporter':return None,anchor['catalogue'],anchor['last_generated']
    if placement!='PostBPR':raise ValueError('Unreleased report placement')
    previous=read(run.pk,placement='PostImporter',verify_bytes=False)
    return previous,previous.metadata['catalogue'],previous.metadata['candidate']['last_generated_after']


def _sources(phase,request,config,names):
    from mta.application.runtime_report_configuration import plan
    from mta.runtime.runtime_report_phase_sources import bind
    from mta.runtime.runtime_report_bpr_sources import bind_post_bpr
    revision=phase.metadata.get('action_revision',0)
    bound=bind(phase.pk,expected_digest=phase.digest,expected_phase=phase.phase,
        expected_action_revision=revision,expected_profile_digest=phase.snapshot.manifest['references']['profile'],
        expected_request_digest=digest(request))
    placement={'PRE_BPR':'PostImporter','BPR':'PostBPR'}[phase.phase]
    effective=deepcopy(config)
    by_id={row['Id']:row['LastGeneratedFileName'] for row in names}
    for definition in effective['RuntimeReports']:
        definition['LastGeneratedFileName']=by_id[definition['Id']]
    definitions=next(value['RuntimeReports'] for value in plan(effective,'Full') if value['placement']==placement)
    result={}
    for definition in definitions:
        rows,provenance=bind_post_bpr(bound,definition=definition)
        result[definition['Id']]=dict(sources=rows,provenance=provenance)
    return bound,definitions,result


def _content(definitions,inputs,candidate):
    """Independently compare source-derived CSV bytes, including ZIP members."""
    from mta.application.runtime_report_projection import project
    from mta.application.runtime_report_encoding import chunks
    for definition,event in zip(definitions,candidate['reports']):
        hasher=hashlib.sha256();size=0
        for chunk in chunks(definition,project(definition,inputs[definition['Id']]['sources'])['rows']):
            hasher.update(chunk);size+=len(chunk)
        for receipt in event['write']:
            if definition['Compression']:
                expected=[dict(name=event['last_generated_file_name']+'.csv',ordinal=0,
                               sha256=hasher.hexdigest(),size_bytes=size)]
                if receipt['members']!=expected:raise ValueError('Source-derived archive member differs')
            elif (receipt['sha256'],receipt['size_bytes'],receipt['members'])!=(hasher.hexdigest(),size,[]):
                raise ValueError('Source-derived report bytes differ')


def _archive(*,root,staging,members,destination):
    from mta.application.operational_io import owned_path
    target=owned_path(root,destination)
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for member in members:archive.write(owned_path(root,staging+'/'+member),arcname=member)
    return dict(protocol='existing-scoped-ZIP_DEFLATED')


def prepare(attempt_id,worker_token,*,phase_id,compatibility_digest,candidate_id=None,
            expected_candidate_digest=None):
    """Complete one required placement; recovery reuses accepted typed phase."""
    from mta.runtime.models import RunPhaseAcceptance,RuntimeReportPublication
    from mta.runtime.scope_execution import require_claim,_setting
    from mta.runtime.production_scope import authorize
    from mta.runtime.scope_runtime_reports import require_publication_writer
    require_publication_writer()
    if not transaction.get_autocommit():raise ValueError('Report preparation requires autocommit')
    authorize()
    with transaction.atomic():
        attempt,run=require_claim(attempt_id,worker_token,compatibility_digest=compatibility_digest)
        phase=RunPhaseAcceptance.objects.select_related('run','snapshot').get(pk=phase_id,run=run,state_sealed=True)
        placement={'PRE_BPR':'PostImporter','BPR':'PostBPR'}.get(phase.phase)
        if placement is None:raise ValueError('Released publication phase required')
        existing=RuntimeReportPublication.objects.filter(run=run,placement=placement).first()
        if existing is not None:return read(run.pk,placement=placement,verify_bytes=True)
        raw,request,config,anchor=_configuration(run)
        previous,prior_catalogue,names=_previous(run,placement,anchor)
    bound,definitions,inputs=_sources(phase,request,config,names)
    if bound.identity['action_revision']!=attempt.action_revision:
        raise ValueError('Publication cannot recapture a later action cut')
    root=_root(run,raw)
    root.mkdir(parents=True,exist_ok=True)
    if candidate_id is None:
        if expected_candidate_digest is not None:raise ValueError('Candidate digest without identity')
        candidate_id=str(uuid4())
        candidate=candidates.materialize(root=root,candidate_id=candidate_id,report_configuration=config,
            placement=placement,variables=_variables(run),last_generated=names,inputs=inputs,archive_writer=_archive)
    else:
        candidate=candidates.verify(root=root,candidate_id=candidate_id,expected_digest=expected_candidate_digest)
    folded=catalogue.validate_candidate(candidate=candidate,report_configuration=config,placement=placement,
        variables=_variables(run),last_generated=names,provenance={key:value['provenance'] for key,value in inputs.items()},
        previous_catalogue=prior_catalogue)
    _content(definitions,inputs,candidate)
    metadata=dict(schema=SCHEMA,candidate=candidate,catalogue=folded['catalogue'],
        anchor=anchor if previous is None else None,previous_digest=None if previous is None else previous.digest,
        authority=dict(request_node=_request_node(run),snapshot_digest=phase.snapshot.state_digest))
    with transaction.atomic():
        current,current_run=require_claim(attempt_id,worker_token,compatibility_digest=compatibility_digest)
        authorize()
        current_phase=RunPhaseAcceptance.objects.select_related('snapshot').get(pk=phase_id,run=current_run)
        current_raw,current_request,current_config,current_anchor=_configuration(current_run)
        current_previous,current_catalogue,current_names=_previous(current_run,placement,current_anchor)
        if (current_phase.digest!=phase.digest or current_phase.snapshot.state_digest!=phase.snapshot.state_digest
                or digest(current_request)!=digest(request) or digest(current_config)!=digest(config)
                or _request_node(current_run)!=metadata['authority']['request_node']
                or (None if current_previous is None else current_previous.digest)!=metadata['previous_digest']
                or digest(current_catalogue)!=digest(prior_catalogue) or digest(current_names)!=digest(names)
                or current.action_revision!=bound.identity['action_revision']):
            raise ValueError('Report owner/configuration/source/catalogue changed before registration')
        existing=RuntimeReportPublication.objects.filter(run=run,placement=placement).first()
        if existing is not None:return read(run.pk,placement=placement,verify_bytes=True)
        candidates.verify(root=_root(current_run,current_raw),candidate_id=candidate_id,expected_digest=candidate['digest'])
        row=RuntimeReportPublication(id=candidate_id,run=current_run,owner_kind='SCOPED_PHASE',phase=current_phase,
            scope_attempt=current,catalogue_parent=current_previous,placement=placement,
            input_digest=current_run.input_digest,input_manifest_digest=current_run.input_manifest_digest,
            source_digest=current_phase.digest,profile_digest=digest(current_raw['profile']),
            scope_request_digest=digest(current_request),configuration_digest=digest(current_config),
            recipe_digest=recipe_digest(),action_revision=current.action_revision,
            action_digest=digest(dict(phase=current_phase.digest,revision=current.action_revision)),
            candidate_digest=candidate['digest'],catalogue_digest=digest(folded['catalogue']),metadata=metadata)
        row.digest=digest(_body(row))
        with _setting('fresh.scope_worker',worker_token):row.save(force_insert=True)
        return row


def read(run_id,*,placement='PostBPR',verify_bytes=False):
    """Receipt identity/readiness only; the API still owns user authorization."""
    from mta.runtime.models import RuntimeReportPublication
    row=RuntimeReportPublication.objects.select_related('run','phase__snapshot').get(run_id=run_id,placement=placement)
    if row.digest!=digest(_body(row)) or row.metadata.get('schema')!=SCHEMA:
        raise ValueError('Runtime publication receipt identity differs')
    raw,request,config,anchor=_configuration(row.run)
    if (row.scope_request_digest!=digest(request) or row.configuration_digest!=digest(config)
            or row.profile_digest!=digest(raw['profile']) or row.input_digest!=row.run.input_digest
            or row.input_manifest_digest!=row.run.input_manifest_digest or row.recipe_digest!=recipe_digest()
            or row.source_digest!=row.phase.digest or not row.phase.state_sealed
            or row.metadata['authority']!=dict(request_node=_request_node(row.run),snapshot_digest=row.phase.snapshot.state_digest)
            or row.candidate_digest!=row.metadata['candidate']['digest']
            or row.catalogue_digest!=digest(row.metadata['catalogue'])):
        raise ValueError('Runtime publication captured authority differs')
    if verify_bytes:
        candidates.verify(root=_root(row.run,raw),candidate_id=str(row.pk),expected_digest=row.candidate_digest)
    return row
