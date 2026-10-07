"""Scenario-bound RRR source writer; unchanged native Norm formula and gate exception."""
import hashlib
import json
import os
from collections import Counter
from decimal import Decimal
from pathlib import Path
from django.db import connection, transaction
from mta.runtime.offline_scenario import registry
from mta.runtime.offline_rrr_models import OfflineRrrColourSource, OfflineRrrColourRow
from mta.presentation import daily_rrr_colour as producer
from mta.serialization import digest, storage

VERSION = 'daily-rrr-offline-v1'


def recipe_digest():
    return digest(dict(version=VERSION,sql=producer.SOURCE_SQL_SHA256,
        files={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in
               (Path(__file__),Path(producer.__file__))}))


def validate_scope(context,bands,orders):
    pins = registry()
    if (context.get('scenario_sha256')!=pins['scenario_sha256']
            or context.get('artifact_sha256') not in {row['sha256'] for row in pins['scenarios'].values()}
            or context.get('instance_port')!=3006 or context.get('is_mto_environment')!=0
            or context.get('synthetic') is not True or context.get('order_capabilities_complete') is not True):
        raise ValueError('Unapproved offline RRR scope')
    if (not {'r1_order_route','r1_order_bpp','AllocatedOrders'} <= set(orders)
            or any(not isinstance(rows,(list,tuple)) or rows for rows in orders.values())):
        raise ValueError('Offline Norm-only RRR requires complete empty order inputs')
    for row in bands:
        if any(producer._int(row[field],field) != 0 for field in producer._BAND_INPUT_FIELDS[7:]):
            raise ValueError('Offline RRR order requirements are outside approved scope')


def produce(output, *, context):
    calculated = output['CalculationOutputs']
    names = ('r1_requirement_band','r1_advance_stock_allocation','r1_order_route','r1_order_bpp')
    capabilities = {}
    for name in names:
        matches = [row['rows'] for row in calculated if row['capability']==name]
        if len(matches)!=1:
            raise ValueError('Missing/duplicate RRR producer capability: '+name)
        capabilities[name]=matches[0]
    source = dict(rationed_report=output['BPRFinal'][0]['vf_RationedReqReport'],
        requirement_bands=capabilities['r1_requirement_band'],
        bpr_master=output['ClosingState'][0]['bpr']['BPRMaster'],
        advance_stock_allocations=capabilities['r1_advance_stock_allocation'],
        order_capabilities={**{name:capabilities[name] for name in ('r1_order_route','r1_order_bpp')},'AllocatedOrders':[]},
        context=context)
    rows = storage(producer.norm_rrr_colour_rows(**source,scope_validator=validate_scope))
    return rows,digest(source)


def write(run,output):
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    capture = MdmDailyInputCapture.objects.select_related('source').filter(run=run).first()
    if capture is None or not capture.source.receipt.get('offline_owner'):
        return
    if transaction.get_autocommit() or run.status!='RUNNING':
        raise ValueError('Offline source requires the production transaction')
    receipt = capture.source.receipt
    context = dict(run_id=str(run.pk),instance_port=3006,synthetic=True,is_mto_environment=0,
        order_capabilities_complete=True,scenario_sha256=receipt['scenario_sha256'],
        artifact_sha256=receipt['artifact_sha256'])
    rows,source_digest = produce(output,context=context)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.offline_rrr_write',%s,true)",[str(run.pk)])
    source = OfflineRrrColourSource.objects.create(run=run,input_digest=run.input_digest,
        artifact_sha256=context['artifact_sha256'],scenario_sha256=context['scenario_sha256'],
        recipe_digest=recipe_digest(),source_inputs_digest=source_digest,rows_digest=digest(rows),row_count=len(rows))
    OfflineRrrColourRow.objects.bulk_create([OfflineRrrColourRow(receipt=source,ordinal=i,**row)
        for i,row in enumerate(rows)],batch_size=500)
    if _rows(source)!=rows:
        raise ValueError('Offline RRR source typed readback differs')


def _rows(source):
    rows = storage(list(source.rows.order_by('ordinal').values(*producer.OUTPUT_FIELDS)))
    if len(rows)!=source.row_count or digest(rows)!=source.rows_digest:
        raise ValueError('Offline RRR rows changed')
    return rows


def read(run):
    source = OfflineRrrColourSource.objects.get(run=run)
    if source.input_digest!=run.input_digest or source.recipe_digest!=recipe_digest():
        raise ValueError('Offline RRR source identity differs')
    return _rows(source)


def read_published(run):
    from django.conf import settings
    from mta.runtime.offline_scenario import require_run
    from mta.presentation.daily_publication import require_ready, source_identity
    from mta.presentation.daily_activation import require_activation
    if getattr(settings, 'VF_MTA_RRR_COLOUR_EXTENSION', '') != VERSION:
        raise ValueError('Offline RRR reader is not enabled')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        if cursor.fetchone()[0] != 'daily_3006':
            raise ValueError('Offline RRR requires its owned database')
    require_run(run)
    publication = require_ready(run)
    require_activation(run, publication)
    if publication.source_digest != source_identity(run):
        raise ValueError('Offline RRR publication source differs')
    return read(run)


def proof_identity(run,path):
    """Bind actual complete SQL values to the committed typed source."""
    root = Path(os.environ['VF_EVIDENCE_ROOT']).resolve().parent
    path = Path(path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('RRR proof escaped its evidence owner')
    raw = path.read_bytes(); proof = json.loads(raw)
    source = OfflineRrrColourSource.objects.get(run=run)
    if (proof.get('status')!='PASS' or proof.get('run_id')!=str(run.pk)
            or proof.get('output_digest')!=run.output_digest
            or proof.get('producer_sha256')!=producer.SOURCE_SQL_SHA256
            or proof.get('gate')!='approved-MTO0-exception-not-canonical-gating-parity'
            or proof.get('offline_context')!={'artifact_sha256':source.artifact_sha256,
                                            'scenario_sha256':source.scenario_sha256}
            or proof.get('missing') or proof.get('extra')):
        raise ValueError('Independent RRR proof identity differs')
    def bag(rows):
        normalized=[]
        for row in rows:
            if set(row)!=set(producer.OUTPUT_FIELDS):
                raise ValueError('Incomplete RRR proof row')
            row=dict(row)
            if row['RationedCasePacks'] is not None:
                row['RationedCasePacks']=str(Decimal(str(row['RationedCasePacks'])).normalize())
            normalized.append(digest(row))
        return Counter(normalized)
    if bag(read(run))!=bag(proof['modern']) or bag(proof['modern'])!=bag(proof['legacy']):
        raise ValueError('RRR native/typed complete row bags differ')
    return dict(path=str(path.relative_to(root)),sha256=hashlib.sha256(raw).hexdigest(),
                rows_digest=source.rows_digest,source_inputs_digest=source.source_inputs_digest)


def require_proof(run):
    summary=run.parity_summary.get('offline_rrr_proof')
    if not isinstance(summary,dict):
        raise ValueError('Offline RRR independent source acceptance is missing')
    root=Path(os.environ['VF_EVIDENCE_ROOT']).resolve().parent
    if summary!=proof_identity(run,root/summary['path']):
        raise ValueError('Offline RRR accepted proof changed')
    return summary
