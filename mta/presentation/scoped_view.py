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
from mta.presentation.request_scope import validated_read

SCHEMA='fresh-bpr-read-reference-v2'


def recipe_digest():
    # The finite forward-schema adapter preserves the actual59ca6cd3 graph
    # recipe only while every unchanged reader dependency matches its pin.
    from mta.presentation.runtime_report_view import legacy_view_recipe
    return legacy_view_recipe()


def verify_guards(*,publication=False,registered=False):
    frozen=import_module('mta.runtime.migrations.0218_scope_read_reference_guards')
    current=import_module('mta.runtime.migrations.0228_scope_read_action_ownership')
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
        actual=cursor.fetchall()
        forward=import_module('mta.runtime.migrations.0230_runtime_report_publication_guards')
        forward_body=forward.READ_REFERENCE_BODY
        expected=[(name,body,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
            for name,body in sorted(bodies.items())]
        alternative=[(name,forward_body if name=='guard_scope_read_reference' else body,
            False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
            for name,body in sorted(bodies.items())]
        registered_body=import_module('mta.runtime.migrations.0235_registered_scope_read_attachment').BODY
        cursor.execute("SELECT EXISTS(SELECT 1 FROM mta.django_migrations "
            "WHERE app='fresh_mta' AND name='0238_registered_read_action_cut')")
        if cursor.fetchone()==(True,):
            registered_body=import_module('mta.runtime.migrations.0238_registered_read_action_cut').BODY
        cursor.execute("SELECT EXISTS(SELECT 1 FROM mta.django_migrations "
            "WHERE app='fresh_mta' AND name='0239_production_generic_scope_read')")
        if cursor.fetchone()==(True,):
            registered_body=import_module('mta.runtime.migrations.0239_production_generic_scope_read').BODY
        registered_expected=[(name,registered_body if name=='guard_scope_read_reference' else body,
            False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
            for name,body in sorted(bodies.items())]
        allowed=((registered_expected,) if registered else
            (alternative,registered_expected) if publication else (expected,alternative,registered_expected))
        if actual not in allowed:
            raise PublicationUnavailable('bpr_read_reference_guard_body_differs')
        cursor.execute("SELECT prosrc,prosecdef,proconfig FROM pg_proc WHERE oid='mta.ingestion_watch()'::regprocedure")
        if cursor.fetchall()!=[(scoped_derived_body(cursor,minimum='0218_scope_read_reference_guards'),True,['search_path=pg_catalog, mta'])]:
            raise PublicationUnavailable('bpr_read_reference_revision_owner_differs')


def _configuration(run):
    from mta.presentation import registered_report_view
    if registered_report_view.applicable_run(run):
        return registered_report_view.configuration(run)
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_scope import CONFIGURED_SCHEMA
    request=read_input(run,components=('scope_request',)).get('scope_request')
    fields={'schema','scope','command_key','compatibility_digest','runtime_reports'}
    if type(request) is not dict:
        raise PublicationUnavailable('bpr_read_reference_configuration_required')
    if request.get('scope')=='UptoDBM':
        from mta.runtime.production_upto_dbm import SCHEMA as DBM_SCHEMA,disposition
        if set(request)!=fields|{'dispositions'} or request['schema']!=DBM_SCHEMA:
            raise PublicationUnavailable('bpr_read_reference_configuration_required')
        try:disposition(request['dispositions'])
        except ValueError as error:
            raise PublicationUnavailable('bpr_read_reference_configuration_required') from error
    elif set(request)!=fields or request.get('schema')!=CONFIGURED_SCHEMA or request.get('scope')!='UptoBPR':
        raise PublicationUnavailable('bpr_read_reference_configuration_required')
    if type(request['command_key']) is not str or not 1<=len(request['command_key'])<=120:
        raise PublicationUnavailable('bpr_read_reference_configuration_required')
    from mta.runtime.ingestion_context import sha
    sha(request['compatibility_digest'])
    scope_runtime_reports.require_test_database()
    return scope_runtime_reports.validate(request['runtime_reports']),digest(request)


def recipe_for_configuration(configuration):
    from mta.presentation import registered_report_view
    return (registered_report_view.recipe_digest()
            if registered_report_view.applicable_configuration(configuration) else recipe_digest())


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
    @property
    def action_revision(self):
        from mta.presentation.scoped_read_cut import revision
        return revision(self.reference)


def _metadata(bpr,planning,git,expedite,files,configuration,request_digest,*,
              action_command=None,previous_reference=None,transition_kind=None):
    from mta.presentation.scoped_read_cut import transition
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
        input_manifest_digest=source.run.input_manifest_digest,
        action_revision=source.action_revision if action_command is None else action_command.pk,
        source_digest=source.source_digest,configuration_digest=bpr.reports.generation.configuration_digest,
        recipe_digest=recipe_for_configuration(configuration),scope_request_digest=request_digest,runtime_reports=configuration,
        bpr=bpr.read_identity,planning=planning.read_identity,git=git.read_identity,
        pick=expedite.core.pick.provenance(),expedite=expedite.read_identity,
        pick_files=dict(digest=files.digest,directory=str(files.directory),files=files.files),
        transition=transition(action_command,previous_reference,transition_kind))


def _files(phase,row):
    files=row.pick_files
    if (files.phase_id!=phase.pk or files.source_digest!=phase.digest or files.recipe_digest!=scoped_pick_files.recipe_digest()
            or files.digest!=digest(scoped_pick_files._identity(phase,files.recipe_digest,files.directory,files.files))):
        raise PublicationUnavailable('bpr_read_reference_pick_files_differ')
    return files


@validated_read
def _bind(row,expected_digest,*,retained_parent=False):
    from mta.presentation import registered_report_view
    if registered_report_view.applicable_reference(row):
        return registered_report_view.bind(row,expected_digest,retained_parent=retained_parent)
    from mta.presentation import runtime_report_view
    if runtime_report_view.applicable_reference(row):
        if retained_parent:
            raise PublicationUnavailable('postbpr_read_reference_refresh_not_released')
        return runtime_report_view.bind(row,expected_digest)
    verify_guards()
    report=row.report_generation
    if row.digest!=expected_digest or row.digest!=digest(row.metadata) or row.recipe_digest!=recipe_digest():
        raise PublicationUnavailable('bpr_read_reference_identity_differs')
    from mta.presentation import scoped_read_graph
    bpr,planning,git,expedition=scoped_read_graph.bind(row,retained_parent=retained_parent)
    configuration,request_digest=_configuration(bpr.sources.run)
    files=_files(report.phase,row)
    actual=_metadata(bpr,planning,git,expedition,files,configuration,request_digest,
        action_command=row.action_command,previous_reference=row.previous_reference,
        transition_kind=None if row.metadata['transition'] is None else row.metadata['transition']['kind'])
    if (actual!=row.metadata or row.runtime_reports_digest!=configuration['configuration_digest']
            or row.expedite_parent_generation_id!=expedition.parent.generation.pk):
        raise PublicationUnavailable('bpr_read_reference_dependencies_differ')
    return ViewBinding(row,bpr,planning,git,expedition)


def bind(reference_id,*,expected_digest):
    try:
        row=ScopeReadReference.objects.select_related('report_generation__phase__snapshot',
            'report_generation__phase__run','git_generation','expedite_parent_generation','pick_files',
            'action_command__phase_acceptance__snapshot','previous_reference__report_generation').get(pk=reference_id)
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


def _save_reference(bpr,planning,git,expedition,files,configuration,request_digest,*,
                    action_command=None,previous_reference=None,transition_kind=None):
    from mta.presentation.registered_report_view import applicable_configuration
    if not applicable_configuration(configuration):
        from mta.presentation.legacy_scope_read_compatibility import require_original_writer
        require_original_writer()
    if not connection.in_atomic_block:raise ValueError('Read reference registration requires its transaction')
    metadata=_metadata(bpr,planning,git,expedition,files,configuration,request_digest,
        action_command=action_command,previous_reference=previous_reference,transition_kind=transition_kind)
    checksum=digest(metadata)
    row=ScopeReadReference.objects.filter(digest=checksum).first()
    if row is None:
        row=ScopeReadReference(action_command=action_command,previous_reference=previous_reference,
            report_generation=bpr.reports.generation,git_generation=git.generation,
            expedite_parent_generation=expedition.parent.generation,pick_files=files,recipe_digest=recipe_for_configuration(configuration),
            runtime_reports_digest=configuration['configuration_digest'],metadata=metadata,digest=checksum)
        with _owner(row.pk):row.save(force_insert=True)
    return row,checksum


def advance_action(view,event):
    """Publish only the immutable reference for this newly sealed DBM action."""
    from mta.presentation.scoped_dbm_view import DbmViewBinding
    if (not connection.in_atomic_block or not isinstance(view,DbmViewBinding)
            or event.run_id!=view.run_id or event.phase_acceptance_id!=view.dbm_phase.pk
            or not event.state_sealed or event.scope_parent_revision!=view.action_revision):
        raise PublicationUnavailable('phase_action_reference_owner_differs')
    row,checksum=_save_reference(view.bpr,view.planning,view.git,view.expedite,view.reference.pick_files,
        view.reference.metadata['runtime_reports'],view.reference.metadata['scope_request_digest'],
        action_command=event,previous_reference=view.reference,transition_kind='ACTION')
    return ViewBinding(row,view.bpr,view.planning,view.git,view.expedite)


def _save(bpr,planning,git,expedition,files,configuration,request_digest):
    row,checksum=_save_reference(bpr,planning,git,expedition,files,configuration,request_digest)
    return _bind(row,checksum)


@transaction.atomic
def prepare(phase_id,*,expected_digest,action_revision):
    phase=RunPhaseAcceptance.objects.select_related('snapshot').get(pk=phase_id)
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_scope import PUBLICATION_SCHEMA
    if read_input(phase.run,components=('scope_request',)).get('scope_request',{}).get('schema')==PUBLICATION_SCHEMA:
        from mta.presentation.runtime_report_view import prepare as prepare_publication
        return prepare_publication(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    from mta.presentation.registered_report_view import applicable_run
    if applicable_run(phase.run):
        from mta.runtime.scope_execution import _source_lock
        _source_lock(phase.run_id)
    run=CalculationRun.objects.select_for_update().get(pk=phase.run_id)
    configuration,request_digest=_configuration(run)
    from mta.presentation.registered_report_view import applicable_configuration
    if not applicable_configuration(configuration):
        from mta.presentation.legacy_scope_read_compatibility import require_original_writer
        require_original_writer()
    verify_guards(registered=applicable_configuration(configuration))
    from mta.presentation import scoped_sources
    sources=scoped_sources.bind(phase_id,expected_digest=expected_digest,action_revision=action_revision,include_nms=True,include_inherited_btr=True)
    if sources.inherited_btr is None:raise PublicationUnavailable('bpr_read_reference_inherited_btr_required')
    scoped_requests.bind(sources)
    files=scoped_pick_files.prepare(phase_id,expected_digest=expected_digest)
    # Pass admitted immutable dependencies forward instead of traversing the
    # same graph at every stage. Keep the exact optional capabilities used by
    # each public binder; they form part of downstream read identities.
    nms_sources=replace(sources,inherited_btr=None)
    plain_sources=replace(nms_sources,_images={name:item for name,item in sources._images.items()
        if name!='closing/consumer_context/NMSAllItems'})
    reports=scoped_report_storage._prepare(phase,plain_sources)
    prepared=scoped_prepared._prepare(reports,plain_sources)
    nms_prepared=replace(prepared,sources=nms_sources)
    planning=scoped_planning._prepare(nms_prepared)
    transit=scoped_transit_storage._prepare(phase,plain_sources)
    pick=scoped_pick_storage._prepare(phase,plain_sources)
    core=scoped_expedite_storage._prepare(nms_prepared,pick)
    git=scoped_git._prepare(replace(prepared,transit=transit))
    # Independent preparation is complete before briefly fencing this prefix.
    RemarkOwner.objects.select_for_update().get(pk='BPRReport_RemarkDetails')
    from mta.presentation import scoped_remarks
    remarks=scoped_remarks.bind(nms_sources,configuration_digest=reports.generation.configuration_digest)
    parent=scoped_expedite_parent._prepare(core,remarks,
        expected_core_digest=core.generation.digest,action_revision=action_revision)
    expedition=scoped_expedite.ExpediteBinding(core,parent,transit,scoped_requests.bind(sources))
    bpr=replace(prepared,sources=sources,remarks=remarks,transit=transit)
    return _save(bpr,planning,git,expedition,files,configuration,request_digest)


@transaction.atomic
def refresh_parent(reference_id,*,expected_digest):
    row=ScopeReadReference.objects.select_related('report_generation__phase__snapshot','pick_files').get(pk=reference_id)
    from mta.runtime.scope_execution import _source_lock
    from mta.runtime import scoped_remark_ownership
    _source_lock(row.report_generation.run_id)
    CalculationRun.objects.select_for_update().get(pk=row.report_generation.run_id)
    RemarkOwner.objects.select_for_update().get(pk='BPRReport_RemarkDetails')
    previous=_bind(row,expected_digest,retained_parent=True)
    from mta.presentation import scoped_remarks
    remarks=scoped_remarks.bind(previous.bpr.sources,configuration_digest=row.report_generation.configuration_digest)
    if remarks.highwater==previous.bpr.remarks.highwater:return previous
    # SQL permits retained-prefix recovery only to the registered table owner.
    # A runtime caller still needs its complete fresh canonical remark append.
    with scoped_remark_ownership.publication(row.pk,'owned-refresh'):
        parent=scoped_expedite_parent._prepare(previous.expedite.core,remarks,
            expected_core_digest=previous.expedite.core.generation.digest,
            action_revision=row.report_generation.action_revision)
        fresh=scoped_expedite.require_binding(previous.run,replace(previous.expedite,parent=parent))
        configuration,request_digest=_configuration(previous.run)
        result,checksum=_save_reference(replace(previous.bpr,remarks=remarks),previous.planning,previous.git,fresh,
            row.pick_files,configuration,request_digest,action_command=row.action_command,
            previous_reference=row,transition_kind='REMARK')
    return _bind(result,checksum)
