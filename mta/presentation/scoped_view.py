"""Prepare and bind exact BPR read dependencies; never selects a serving view.

An immutable reference is distinct from required-artifact/whole-scope readiness.
No reader calls a producer, writes a generation or scans download-file bytes.
"""
from contextlib import contextmanager
from dataclasses import dataclass,replace
from importlib import import_module
import inspect

from django.core.exceptions import ObjectDoesNotExist,ValidationError
from django.db import connection,transaction,DatabaseError
from mta.presentation.context import PublicationUnavailable
from mta.presentation import (scoped_prepared,scoped_planning,scoped_git,scoped_expedite,
    scoped_report_storage,scoped_pick_storage,scoped_transit_storage,
    scoped_expedite_storage,scoped_expedite_parent,scoped_requests)
from mta.runtime import scoped_pick_files,scope_runtime_reports
from mta.runtime.models import CalculationRun,ScopeReadReference,RunPhaseAcceptance,RemarkOwner
from mta.serialization import digest

SCHEMA='fresh-bpr-read-reference-v1'


def recipe_digest():
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(inspect.getmodule(recipe_digest)),
        expedite_reader=scoped_expedite.recipe_digest()))


def verify_guards():
    frozen=import_module('mta.runtime.migrations.0218_scope_read_reference_guards')
    current=import_module('mta.runtime.migrations.0219_scope_read_test_database_casefold')
    with connection.cursor() as cursor:
        from mta.runtime.ingestion_ownership import require_guard_coverage,scoped_derived_body
        require_guard_coverage(cursor)
        cursor.execute("SELECT T.tgname,T.tgtype,P.proname,T.tgenabled,T.tgnargs,T.tgqual::text,T.tgattr::text,"
            "T.tgdeferrable,T.tginitdeferred,T.tgconstraint<>0,T.tgoldtable,T.tgnewtable,N.nspname "
            "FROM pg_trigger T JOIN pg_proc P ON P.oid=T.tgfoid JOIN pg_namespace N ON N.oid=P.pronamespace "
            "WHERE T.tgrelid='mta.fresh_mta_scopereadreference'::regclass AND NOT T.tgisinternal "
            "AND T.tgname NOT LIKE 'ingestion_watch_%%' ORDER BY 1")
        expected=[('scope_read_no_truncate',34,'deny_scope_read_truncate'),
            ('scope_read_reference_guard',31,'guard_scope_read_reference')]
        from mta.runtime.scoped_remark_ownership import verified_business_rows
        rows=verified_business_rows(cursor,cursor.fetchall())
        if rows!=[(*r,'O',0,None,'',False,False,False,None,None,'mta') for r in expected]:
            raise PublicationUnavailable('bpr_read_reference_guards_differ')
        bodies={name:frozen.SQL.split('CREATE FUNCTION mta.'+name+'()',1)[1].split('AS $guard$',1)[1].split('$guard$;',1)[0]
            for name in ('deny_scope_read_truncate','guard_scope_read_reference')}
        bodies['guard_scope_read_reference']=current.BODY
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,P.proowner=C.relowner,"
            "P.prorettype='trigger'::regtype,P.pronargs=0 FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
            "WHERE C.oid='mta.fresh_mta_scopereadreference'::regclass AND N.nspname='mta' "
            "AND P.proname=ANY(%s) ORDER BY 1",[list(bodies)])
        if cursor.fetchall()!=[(name,body,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True) for name,body in sorted(bodies.items())]:
            raise PublicationUnavailable('bpr_read_reference_guard_body_differs')
        cursor.execute("SELECT prosrc,prosecdef,proconfig FROM pg_proc WHERE oid='mta.ingestion_watch()'::regprocedure")
        if cursor.fetchall()!=[(scoped_derived_body(cursor,minimum='0218_scope_read_reference_guards'),True,['search_path=pg_catalog, mta'])]:
            raise PublicationUnavailable('bpr_read_reference_revision_owner_differs')


def _configuration(run):
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_scope import CONFIGURED_SCHEMA
    request=read_input(run,components=('scope_request',)).get('scope_request')
    if (type(request) is not dict or set(request)!={'schema','scope','command_key','compatibility_digest','runtime_reports'}
            or request['schema']!=CONFIGURED_SCHEMA or request['scope']!='UptoBPR'
            or type(request['command_key']) is not str or not 1<=len(request['command_key'])<=120):
        raise PublicationUnavailable('bpr_read_reference_configuration_required')
    from mta.runtime.ingestion_context import sha
    sha(request['compatibility_digest'])
    scope_runtime_reports.require_test_database()
    return scope_runtime_reports.validate(request['runtime_reports']),digest(request)


