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
from mta.runtime.relational_state import save_image,save_export,load_image,load_export,iter_image,iter_export,read_daily

SCHEMA='fresh-derived-report-generation-v1'
CONSUMERS=('ExcessProjection','FulfillmentProjection','ExpediteProjection','PickPostProjection')


def recipe_identity():
    from mta.domain import deferred_dbm_exports,btr_finalization
    from mta.presentation import excess_storage,fulfillment_storage,expedite_storage,pick_post_storage
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(_build),
        exports=inspect.getsource(deferred_dbm_exports),btr=inspect.getsource(btr_finalization),
        consumers={m.__name__:inspect.getsource(m) for m in
            (excess_storage,fulfillment_storage,expedite_storage,pick_post_storage)}))


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


def generation(run):
    row=DailyReportGeneration.objects.filter(run=run,status='READY').first()
    if (row is None or row.version!=1 or row.source_digest!=run.production_digest
            or row.recipe_digest!=recipe_identity() or row.digest!=digest(row.metadata)
            or row.metadata.get('schema')!=SCHEMA):
        raise ValueError('Derived report generation is not ready or its identity differs')
    if row.metadata['consumers']!=consumer_metadata(run):
        raise ValueError('Derived consumer receipt drift')
    return row


def image_metadata(run,path):
    return generation(run).metadata['images'].get(path)


def include_generation(run,output):
    metadata=generation(run).metadata
    for path,item in metadata['images'].items():
        output['ClosingState'][0]['btr'][path.rsplit('/',1)[1]]=load_image(run,item)
    for report in output['Reports']:
        if 'deferred' in report:
            nodes=metadata['exports'].get(report['stage'])
            if nodes is None:raise ValueError('Deferred report export missing: '+report['stage'])
            report['tables'].update({name:load_export(run,item) for name,item in nodes.items()})
            report.pop('deferred');report.pop('sources')
    output['BTRFinal']=[output['ClosingState'][0]['btr']]
    return output


def verify_rows(run,metadata):
    for item in metadata['images'].values():
        with stage('report_image_verify',image=item['image'],rows=item['count']):
            for _ in iter_image(run,item):pass
    for nodes in metadata['exports'].values():
        for item in nodes.values():
            with stage('report_export_verify',image=item['image'],rows=item['count']):
                for _ in iter_export(run,item):pass
    if consumer_metadata(run)!=metadata['consumers']:
        raise ValueError('Derived consumer receipt drift')


def _build(run):
    from mta.runtime.input_reader import read_input
    from mta.runtime.report_sources import read_routes
    from mta.domain.btr_finalization import reporting_btr,DERIVED_TABLES
    from mta.domain.deferred_dbm_exports import render
    from mta.application.native_output_contracts import validate_rows
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
        validate_rows(derived[name],'BTR/'+name,stage='report-generation/'+name)
        path='closing/btr/'+name
        images[path]=save_image(run,path,path,derived[name])
        if load_image(run,images[path])!=storage(derived[name]):
            raise ValueError('Derived BTR full typed readback differs: '+name)
    exports={}
    for report in output['Reports']:
        if 'deferred' not in report:continue
        rows=render(run.business_date,report['deferred'],report['sources'])
        exports[report['stage']]={name:save_export(run,'reports/'+report['stage']+'/'+name,values)
            for name,values in rows.items()}
        for name,item in exports[report['stage']].items():
            if load_export(run,item)!=storage(rows[name]):raise ValueError('Derived export readback differs')
    bands=read_pick_bands(run)
    calculation_digest=run.pick_projection.calculation_digest
    routes=read_routes(run,run.production_manifest['report_sources']['routes'])
    write_excess(run,output)
    write_fulfillment(run,output,calculation_digest=calculation_digest,routes=routes)
    write_expedite(run,output,bands=bands)
    write_pick_post(run,output,bands=bands)
    metadata=dict(schema=SCHEMA,images=images,exports=exports,consumers=consumer_metadata(run))
    if len(json.dumps(metadata))>1024*1024:raise ValueError('Derived report metadata exceeds its finite bound')
    verify_rows(run,metadata)
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
        row,_=DailyReportGeneration.objects.get_or_create(run=run,defaults=dict(
            source_digest=run.production_digest,recipe_digest=recipe_identity()))
        if row.source_digest!=run.production_digest or row.recipe_digest!=recipe_identity():
            raise ValueError('Report source/recipe generation changed')
        if row.status=='READY':
            row=generation(run);verify_rows(run,row.metadata);return row
        with transaction.atomic():
            row=DailyReportGeneration.objects.select_for_update().get(run=run)
            verify_root(run)
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(run.pk)])
            with stage('derived_report_build'):
                row.metadata=_build(run)
            summary('derived_report_consumers',families=len(row.metadata['consumers']))
            row.digest=digest(row.metadata);row.status='READY';row.sealed_at=timezone.now()
            row.save(update_fields=['metadata','digest','status','sealed_at'])
        return generation(run)
    finally:
        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_unlock(%s)',[lock])
