"""Finite typed report-stage images, separate from the accepted phase codec.

The registrar owns the transaction, run/worker and source cut. This module owns
only physical shape, exact cell transport and ordinal/checksum readback. Image
metadata contains no business values. The shared phase registry stays unchanged.
"""
from collections.abc import Mapping
from copy import deepcopy
from uuid import UUID

from django.db import transaction
from mta.serialization import digest, storage
from mta.row_sequences import RecordRows, is_record_rows
from mta.runtime import relational_state as typed
from mta.runtime.runtime_report_sources import image_rows

SCHEMA = 'fresh-runtime-report-stage-images-v1'
PLACEMENTS = ('PostImporter','PostBPR','PostDBM','PostBTR','Final')
# Explicit physical lineage. New tables keep old phase recipes and row guards
# intact; each image stores just its consumed columns, not a second day state.
PHYSICAL = {
    'BTR/RationingHistory':'BTR/RationingHistory',
    'BTR/LastBatchRunTbl':'BTR/LastBatchRunTbl',
    'BTR/SkuLocAttributeData':'BTR/SkuLocAttributeData',
    'BPR/BORWithOrderAllocation':'production/BORWithOrderAllocation',
    'BPR/BOR_OrderAllocationHistory':'production/BOR_OrderAllocationHistory',
    'BPR/vf_ReqCalculation':'production/BOROARequirement',
    'BPR/LastBatchRunTbl':'DBM/LastBatchRunTbl',
    'BPR/SpikeOrderData':'BPR/SpikeOrderData',
    'BPR/vf_RationedReqReport':'BPR/vf_RationedReqReport',
    'BPR/SupplierDispatchReq':'complete/BPR/SupplierDispatchReq',
    **{'BPR/'+name:'Importer/'+name for name in (
        'SKUDescriptionTbl','SiteDescriptionTbl','SkuAttributeData',
        'SkuLocAttributeData','LocationAttributeData')},
}
LOGICAL = {name:deepcopy(typed.STORAGE_TABLES[table]) for name,table in PHYSICAL.items()}
LOGICAL.update({
    'BPR/vf_PickListReport':[
        ['SKUCode','nvarchar'],['WhCode','nvarchar'],['ParentWhCode','nvarchar'],
        ['TOR_B','int'],['TOR_R','int'],['TOY','int'],['TOG','int']],
    'BPR/ColorSequence':[['Color','nvarchar'],['SequenceNo','int']],
    'BPR/BORReport_OARemarkDetails':[
        ['SKUCode','nvarchar'],['WhCode','nvarchar'],['SupplierCode','nvarchar'],
        ['Remark','nvarchar'],['RemarkDate','datetime']],
})
TABLES = {'placement/'+name:columns for name,columns in LOGICAL.items()}


def path(candidate_id, logical):
    if type(candidate_id) is not str or str(UUID(candidate_id)) != candidate_id:
        raise ValueError('Canonical report image owner UUID required')
    if logical not in LOGICAL:
        raise ValueError('Unqualified report image source')
    return 'runtime-report/'+candidate_id+'/'+logical


def describe(candidate_id, logical, rows):
    if not is_record_rows(rows):
        raise ValueError('Explicit report image rows required')
    image=path(candidate_id,logical)
    columns={name.casefold():(name,kind) for name,kind in LOGICAL[logical]}
    # Store exactly the existing scalar wire representation; decode by native
    # schema on read. This retains decimals, datetime fractions, NULL and order.
    values=RecordRows(len(rows),lambda:(storage(row) for row in rows))
    metadata,fields,native=typed.describe_rows(values,columns,image)
    metadata['table']='placement/'+logical
    if fields!=[name for name,_kind in native] or len(set(fields))!=len(fields):
        raise ValueError('Report stage image requires unique canonical column names')
    return metadata,values,fields,native


def write(run,candidate_id,logical,rows):
    """Called only inside the authenticated registrar's atomic owner."""
    if transaction.get_autocommit():
        raise ValueError('Report images require an atomic publication owner')
    metadata,values,fields,native=describe(candidate_id,logical,rows)
    if values:
        query=('INSERT INTO '+typed.table_sql(metadata['table'])+
            ' (vf_run_id,vf_image,vf_ordinal,'+
            ','.join(typed.quote(name) for name,_ in native)+') VALUES ('+
            ','.join(['%s']*(len(native)+3))+')')
        typed.bulk(query,((run.pk,metadata['image'],ordinal,*[
            typed.db_value(row[field],kind) for field,(_,kind) in zip(fields,native)])
            for ordinal,row in enumerate(values)))
    if digest(typed.load_image(run,metadata,table_registry=TABLES))!=digest(values):
        raise ValueError('Report stage typed readback differs')
    return metadata


def validate_images(value,*,candidate_id,placement):
    if (type(value) is not dict or set(value)!={'schema','candidate_id','placement','images','digest'}
            or value['schema']!=SCHEMA or value['candidate_id']!=candidate_id
            or value['placement']!=placement or placement not in PLACEMENTS
            or type(value['images']) is not dict
            or value['digest']!=digest({k:v for k,v in value.items() if k!='digest'})):
        raise ValueError('Exact report stage image manifest required')
    for logical,meta in value['images'].items():
        if (type(meta) is not dict or set(meta)!={'image','table','count','digest','fields'}
                or meta['image']!=path(candidate_id,logical)
                or meta['table']!='placement/'+logical
                or type(meta['count']) is not int or meta['count']<0
                or type(meta['digest']) is not str or len(meta['digest'])!=64
                or any(c not in '0123456789abcdef' for c in meta['digest'])
                or type(meta['fields']) is not list):
            raise ValueError('Report stage image identity differs')
        declared=dict(LOGICAL[logical]);seen=set()
        for field in meta['fields']:
            if (type(field) not in (tuple,list) or len(field)!=3
                    or field[0]!=field[1] or field[0] not in declared
                    or field[0] in seen or field[2] not in ('str','int','float','bool')):
                raise ValueError('Report stage image column contract differs')
            seen.add(field[0])
        if meta['count'] and not seen:
            raise ValueError('Nonempty report stage image has no columns')
    return value


def capture(run,*,candidate_id,placement,sources,row_writer=None):
    if placement not in PLACEMENTS or not isinstance(sources,Mapping):
        raise ValueError('Explicit placement source bags required')
    # Validate all shapes before the first write, even if the caller supplies
    # an injectable transport for a pure contract test.
    for logical,rows in sources.items():describe(candidate_id,logical,rows)
    writer=row_writer or (lambda logical,rows:write(run,candidate_id,logical,rows))
    result=dict(schema=SCHEMA,candidate_id=candidate_id,placement=placement,
        images={logical:writer(logical,rows) for logical,rows in sources.items()})
    result['digest']=digest(result)
    return validate_images(result,candidate_id=candidate_id,placement=placement)


def read(run,manifest,*,candidate_id,placement,fields):
    """No run selection or readiness implied; caller authenticates receipt."""
    validate_images(manifest,candidate_id=candidate_id,placement=placement)
    if not isinstance(fields,Mapping) or not set(fields)<=manifest['images'].keys():
        raise ValueError('Required report stage image absent')
    return {logical:image_rows(run,manifest['images'][logical],
        expected_table='placement/'+logical,fields=names,registry=TABLES)
        for logical,names in fields.items()}