@dataclass(frozen=True)
class ViewBinding:
    reference: object
    bpr: object
    planning: object
    git: object
    expedite: object

    @property
    def run(self):return self.bpr.sources.run
    @property
    def run_id(self):return self.run.pk
    @property
    def pick(self):return self.expedite.core.pick
    @property
    def read_identity(self):return dict(id=str(self.reference.pk),digest=self.reference.digest)


def _metadata(bpr,planning,git,expedite,files,configuration,request_digest):
    source=bpr.sources
    if (source.run.pk!=planning.run_id or source.run.pk!=git.run_id or source.run.pk!=expedite.run_id
            or bpr.reports.generation.pk!=planning.prepared.reports.generation.pk
            or bpr.reports.generation.pk!=git.prepared.reports.generation.pk
            or bpr.reports.generation.pk!=expedite.core.prepared.reports.generation.pk
            or bpr.remarks is None or bpr.remarks.provenance()!=expedite.parent.remarks.provenance()
            or bpr.transit is None or bpr.transit.generation.pk!=expedite.transit.generation.pk
            or git.prepared.transit.generation.pk!=expedite.transit.generation.pk
            or source.inherited_btr is None):
        raise PublicationUnavailable('bpr_read_reference_dependencies_differ')
    return dict(schema=SCHEMA,run_id=str(source.run.pk),phase_id=str(source.acceptance_id),
        phase_digest=source.acceptance_digest,snapshot_digest=source.snapshot_digest,input_digest=source.run.input_digest,
        input_manifest_digest=source.run.input_manifest_digest,action_revision=source.action_revision,
        source_digest=source.source_digest,configuration_digest=bpr.reports.generation.configuration_digest,
        recipe_digest=recipe_digest(),scope_request_digest=request_digest,runtime_reports=configuration,
        bpr=bpr.read_identity,planning=planning.read_identity,git=git.read_identity,
        pick=expedite.core.pick.provenance(),expedite=expedite.read_identity,
        pick_files=dict(digest=files.digest,directory=str(files.directory),files=files.files))


def _files(phase,row):
    files=row.pick_files
    if (files.phase_id!=phase.pk or files.source_digest!=phase.digest or files.recipe_digest!=scoped_pick_files.recipe_digest()
            or files.digest!=digest(scoped_pick_files._identity(phase,files.recipe_digest,files.directory,files.files))):
        raise PublicationUnavailable('bpr_read_reference_pick_files_differ')
    return files


def _bind(row,expected_digest,*,retained_parent=False):
    verify_guards()
    report=row.report_generation;revision=report.action_revision
    if row.digest!=expected_digest or row.digest!=digest(row.metadata) or row.recipe_digest!=recipe_digest():
        raise PublicationUnavailable('bpr_read_reference_identity_differs')
    expedition=scoped_expedite._load(row.metadata['expedite'],retained_parent=retained_parent)
    bpr=scoped_prepared.bind(report.pk,expected_digest=row.metadata['bpr']['projection_digest'],
        expected_report_digest=report.digest,action_revision=revision,include_inherited_btr=True,include_nms=True,
        include_remarks=True,transit_generation_id=expedition.transit.generation.pk,
        expected_transit_digest=expedition.transit.generation.digest)
    if retained_parent:bpr=replace(bpr,remarks=expedition.parent.remarks)
    planning=scoped_planning.bind(report.pk,expected_digest=row.metadata['planning']['planning_digest'],
        expected_source_digest=bpr.projection.digest,expected_report_digest=report.digest,action_revision=revision)
    git=scoped_git.bind(row.git_generation_id,expected_digest=row.metadata['git']['digest'],action_revision=revision)
    configuration,request_digest=_configuration(bpr.sources.run)
    files=_files(report.phase,row)
    actual=_metadata(bpr,planning,git,expedition,files,configuration,request_digest)
    if (actual!=row.metadata or row.runtime_reports_digest!=configuration['configuration_digest']
            or row.expedite_parent_generation_id!=expedition.parent.generation.pk):
        raise PublicationUnavailable('bpr_read_reference_dependencies_differ')
    return ViewBinding(row,bpr,planning,git,expedition)


def bind(reference_id,*,expected_digest):
    try:
        row=ScopeReadReference.objects.select_related('report_generation__phase__snapshot','pick_files').get(pk=reference_id)
        return _bind(row,expected_digest)
    except (ObjectDoesNotExist,KeyError,TypeError,ValueError,ValidationError) as error:
        raise PublicationUnavailable('bpr_read_reference_unavailable') from error


