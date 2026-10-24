"""The exact opening owner of pre-BTR availability, without new BTR work.

Binding checks sealed owner metadata and captured profile equality. Explicit
row verification traverses this bag; SQL retains its physical owner and ordinals.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import date,timedelta
import inspect

from mta.presentation.context import PublicationUnavailable
from mta.runtime import input_storage,input_v3,relational_state as typed,opening_storage
from mta.serialization import digest

PATH='closing/btr/BufferTrendPhysicalInv'
INPUT='input/opening/state/btr/BufferTrendPhysicalInv'
TABLE='BTR/BufferTrendPhysicalInv'


def recipe_digest():
    return digest(inspect.getsource(inspect.getmodule(recipe_digest)))


def _fail():raise PublicationUnavailable('bpr_inherited_btr_owner_differs')


def _node(owner,path):
    """Resolve the existing finite one-hop input owner, never a newer opening."""
    manifest=owner.input_payload
    node=manifest['tree'];current='input'
    for part in path.split('/')[1:]:
        if 'owner_reference' in node:
            if manifest.get('schema')!=input_storage.V3 or node!={'owner_reference':current}:
                _fail()
            owner,manifest,_legacy=input_v3._owner_manifest(owner,current,
                manifest['owner_references'][current],input_v3._identity(owner,None,reading=True),None)
            input_storage.read_input(owner,components=(),image_reader=opening_storage.load_image)
            node=input_v3._node_at(manifest,current)
        if set(node)!={'object'}:_fail()
        matches=[child for name,child in node['object'] if name==part]
        if not matches:return None
        if len(matches)!=1:_fail()
        node=matches[0];current+='/'+part
    return owner,node


def _metadata(item,image):
    if (type(item) is not dict or item.get('image')!=image or item.get('table')!=TABLE
            or type(item.get('count')) is not int or item['count']<0
            or type(item.get('fields')) is not list or item['count'] and not item['fields']):_fail()
    from mta.runtime.ingestion_context import sha
    sha(item.get('digest'))
    seen=set();columns=dict(typed.STORAGE_TABLES[TABLE])
    for field in item['fields']:
        if (not isinstance(field,(list,tuple)) or len(field)!=3 or field[0]!=field[1]
                or field[0] not in columns or field[0] in seen
                or field[2] not in ('str','int','float','bool')):_fail()
        seen.add(field[0])
    if item['count'] and not {'SKUCode','WhCode','Availability_01_30',
            'Availability_31_60','Availability_61_90'}<=seen:_fail()
    return deepcopy(item)


@dataclass(frozen=True)
class InheritedBtr:
    owner: object
    locator: dict

    def metadata(self):return deepcopy(self.locator['image'])

    def provenance(self):return deepcopy(self.locator)

    def rows(self):
        if self.locator['representation']=='explicit_empty':return []
        reader=opening_storage.load_image if self.locator['owner_kind']=='INITIALIZATION' else typed.load_image
        try:return reader(self.owner,self.metadata())
        except ValueError as error:raise PublicationUnavailable('bpr_inherited_btr_rows_differ') from error

    def verify_rows(self):
        if self.locator['representation']=='explicit_empty':return
        reader=opening_storage.iter_image if self.locator['owner_kind']=='INITIALIZATION' else typed.iter_image
        try:
            for _ in reader(self.owner,self.metadata()):pass
        except ValueError as error:raise PublicationUnavailable('bpr_inherited_btr_rows_differ') from error

    def query(self):
        item=self.metadata()
        selected=','.join(typed.quote(column)+' AS '+typed.quote(name) for name,column,_ in item['fields'])
        if not selected:selected=','.join(typed.quote(name) for name,_ in typed.STORAGE_TABLES[TABLE])
        if self.locator['representation']=='explicit_empty':
            return ('SELECT vf_ordinal,'+selected+' FROM '+typed.table_sql(TABLE)+' WHERE false',[])
        initial=self.locator['owner_kind']=='INITIALIZATION'
        table=opening_storage.table_sql(TABLE) if initial else typed.table_sql(TABLE)
        column='vf_initialization_id' if initial else 'vf_run_id'
        return ('SELECT vf_ordinal,'+selected+' FROM '+table+' WHERE '+column+'=%s AND vf_image=%s',
            [self.owner.pk,item['image']])


def bind(phase):
    """Called only after the existing accepted BPR/input/action binding checks."""
    from django.core.exceptions import ObjectDoesNotExist
    from mta.runtime.captured_input import SCHEMAS,origin
    from mta.runtime.input_reader import read_input
    from mta.runtime.models import CalculationRun,RunCommand
    from mta.runtime.receipt_integrity import verify_root
    try:
        run=phase.run
        physical=origin(run) if run.input_payload.get('schema') in SCHEMAS else run
        input_storage.read_input(physical,components=())
        raw=read_input(run,components=('lineage','initialization_binding'))
        opening_date=date.fromisoformat(phase.snapshot.manifest['metadata']['opening_date'])
        if opening_date>=run.business_date:_fail()
        representation='physical';report_owner=None
        if run.predecessor_id is not None:
            parent=CalculationRun.objects.get(pk=run.predecessor_id)
            opening=_node(physical,'input/opening')
            if opening is None or opening[1]!={'scalar':None}:_fail()
            if (parent.kind!='DAILY_CHAIN' or parent.production_manifest.get('version') not in (2,3)
                    or parent.business_date!=opening_date
                    or raw.get('lineage',{}).get('run_id')!=str(parent.pk)
                    or raw['lineage'].get('output_digest')!=parent.output_digest):_fail()
            verify_root(parent)
            previous=read_input(parent,components=('initialization_binding','profile'))
            if (previous.get('initialization_binding')!=raw.get('initialization_binding')
                    or digest(previous['profile'])!=phase.snapshot.manifest['references']['profile']):_fail()
            if raw.get('initialization_binding') is not None:
                if (parent.mdm_input_capture.source_id!=phase.source_id
                        or parent.mdm_input_capture.status!='CONSUMED'
                        or parent.business_date+timedelta(days=1)!=run.business_date):_fail()
            commands=[]
            for event in RunCommand.objects.filter(run=parent,phase_acceptance__isnull=True).order_by('id'):
                if digest(event.payload)!=event.digest:_fail()
                commands.append(dict(id=event.pk,digest=event.digest,before=event.before_digest,after=event.after_digest))
            if raw['lineage'].get('commands')!=commands:_fail()
            owner=parent;kind='PREDECESSOR';item=parent.production_manifest['images'].get(PATH)
            if item is None:
                # Native v3 persists operational BTR first. Analytics belong to
                # its separate immutable report generation; never rebuild here.
                from mta.runtime.models import DailyReportGeneration
                from mta.presentation import operational_reports
                if not DailyReportGeneration.objects.filter(run=parent,status='READY').exists():return None
                generation=operational_reports.generation(parent)
                item=generation.metadata['images'].get(PATH)
                if item is None:return None
                report_owner=dict(id=str(generation.pk),digest=generation.digest,
                    source_digest=generation.source_digest,recipe_digest=generation.recipe_digest)
            else:
                node=parent.production_manifest.get('closing',{}).get('btr',{}).get('tables',{}).get('BufferTrendPhysicalInv')
                if node!={'image':PATH}:_fail()
            item=_metadata(item,PATH)
            owner_digest=parent.output_digest
        else:
            found=_node(physical,INPUT)
            if found is None:return None
            owner,node=found
            dated=_node(physical,'input/opening/opening_date')
            if dated is None or dated[0].pk!=owner.pk or dated[1]!={'scalar':opening_date.isoformat()}:_fail()
            kind='INITIALIZATION' if owner._meta.model_name=='productioninitialization' else 'CAPTURED_INPUT'
            if kind=='INITIALIZATION' and (owner.source_id!=phase.source_id
                    or owner.opening_date!=opening_date or opening_date+timedelta(days=1)!=run.business_date):_fail()
            if kind=='INITIALIZATION' and raw.get('initialization_binding')!=dict(id=str(owner.pk),
                    source_digest=owner.source.digest,input_sha256=owner.input_sha256,
                    content_digest=owner.input_digest,configuration_digest=owner.configuration_digest):_fail()
            if node=={'empty':True}:
                representation='explicit_empty'
                item=dict(image=INPUT+'/values',table=TABLE,count=0,digest=digest([]),fields=[])
            else:
                if node.get('children')!=[] or node.get('records')!=INPUT+'/values':_fail()
                item=_metadata(owner.input_payload['images'].get(node['records']),node['records'])
                if not item['count'] and item['digest']!=digest([]):_fail()
            owner_digest=owner.input_manifest_digest
        locator=dict(schema='fresh-inherited-btr-source-v1',owner_kind=kind,owner_id=str(owner.pk),
            owner_digest=owner_digest,run_id=str(run.pk),input_digest=run.input_digest,
            input_manifest_digest=run.input_manifest_digest,physical_input_owner=str(physical.pk),
            phase_id=str(phase.pk),phase_digest=phase.digest,producer_date=opening_date.isoformat(),
            accepted_business_date=run.business_date.isoformat(),representation=representation,image=item,
            report_generation=report_owner)
        return InheritedBtr(owner,locator)
    except (ValueError,KeyError,TypeError,ObjectDoesNotExist) as error:
        raise PublicationUnavailable('bpr_inherited_btr_owner_differs') from error
