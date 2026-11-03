"""Derived reporting from committed v3 facts using existing daily preparation.

A failed private build rolls back its rows and leaves the operational day intact.
No input consumption, engine execution, run rewrite or automatic selection occurs.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import inspect,json
from django.conf import settings
from django.db import connection,transaction
from django.utils import timezone
from mta.runtime.models import CalculationRun,DailyReportGeneration
from mta.serialization import digest,storage
from mta.application.stage_observation import stage,summary
from mta.presentation.request_scope import once_per_request
from mta.runtime.relational_state import save_image,save_export,load_image,load_export,iter_image,iter_export
from mta.runtime.accepted_state_read import read_accepted_daily as read_daily

SCHEMA='fresh-derived-report-generation-v1'
DATED_SCHEMA='fresh-derived-report-generation-v2'
CONSUMERS=('ExcessProjection','FulfillmentProjection','ExpediteProjection','PickPostProjection')


def recipe_identity(version=1):
    from mta.domain import deferred_dbm_exports,btr_finalization
    from mta.presentation import excess_storage,fulfillment_storage,expedite_storage,pick_post_storage
    legacy = digest(dict(schema=SCHEMA,builder=inspect.getsource(_build),
        exports=inspect.getsource(deferred_dbm_exports),btr=inspect.getsource(btr_finalization),
        consumers={m.__name__:inspect.getsource(m) for m in
            (excess_storage,fulfillment_storage,expedite_storage,pick_post_storage)}))
    if version == 1:
        return legacy
    if version != 2:
        raise ValueError('Unsupported derived report generation version')
    from mta.presentation import btr_calendar_images, btr_calendar_sources, btr_calendar
    return digest(dict(schema=DATED_SCHEMA, base=legacy, builder=inspect.getsource(_build_dated),
        storage=[inspect.getsource(module) for module in (btr_calendar_images, btr_calendar_sources, btr_calendar)]))


def consumer_metadata(run):
    from mta.runtime import models
    result={}
    for name in CONSUMERS:
        model=getattr(models,name)
        fields=[f.attname for f in model._meta.fields if f.name not in ('run','id','created_at')]
        rows=list(model.objects.filter(run=run).values(*fields))
        if len(rows)!=1:raise ValueError('Required derived consumer receipt missing: '+name)
        result[name]=storage(rows)
    return result


@once_per_request
def generation(run):
    row=DailyReportGeneration.objects.filter(run=run,status='READY').first()
    if (row is None or row.version not in (1,2) or row.source_digest!=run.production_digest
            or row.recipe_digest!=recipe_identity(row.version) or row.digest!=digest(row.metadata)
            or row.metadata.get('schema')!=(SCHEMA if row.version==1 else DATED_SCHEMA)):
        raise ValueError('Derived report generation is not ready or its identity differs')
    if row.version == 2:
        from mta.presentation.btr_calendar_sources import TRENDS, validate
        from mta.presentation import btr_calendar_images as calendar
        validate(run, row.metadata['btr_calendar'])
        dated_paths = {path for path, item in row.metadata['images'].items() if calendar.owns(item)}
        if dated_paths != {'closing/btr/'+name for name in TRENDS}:
            raise ValueError('Dated BTR generation storage roster differs')
    if row.metadata['consumers']!=consumer_metadata(run):
        raise ValueError('Derived consumer receipt drift')
    return row


def image_metadata(run,path):
    return generation(run).metadata['images'].get(path)


def include_generation(run,output):
    from mta.presentation import btr_calendar_images as calendar
    metadata=generation(run).metadata
    for path,item in metadata['images'].items():
        output['ClosingState'][0]['btr'][path.rsplit('/',1)[1]]=(
            calendar.load(run,metadata['btr_calendar'],item) if calendar.owns(item) else load_image(run,item))
    for report in output['Reports']:
        if 'deferred' in report:
            nodes=metadata['exports'].get(report['stage'])
            if nodes is None:raise ValueError('Deferred report export missing: '+report['stage'])
            report['tables'].update({name:load_export(run,item) for name,item in nodes.items()})
            report.pop('deferred');report.pop('sources')
    output['BTRFinal']=[output['ClosingState'][0]['btr']]
    return output


def verify_rows(run,metadata):
    from mta.presentation import btr_calendar_images as calendar
    for item in metadata['images'].values():
        with stage('report_image_verify',image=item['image'],rows=item['count']):
            rows = (calendar.verified_rows(run,metadata['btr_calendar'],item) if calendar.owns(item)
                    else iter_image(run,item))
            for _ in rows:pass
    for nodes in metadata['exports'].values():
        for item in nodes.values():
            with stage('report_export_verify',image=item['image'],rows=item['count']):
                for _ in iter_export(run,item):pass
    if consumer_metadata(run)!=metadata['consumers']:
        raise ValueError('Derived consumer receipt drift')


def _build(run):
    from mta.runtime.input_reader import read_execution_input as read_input
    from mta.runtime.report_sources import read_routes
    from mta.domain.btr_finalization import reporting_btr,DERIVED_TABLES
    from mta.domain.deferred_dbm_exports import render
    from mta.presentation.pick_storage import read_pick_bands
    from mta.presentation.excess_storage import write_excess
    from mta.presentation.fulfillment_storage import write_fulfillment
    from mta.presentation.expedite_storage import write_expedite
    from mta.presentation.pick_post_storage import write_pick_post
    output=read_daily(run)
    closing=output['ClosingState'][0]
    facts={**closing['consumer_context'],**closing['importer'],**closing['dbm'],
        'vf_RationedReqReport':output['BPRReports'][0]['vf_RationedReqReport']}
    profile=read_input(run,components=('profile',))['profile']
    delivery=profile['delivery']
    derived=reporting_btr(run.business_date,closing['btr'],facts,delivery['btr_settings'],
        importer_vf_settings=delivery.get('btr_history',{}).get('importer_vf_settings'))
    images={}
    for name in sorted(DERIVED_TABLES):
        path='closing/btr/'+name
        images[path]=save_image(run,path,path,derived[name])
    exports={}
    for report in output['Reports']:
        if 'deferred' not in report:continue
        rows=render(run.business_date,report['deferred'],report['sources'])
        exports[report['stage']]={name:save_export(run,'reports/'+report['stage']+'/'+name,values)
            for name,values in rows.items()}
    bands=read_pick_bands(run)
    calculation_digest=run.pick_projection.calculation_digest
    routes=read_routes(run,run.production_manifest['report_sources']['routes'])
    write_excess(run,output)
    write_fulfillment(run,output,calculation_digest=calculation_digest,routes=routes)
    write_expedite(run,output,bands=bands)
    write_pick_post(run,output,bands=bands)
    metadata=dict(schema=SCHEMA,images=images,exports=exports,consumers=consumer_metadata(run))
    if len(json.dumps(metadata))>1024*1024:raise ValueError('Derived report metadata exceeds its finite bound')
    return metadata


def _build_dated(run):
    # _build is the source-pinned v1 recipe used to verify and retry retained
    # publications. Both versions invoke the same domain producer.
    from mta.presentation import btr_calendar_images as calendar
    from mta.presentation.btr_calendar_sources import TRENDS, advance
    predecessor = run.predecessor if run.predecessor_id else None
    prior_directory = None
    if predecessor is not None and DailyReportGeneration.objects.filter(run=predecessor,version=2).exists():
        prior_directory = generation(predecessor).metadata['btr_calendar']
    directory = advance(run, predecessor=predecessor if prior_directory is not None else None,
                        directory=prior_directory)
    from mta.runtime.input_reader import read_execution_input as read_input
    from mta.runtime.report_sources import read_routes
    from mta.domain.btr_finalization import reporting_btr,DERIVED_TABLES
    from mta.domain.deferred_dbm_exports import render
    from mta.presentation.pick_storage import read_pick_bands
    from mta.presentation.excess_storage import write_excess
    from mta.presentation.fulfillment_storage import write_fulfillment
    from mta.presentation.expedite_storage import write_expedite
    from mta.presentation.pick_post_storage import write_pick_post
    output=read_daily(run)
    closing=output['ClosingState'][0]
    facts={**closing['consumer_context'],**closing['importer'],**closing['dbm'],
        'vf_RationedReqReport':output['BPRReports'][0]['vf_RationedReqReport']}
    profile=read_input(run,components=('profile',))['profile']
    delivery=profile['delivery']
    derived=reporting_btr(run.business_date,closing['btr'],facts,delivery['btr_settings'],
        importer_vf_settings=delivery.get('btr_history',{}).get('importer_vf_settings'))
    images={}
    for name in sorted(DERIVED_TABLES):
        path='closing/btr/'+name
        if name in TRENDS:
            images[path] = calendar.save(run, directory, name, derived[name])
        else:
            images[path] = save_image(run, path, path, derived[name])
    exports={}
    for report in output['Reports']:
        if 'deferred' not in report:continue
        rows=render(run.business_date,report['deferred'],report['sources'])
        exports[report['stage']]={name:save_export(run,'reports/'+report['stage']+'/'+name,values)
            for name,values in rows.items()}
    bands=read_pick_bands(run)
    calculation_digest=run.pick_projection.calculation_digest
    routes=read_routes(run,run.production_manifest['report_sources']['routes'])
    write_excess(run,output)
    write_fulfillment(run,output,calculation_digest=calculation_digest,routes=routes)
    write_expedite(run,output,bands=bands)
    write_pick_post(run,output,bands=bands)
    metadata=dict(schema=DATED_SCHEMA,btr_calendar=directory,images=images,exports=exports,consumers=consumer_metadata(run))
    if len(json.dumps(metadata))>1024*1024:raise ValueError('Derived report metadata exceeds its finite bound')
    return metadata


def prepare(run_id,*,expected_output_digest):
    if not transaction.get_autocommit():raise ValueError('Report generation owns its transaction')
    run=CalculationRun.objects.get(pk=run_id)
    if run.production_manifest.get('version')!=3:return None
    from mta.runtime.receipt_integrity import verify_root
    verify_root(run)
    if run.output_digest!=expected_output_digest or str(run.pk)==str(settings.VF_MTA_PUBLISHED_RUN):
        raise ValueError('Explicit unselected operational run required')
    lock=int.from_bytes(run.pk.bytes[:8],'big',signed=True)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(%s)',[lock])
        if not cursor.fetchone()[0]:raise ValueError('Report preparation already running')
    try:
        from functools import cache
        from mta.runtime.btr_import_image import report_version
        candidate_version = cache(lambda: report_version(run))
        row,_=DailyReportGeneration.objects.get_or_create(run=run,defaults=dict(version=candidate_version,
            source_digest=run.production_digest,recipe_digest=lambda: recipe_identity(candidate_version())))
        if row.status=='READY':
            return generation(run)
        if row.source_digest!=run.production_digest or row.recipe_digest!=recipe_identity(row.version):
            raise ValueError('Report source/recipe generation changed')
        with transaction.atomic():
            row=DailyReportGeneration.objects.select_for_update().get(run=run)
            verify_root(run)
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(run.pk)])
            with stage('derived_report_build'):
                row.metadata=_build_dated(run) if row.version==2 else _build(run)
            summary('derived_report_consumers',families=len(row.metadata['consumers']))
            row.digest=digest(row.metadata);row.status='READY';row.sealed_at=timezone.now()
            row.save(update_fields=['metadata','digest','status','sealed_at'])
        return generation(run)
    finally:
        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_unlock(%s)',[lock])