@contextmanager
def _owner(reference_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_read_reference',true)");previous=cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config('fresh.scope_read_reference',%s,true)",[str(reference_id)])
    try:yield
    except DatabaseError:
        transaction.set_rollback(True)
        raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:cursor.execute("SELECT set_config('fresh.scope_read_reference',%s,true)",[previous])


def _save(bpr,planning,git,expedition,files,configuration,request_digest):
    metadata=_metadata(bpr,planning,git,expedition,files,configuration,request_digest);checksum=digest(metadata)
    row=ScopeReadReference.objects.filter(digest=checksum).first()
    if row is None:
        row=ScopeReadReference(report_generation=bpr.reports.generation,git_generation=git.generation,
            expedite_parent_generation=expedition.parent.generation,pick_files=files,recipe_digest=recipe_digest(),
            runtime_reports_digest=configuration['configuration_digest'],metadata=metadata,digest=checksum)
        with _owner(row.pk):row.save(force_insert=True)
    return _bind(row,checksum)


@transaction.atomic
def prepare(phase_id,*,expected_digest,action_revision):
    phase=RunPhaseAcceptance.objects.get(pk=phase_id)
    run=CalculationRun.objects.select_for_update().get(pk=phase.run_id)
    configuration,request_digest=_configuration(run)
    verify_guards()
    from mta.presentation import scoped_sources
    sources=scoped_sources.bind(phase_id,expected_digest=expected_digest,action_revision=action_revision,include_nms=True,include_inherited_btr=True)
    if sources.inherited_btr is None:raise PublicationUnavailable('bpr_read_reference_inherited_btr_required')
    scoped_requests.bind(sources)
    files=scoped_pick_files.prepare(phase_id,expected_digest=expected_digest)
    report=scoped_report_storage.prepare(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    projection=scoped_prepared.prepare(report.pk,expected_report_digest=report.digest,action_revision=action_revision)
    planning=scoped_planning.prepare(report.pk,expected_source_digest=projection.digest,expected_report_digest=report.digest,action_revision=action_revision)
    transit=scoped_transit_storage.prepare(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    pick=scoped_pick_storage.prepare(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    core=scoped_expedite_storage.prepare(report.pk,expected_report_digest=report.digest,expected_source_digest=projection.digest,
        pick_generation_id=pick.pk,expected_pick_digest=pick.digest,action_revision=action_revision)
    git=scoped_git.prepare(report.pk,expected_report_digest=report.digest,expected_source_digest=projection.digest,
        transit_generation_id=transit.pk,expected_transit_digest=transit.digest,action_revision=action_revision)
    # Independent preparation is complete before briefly fencing this prefix.
    RemarkOwner.objects.select_for_update().get(pk='BPRReport_RemarkDetails')
    parent=scoped_expedite_parent.prepare(core.pk,expected_core_digest=core.digest,action_revision=action_revision)
    parent=scoped_expedite_parent.bind(parent.pk,expected_digest=parent.digest,action_revision=action_revision)
    expedition=scoped_expedite.ExpediteBinding(parent.core,parent,
        scoped_transit_storage.bind(transit.pk,expected_digest=transit.digest,action_revision=action_revision),scoped_requests.bind(sources))
    bpr=scoped_prepared.bind(report.pk,expected_digest=projection.digest,expected_report_digest=report.digest,action_revision=action_revision,
        include_inherited_btr=True,include_nms=True,include_remarks=True,transit_generation_id=transit.pk,expected_transit_digest=transit.digest)
    return _save(bpr,scoped_planning.bind(report.pk,expected_digest=planning.digest,expected_source_digest=projection.digest,
        expected_report_digest=report.digest,action_revision=action_revision),scoped_git.bind(git.pk,expected_digest=git.digest,action_revision=action_revision),
        expedition,files,configuration,request_digest)


@transaction.atomic
def refresh_parent(reference_id,*,expected_digest):
    row=ScopeReadReference.objects.select_related('report_generation__phase__snapshot','pick_files').get(pk=reference_id)
    CalculationRun.objects.select_for_update().get(pk=row.report_generation.run_id)
    RemarkOwner.objects.select_for_update().get(pk='BPRReport_RemarkDetails')
    previous=_bind(row,expected_digest,retained_parent=True)
    fresh=scoped_expedite.bind(scoped_expedite.refresh_parent(row.metadata['expedite']))
    configuration,request_digest=_configuration(previous.run)
    return _save(replace(previous.bpr,remarks=fresh.parent.remarks),previous.planning,previous.git,fresh,
        row.pick_files,configuration,request_digest)
