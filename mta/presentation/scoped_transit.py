"""Prepare finite transit bags from captured facts and accepted BPR owners.

This read-only producer grants no native/UI admission. Its caller must persist
and seal a phase-owned generation before consumers can use the returned bags.
Missing external sources or settings never borrow a terminal/old population.
"""
import inspect
from datetime import date,datetime

from mta.application import daily_transit as processor,production_source_inputs
from mta.presentation import scoped_sources
from mta.presentation.context import PublicationUnavailable
from mta.runtime.input_reader import read_input
from mta.serialization import digest,storage
from mta.row_sequences import is_record_rows
from mta.domain.complete_daily_scalars import ascii_equal
from mta.domain.dbm_conditional import validate_settings_rows

SCHEMA='fresh-bpr-transit-rows-v1'
SETTINGS_PATH='input/profile/delivery/btr_history/importer_vf_settings'


def _settings_owner(run,rows,*,path=SETTINGS_PATH):
    """Resolve this declared profile bag, including native initialization refs."""
    from mta.runtime import input_v3,captured_input
    owner=(captured_input.origin(run) if run.input_payload.get('schema') in captured_input.SCHEMAS else run)
    manifest=owner.input_payload;node=manifest['tree'];current='input'
    for part in path.split('/')[1:]:
        if 'owner_reference' in node:
            owner,manifest,_legacy=input_v3._owner_manifest(owner,current,
                manifest['owner_references'][current],input_v3._identity(owner,None,reading=True),None)
            node=input_v3._node_at(manifest,current)
        if set(node)!={'object'}:
            raise PublicationUnavailable('bpr_transit_settings_physical_owner_unavailable')
        matches=[child for name,child in node['object'] if name==part]
        if len(matches)!=1:raise PublicationUnavailable('bpr_transit_settings_physical_owner_unavailable')
        node=matches[0];current+='/'+part
    image=manifest['images'].get(node.get('records'))
    if (image is None or image['table']!='Importer/VFSettings'
            or image['count']!=len(rows) or image['digest']!=digest(rows)):
        raise PublicationUnavailable('bpr_transit_settings_physical_owner_differs')
    return dict(path=path,owner_kind=owner._meta.model_name,owner_id=str(owner.pk),
        input_manifest_digest=owner.input_manifest_digest,image=image)


def _opening_settings(phase):
    """Read the same pre-day VFSettings owner used by native Full.

    This does not read current mutable masters or reconstruct a missing bag.
    A successor must use its own accepted predecessor; a root resolves its
    captured initialization reference and verifies the exact binding.
    """
    from datetime import timedelta
    from mta.runtime import captured_input,opening_storage,relational_state
    from mta.presentation.scoped_inherited_btr import _node
    from mta.runtime.models import CalculationRun,RunCommand
    from mta.runtime.receipt_integrity import verify_root
    run=phase.run
    physical=captured_input.origin(run) if run.input_payload.get('schema') in captured_input.SCHEMAS else run
    raw=read_input(run,components=('lineage','initialization_binding','profile'))
    if digest(raw['profile'])!=phase.snapshot.manifest['references']['profile']:
        raise PublicationUnavailable('bpr_transit_captured_profile_differs')
    binding=raw.get('initialization_binding')
    if not binding:raise PublicationUnavailable('bpr_transit_settings_initialization_unavailable')
    if run.predecessor_id is None:
        path='input/opening/state/dbm/VFSettings'
        found=_node(physical,path)
        if found is None:raise PublicationUnavailable('bpr_transit_settings_unavailable')
        owner,node=found
        if (owner._meta.model_name!='productioninitialization'
                or owner.source_id!=phase.source_id
                or owner.opening_date+timedelta(days=1)!=run.business_date
                or binding!=dict(id=str(owner.pk),source_digest=owner.source.digest,
                    input_sha256=owner.input_sha256,content_digest=owner.input_digest,
                    configuration_digest=owner.configuration_digest)):
            raise PublicationUnavailable('bpr_transit_settings_initialization_differs')
        item=owner.input_payload['images'].get(node.get('records'))
        if item is None or item.get('table')!='Importer/VFSettings':
            raise PublicationUnavailable('bpr_transit_settings_physical_owner_differs')
        rows=list(opening_storage.load_image(owner,item))
        locator=_settings_owner(run,rows,path=path)
        return rows,locator
    parent=CalculationRun.objects.get(pk=run.predecessor_id)
    lineage=raw.get('lineage') or {}
    if (parent.kind!='DAILY_CHAIN' or parent.status!='SUCCEEDED'
            or parent.business_date+timedelta(days=1)!=run.business_date
            or parent.mdm_input_capture.source_id!=phase.source_id
            or parent.mdm_input_capture.status!='CONSUMED'
            or lineage.get('run_id')!=str(parent.pk)
            or lineage.get('output_digest')!=parent.output_digest):
        raise PublicationUnavailable('bpr_transit_settings_predecessor_differs')
    verify_root(parent)
    previous=read_input(parent,components=('initialization_binding','profile'))
    if previous.get('initialization_binding')!=binding or digest(previous['profile'])!=digest(raw['profile']):
        raise PublicationUnavailable('bpr_transit_settings_predecessor_differs')
    commands=[]
    for event in RunCommand.objects.filter(run=parent,phase_acceptance__isnull=True).order_by('id'):
        if digest(event.payload)!=event.digest:
            raise PublicationUnavailable('bpr_transit_settings_predecessor_differs')
        commands.append(dict(id=event.pk,digest=event.digest,before=event.before_digest,after=event.after_digest))
    if lineage.get('commands')!=commands:
        raise PublicationUnavailable('bpr_transit_settings_predecessor_differs')
    opening=_node(physical,'input/opening')
    if opening is None or opening[1]!={'scalar':None}:
        raise PublicationUnavailable('bpr_transit_settings_predecessor_differs')
    path='closing/dbm/VFSettings'
    item=parent.production_manifest['images'].get(path)
    if item is None or item.get('image')!=path or item.get('table')!='Importer/VFSettings':
        raise PublicationUnavailable('bpr_transit_settings_physical_owner_differs')
    rows=list(relational_state.load_image(parent,item))
    return rows,dict(path=path,owner_kind='calculationrun',owner_id=str(parent.pk),
        output_digest=parent.output_digest,input_manifest_digest=parent.input_manifest_digest,image=item)


