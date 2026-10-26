"""Bounded v2 roots; row values are verified at each typed image read."""
from mta.serialization import digest

BOUNDARIES=('controls','final-bpr-bluezone','dbm-imported','final-suspensions',
            'final-suggestions','post-rule-reports','btr-insights','closing-state')
OPERATIONAL_ROSTER=('BPRReports','BTRFinal','ClosingState','DBMFinal','Lineage','PublicationContext','Reports')


OPERATIONAL_ROSTER_V3=('ClosingState','Lineage','PublicationContext','ReportSourceFacts')


def operational_roster(run):
    return OPERATIONAL_ROSTER_V3 if run.production_manifest.get('version')==3 else OPERATIONAL_ROSTER


def output_root(run):
    version=run.production_manifest.get('version')
    return digest(dict(schema='fresh-operational-output-v3' if version==3 else 'fresh-operational-output-v2',
        input_digest=run.input_digest,input_manifest_digest=run.input_manifest_digest,
        production_digest=run.production_digest,roster=list(operational_roster(run)),
        boundaries=list(BOUNDARIES)))


def verify_root(run):
    if run.status!='SUCCEEDED':raise ValueError('Only a completed run may be read as an output')
    if (run.input_payload.get('content_digest')!=run.input_digest
            or digest(run.input_payload)!=run.input_manifest_digest):
        raise ValueError('Typed daily input receipt drift')
    if (digest(run.production_manifest)!=run.production_digest
            or run.output_roster!=list(operational_roster(run)) or output_root(run)!=run.output_digest):
        raise ValueError('Operational manifest/roster/root drift')
    if run.production_manifest.get('sources')!=source_receipts(run):
        raise ValueError('Required daily source receipt drift')


def verify(run):
    verify_root(run)
    audit_input(run)


def source_receipts(run):
    from mta.runtime.models import (PickProjection, ExcessProjection, FulfillmentProjection,
        ExpediteProjection, PickPostProjection, DailySourceReceipt)
    from mta.runtime.offline_rrr_models import OfflineRrrColourSource
    result={}
    models=((PickProjection,DailySourceReceipt,OfflineRrrColourSource)
            if run.production_manifest.get('version')==3 else
            (PickProjection,ExcessProjection,FulfillmentProjection,ExpediteProjection,
             PickPostProjection,DailySourceReceipt,OfflineRrrColourSource))
    for model in models:
        fields=[f.attname for f in model._meta.fields
                if f.name not in ('id','run','created_at')]
        result[model.__name__]=list(model.objects.filter(run=run).values(*fields))
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    capture = MdmDailyInputCapture.objects.select_related('source').filter(run=run).first()
    if capture is not None and capture.source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.location_transition import verified_receipt
        receipt = verified_receipt(run, capture.source)
        if receipt is not None:
            values = {f.attname:getattr(receipt,f.attname)
                for f in receipt._meta.fields if f.name != 'run'}
            values['transition_id'] = str(receipt.transition_id) if receipt.transition_id is not None else None
            result['MdmClosingProjectionReceipt'] = [values]
    from mta.serialization import storage
    from mta.mdm.native_audit import receipt as audit_receipt
    native_audit = audit_receipt(run)
    if native_audit is not None:
        result['NativeUploadAudit'] = [native_audit]
    # Only the new request's terminal set joins its root. Old receipt/root
    # identities remain byte-for-byte unchanged; there is no output-root cycle.
    request_node=next((node for key,node in run.input_payload.get('tree',{}).get('object',[])
                       if key=='scope_request'),{})
    placement_request=any(key=='schema' and node.get('scalar')=='fresh-native-report-placement-request-v1'
                          for key,node in request_node.get('object',[]))
    if placement_request:
        from mta.runtime.models import RuntimeReportPublication
        placements=list(RuntimeReportPublication.objects.filter(run=run,
            metadata__schema='fresh-runtime-report-placement-publication-v1').order_by('placement'))
        from mta.runtime.runtime_report_publication import _body
        if ({row.placement for row in placements}!=set(('PostImporter','PostBPR','PostDBM','PostBTR','Final'))
                or any(row.digest!=digest(_body(row)) for row in placements)):
            raise ValueError('Terminal runtime report publication set differs')
        result['RuntimeReportPublication']=[dict(id=str(row.pk),placement=row.placement,digest=row.digest) for row in placements]
    return storage(result)


def audit_input(run):
    if (run.input_payload.get('content_digest')!=run.input_digest
            or digest(run.input_payload)!=run.input_manifest_digest):
        raise ValueError('Typed daily input receipt drift')
    from mta.runtime.captured_input import SCHEMAS as CAPTURED, audit
    if run.input_payload.get('schema') in CAPTURED:
        return audit(run)
    from mta.runtime.relational_state import iter_image
    for metadata in run.input_payload['images'].values():
        for _ in iter_image(run,metadata):pass
    from mta.runtime.input_storage import audit_references
    audit_references(run)


def audit_output(run):
    from mta.runtime.relational_state import iter_image, iter_export
    for metadata in run.production_manifest['images'].values():
        for _ in iter_image(run,metadata):pass
    for stage in run.production_manifest['reports']:
        for node in stage['tables'].values():
            if 'export' in node:
                for _ in iter_export(run,node['export']):pass
