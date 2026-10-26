"""Pure PostBPR source bags for retained Spike and Total Requirement queries.

This is neither phase admission nor copy/hook authentication. Physical paths
describe actual producer lineage; the runtime owner authenticates the phase,
four BPR copy partitions, canonical pair copy and applicable PostBPR hook before
giving these bags typed custody or publishing files. No terminal output is read.
"""
from collections.abc import Mapping
from copy import deepcopy

from mta.application import runtime_demand_reports as demand
from mta.application.runtime_report_projection import describe
from mta.row_sequences import RecordRows, is_record_rows
from mta.runtime.relational_state import STORAGE_TABLES
from mta.runtime.runtime_report_sources import scalar
from mta.temporal.day_phases import BprDay

SCHEMA = 'fresh-runtime-report-bpr-inputs-v1'
IMPORT_SQL_SHA256 = 'c248baeedda13d74a71a499c8b59b7ec46f05f11db00938de59a746bce94ce93'


def _population(owner, name):
    if not isinstance(owner, Mapping) or name not in owner or not is_record_rows(owner[name]):
        raise ValueError('Required PostBPR source population missing: '+name)
    return owner[name]


def _typed(rows, columns, label):
    def records():
        for row in rows:
            if not isinstance(row, Mapping) or not set(columns) <= row.keys():
                raise ValueError('Required PostBPR source fields missing: '+label)
            yield {field:scalar(row[field], kind) for field,kind in columns.items()}
    # Validate all requested cells before returning any usable bundle. Retain
    # reiterable views rather than a second full population in memory.
    for _row in records():
        pass
    return RecordRows(len(rows),records)


def build(phase):
    """Decode the actual BprDay live-out using existing physical schemas.

    Restored BPR snapshots produce the same values. Source lists may be empty;
    a missing population or a missing requested field is never an empty bag.
    """
    if type(phase) is not BprDay or not phase.context.native_daily:
        raise ValueError('Actual native BPR phase required')
    values,descriptors,copy_descriptors={},{},{}

    def add(logical, rows, table, fields, path, kind, **extra):
        schema=dict(STORAGE_TABLES[table])
        if not set(fields) <= schema.keys():
            raise ValueError('PostBPR fields absent from physical schema: '+table)
        columns={field:schema[field] for field in fields}
        values[logical]=_typed(rows,columns,logical)
        descriptors[logical]=dict(physical_table=table,physical_path=path,kind=kind,
            fields=list(fields),types=list(columns.values()),rows=len(rows),**extra)

    add('BPR/SpikeOrderData',_population(phase.order_state,'SpikeOrderData'),
        'BPR/SpikeOrderData',demand.SPIKE_FIELDS,'orders/SpikeOrderData','bpr-order-state')
    add('BPR/vf_RationedReqReport',_population(phase.late,'vf_RationedReqReport'),
        'BPR/vf_RationedReqReport',demand.RATIONED_FIELDS,
        'late/vf_RationedReqReport','late-bpr-report')
    add('BPR/SupplierDispatchReq',_population(phase.complete,'SupplierDispatchReq'),
        'complete/BPR/SupplierDispatchReq',
        ('SKUCode','WHCode','SupplierCode','OriginalReq','DispatchReq',*demand.SUPPLIER_BANDS),
        'complete/SupplierDispatchReq','complete-bpr-supplier-dispatch')
    # These entire Importer field rosters match the four native BPR MDM copy
    # partitions. SKUDescriptionTbl is a copy-validation dependency even though
    # TotalReq's SELECT uses only SiteDescriptionTbl for its parent description.
    for name in ('SkuAttributeData','SKUDescriptionTbl','LocationAttributeData','SiteDescriptionTbl'):
        table='Importer/'+name
        rows=_population(phase.importer,name)
        fields=tuple(field for field,_kind in STORAGE_TABLES[table])
        add('BPR/'+name,rows,table,fields,'importer/'+name,'canonical-bpr-copy-projection',
            import_sql_sha256=IMPORT_SQL_SHA256,persisted_bpr_partition=True)
        copy_descriptors['BPR/'+name]=deepcopy(descriptors['BPR/'+name])
    # Match bind_post_bpr: validate all four copies, expose only query sources.
    del values['BPR/SKUDescriptionTbl'],descriptors['BPR/SKUDescriptionTbl']
    name='SkuLocAttributeData';table='Importer/'+name
    add('BPR/'+name,_population(phase.importer,name),table,
        tuple(field for field,_kind in STORAGE_TABLES[table]),'importer/'+name,
        'reconstructed-canonical-copy',import_sql_sha256=IMPORT_SQL_SHA256,
        persisted_bpr_partition=False)
    return dict(schema=SCHEMA,sources=values,descriptors=descriptors,
                copy_descriptors=copy_descriptors)


def select(bundle,definition):
    """Choose the exact retained query roster without conferring authority."""
    spec=describe(definition)
    if (not isinstance(bundle,dict) or bundle.get('schema')!=SCHEMA
            or spec['captured_source_id'] not in (7,10)):
        raise ValueError('Qualified PostBPR input bundle/query required')
    names=tuple(spec['sources'].values())
    if any(name not in bundle.get('sources',{}) or name not in bundle.get('descriptors',{})
           for name in names):
        raise ValueError('Required PostBPR logical source missing')
    return ({name:bundle['sources'][name] for name in names},
            {name:deepcopy(bundle['descriptors'][name]) for name in names})