def recipe_digest():
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(inspect.getmodule(produce)),
        sources=inspect.getsource(scoped_sources),processor=inspect.getsource(processor),
        intake=inspect.getsource(production_source_inputs)))


def produce(phase_id,*,expected_digest,action_revision):
    sources=scoped_sources.bind(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    run=sources.run
    raw=read_input(run,components=('day','profile'))
    day=raw.get('day',{})
    required=('shipment_input','transporter_input','production_report_policy','production_report_opening')
    if any(name not in day or name in required[:2] and day[name] is None for name in required):
        raise PublicationUnavailable('bpr_transit_captured_sources_unavailable')
    # The intake validator retains a list contract, including when typed input
    # uses a lazy RecordRows bag. Only these two explicit sources materialize.
    def materialize(value):
        return (dict(value,rows=list(value['rows']))
            if isinstance(value,dict) and is_record_rows(value.get('rows')) else value)
    shipment=materialize(day['shipment_input'])
    directory=materialize(day['transporter_input'])
    production_source_inputs.validate(dict(schema=day.get('production_report_schema',production_source_inputs.SCHEMA),
        shipments=shipment,transporters=directory,report_policy=day['production_report_policy'],
        report_opening=day['production_report_opening']),run.business_date.isoformat())
    from mta.runtime.models import RunPhaseAcceptance
    phase=RunPhaseAcceptance.objects.select_related('snapshot').get(pk=sources.acceptance_id)
    if digest(raw.get('profile'))!=phase.snapshot.manifest['references']['profile']:
        raise PublicationUnavailable('bpr_transit_captured_profile_differs')
    delivery=raw['profile'].get('delivery',{})
    settings=delivery.get('btr_history',{}).get('importer_vf_settings')
    settings_owner=None
    if settings is None:settings,settings_owner=_opening_settings(phase)
    settings=list(settings);validate_settings_rows(settings)
    factor_rows=[row for row in settings if ascii_equal(row['Parameter'],'SuperDelayFactor')]
    factors=[row['Value'] for row in factor_rows]
    if len(factors)!=1:raise ValueError('Exactly one accepted SuperDelayFactor required')
    # These are separately captured projections of the same canonical table.
    # Do not merge bags or choose a preferred value when both declare a factor.
    other=delivery.get('conditional_dbm',{}).get('importer_vf_settings',[])
    conflicts=[row for row in other if ascii_equal(row['Parameter'],'SuperDelayFactor')]
    if conflicts and conflicts!=factor_rows:
        raise ValueError('Captured Importer VFSettings factor declarations differ')
    if settings_owner is None:settings_owner=_settings_owner(run,settings)
    standards=sources.rows('closing/dbm/SKULocStandardAttributes')
    report=sources.rows('reports/bpr/vf_RationedReqReport')
    raw_rows=[{key:(date.fromisoformat(value) if key in
        ('CreationDate','GateOutDate','ReportDate') and value is not None else value)
        for key,value in row.items()} for row in shipment['rows']]
    stamp=datetime.combine(run.business_date,datetime.min.time())
    validated=processor.validate_goods_in_transit(raw_rows,standards,run.business_date,stamp)
    rows=dict(InTransitDataRaw=raw_rows,InTransitData=validated['rows'],
        TransitRejectedMaster=validated['diagnostics'],
        GoodsInTransitTransporterMaster=processor.transporter_master(validated['rows'],directory['rows'],
            report,standards,factors[0]))
    metadata=dict(schema=SCHEMA,run_id=str(run.pk),input_digest=run.input_digest,
        input_manifest_digest=run.input_manifest_digest,source_digest=sources.source_digest,
        phase_id=str(sources.acceptance_id),phase_digest=sources.acceptance_digest,
        snapshot_digest=sources.snapshot_digest,action_revision=action_revision,
        display_date=sources.display_date.isoformat(),recipe_digest=recipe_digest(),
        producers=dict(validate=processor.VALIDATE_SOURCE_SHA256,transporter=processor.TRANSPORTER_SOURCE_SHA256),
        captured_sources=dict(shipments=dict(digest=digest(shipment),provenance=shipment['provenance']),
            transporters=dict(digest=digest(directory),provenance=directory['provenance'])),
        settings_owner=settings_owner,super_delay_factor=storage(factors[0]),run_timestamp=storage(stamp),
        images={name:dict(count=len(bag),digest=digest(bag)) for name,bag in rows.items()})
    return metadata,rows
