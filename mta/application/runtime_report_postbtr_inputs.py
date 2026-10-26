"""Pure consumed-field bridge for the six retained PostBTR queries.

These are source bags, not authenticated images or publication receipts. The
caller owns phase/action/copy/hook and frozen-remark-cut authentication, and any
new typed custody. Physical paths below describe lineage, not existing storage.
No terminal output, live master, live remark or partial BOR fallback is read.
"""
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from mta.application import complete_daily_inputs, runtime_bor_report as bor
from mta.application.runtime_report_btr_stage import BtrBoundary
from mta.application.runtime_report_projection import describe
from mta.application.stage_calculation_sources import CalculationSources
from mta.presentation.boroa_contract import SOURCE_FIELDS
from mta.row_sequences import RecordRows, is_record_rows
from mta.runtime.relational_state import STORAGE_TABLES
from mta.runtime.runtime_report_sources import scalar

SCHEMA = 'fresh-runtime-report-postbtr-inputs-v1'
IDS = (2, 3, 4, 5, 6, 8)
IMPORT_SQL_SHA256 = 'c248baeedda13d74a71a499c8b59b7ec46f05f11db00938de59a746bce94ce93'


def native_colours():
    """Read the existing pinned reference without importing Django UI owners."""
    root = Path(__file__).resolve().parents[2]
    value = json.loads((root/'mta/config/native_report_colours_v1.json').read_bytes())
    if (value.get('schema') != 'native-report-colours-v1'
            or value.get('source') != 'mta/application/r1_rationed_report.py'
            or hashlib.sha256((root/value['source']).read_bytes()).hexdigest()
               != value.get('source_sha256')):
        raise ValueError('Pinned native ColorSequence reference changed')
    if value.get('rows') != [dict(Color=colour,SequenceNo=ordinal) for ordinal,colour in
            enumerate(('Black','Red','Yellow','Green','Blue','White','Grey'),1)]:
        raise ValueError('Pinned native ColorSequence reference rows changed')
    return value['rows']


def _population(owner, name):
    if not isinstance(owner, Mapping) or name not in owner or not is_record_rows(owner[name]):
        raise ValueError('Required PostBTR source population missing: '+name)
    return owner[name]


def _typed(rows, columns, label):
    """Decode exact declared cells; preserve NULLs and every supplied ordinal."""
    if not is_record_rows(rows):
        raise ValueError('Explicit PostBTR source population required: '+label)
    def records():
        for row in rows:
            if not isinstance(row, Mapping) or not set(columns) <= row.keys():
                raise ValueError('Required PostBTR source fields missing: '+label)
            yield {name: scalar(row[name], kind) for name, kind in columns.items()}
    # Fail before returning a usable bundle even for a missing late row field.
    for _row in records():
        pass
    return RecordRows(len(rows), records)


def _native_remarks(rows):
    """Undo the existing ancillary model's native-naive -> UTC adaptation.

    daily_bor_prepared._to_model_values attaches UTC to native OA timestamps;
    ancillary_live emits those instants with offsets. Native query ROW_NUMBER
    consumes the corresponding UTC-naive SQL datetime, never local host time.
    """
    if not is_record_rows(rows):
        raise ValueError('Explicit PostBTR source population required: frozen remarks')
    def records():
        for row in rows:
            if not isinstance(row, Mapping) or 'RemarkDate' not in row:
                raise ValueError('Required PostBTR source fields missing: frozen remarks')
            stamp=row['RemarkDate']
            if type(stamp) is str:
                stamp=datetime.fromisoformat(stamp)
            if type(stamp) is not datetime:
                raise ValueError('Required native frozen remark datetime')
            if stamp.tzinfo is not None:
                stamp=stamp.astimezone(timezone.utc).replace(tzinfo=None)
            yield dict(row,RemarkDate=stamp)
    return RecordRows(len(rows),records)


def build(boundary, *, sources, frozen_remarks, color_sequence):
    """Build once over a real completed BTR boundary; select per query below.

    Full supplies capture_bpr's sources with histories completed once by their
    existing owner. Scoped supplies the exact accepted finite sources carried by
    the boundary. Missing history/capture is unavailable, never an empty bag.
    """
    if type(boundary) is not BtrBoundary or type(sources) is not CalculationSources:
        raise ValueError('Explicit native BTR boundary and calculation sources required')
    if boundary.sources is not None and boundary.sources is not sources:
        raise ValueError('Scoped PostBTR calculation source owner differs')
    phase = boundary.phase
    if (not phase.context.native_daily or not phase.completed_boundaries
            or phase.completed_boundaries[-1] != 'btr-insights'):
        raise ValueError('Completed native BTR boundary required')
    values, descriptors = {}, {}

    def add(logical, rows, table, fields, path, kind, *, columns=None, **extra):
        schema = dict(STORAGE_TABLES[table]) if columns is None else columns
        if not set(fields) <= schema.keys():
            raise ValueError('PostBTR fields absent from declared physical schema: '+table)
        selected = {name: schema[name] for name in fields}
        values[logical] = _typed(rows, selected, logical)
        descriptors[logical] = dict(physical_table=table, physical_path=path,
            kind=kind, fields=list(fields), types=list(selected.values()),
            rows=len(rows), **extra)

    history_fields = ('ParentWhCode','ParentWhName','SKUCode','SKUName','WhCode','WhName',
        'IsNormed','Req','ParentNorm','RationedReq','SupplierDispatchReq','DispatchPen',
        'DispatchColor','Dispatch','ReportDate','Stock','GIT')
    for name, fields in (('RationingHistory', history_fields),
            ('LastBatchRunTbl', ('LastRunDate',)),
            ('SkuLocAttributeData', ('SKUCode','LocCode','c9','c10','c12','c13'))):
        add('BTR/'+name, _population(boundary.trend_state,name), 'BTR/'+name, fields,
            'postbtr/btr/'+name, 'completed-btr-stage')

    rationed_table = 'BPR/vf_RationedReqReport'
    rationed = _typed(_population(phase.late,'vf_RationedReqReport'),
                     dict(STORAGE_TABLES[rationed_table]), rationed_table)
    picks = complete_daily_inputs.pick_report(rationed=rationed, bands=sources.pick_bands)
    pick_fields = ('SKUCode','WhCode','ParentWhCode','TOR_B','TOR_R','TOY','TOG')
    # Pick is a native view, not a registered storage table. Its key columns
    # inherit the rationed schema; bands are declared int INSERT expressions.
    pick_types = {name: dict(STORAGE_TABLES[rationed_table])[name] for name in pick_fields[:3]}
    pick_types.update({name:'int' for name in pick_fields[3:]})
    add('BPR/vf_PickListReport', picks, 'BPR/vf_PickListReport', pick_fields,
        'derived/bpr/vf_PickListReport', 'canonical-pick-insert-projection',
        columns=pick_types, parents=['late/vf_RationedReqReport','sources/pick'])

    reports = sources.production_reports
    add('BPR/BORWithOrderAllocation', _population(reports,'BORWithOrderAllocation'),
        'production/BORWithOrderAllocation',
        ('SKUCode','WhCode','SupplierCode','DispatchColor',*bor.QUANTITIES,*bor.DESCENDING),
        'sources/production/BORWithOrderAllocation', 'calculation-production-source')
    add('BPR/BOR_OrderAllocationHistory', _population(reports,'BOR_OrderAllocationHistory'),
        'production/BOR_OrderAllocationHistory',
        ('SKUCode','WhCode','SupplierCode','DispatchColor',*bor.QUANTITIES,'ReportDate'),
        'sources/production/BOR_OrderAllocationHistory', 'once-produced-bpr-history')
    add('BPR/vf_ReqCalculation', _population(reports,'BOROARequirement'),
        'production/BOROARequirement', ('SKUCode','WhCode','AdvAllocDone'),
        'sources/production/BOROARequirement', 'calculation-requirement-projection')

    for name, fields in (
            ('SKUDescriptionTbl', ('SKUCode','SKUDescription')),
            ('SiteDescriptionTbl', ('WHCode','WHDescription')),
            ('SkuAttributeData', ('SKUCode','c3')),
            ('SkuLocAttributeData', ('SKUCode','LocCode','c9','c10','c12','c13','c11','c7'))):
        add('BPR/'+name, _population(phase.importer,name), 'Importer/'+name, fields,
            'importer/'+name, 'canonical-bpr-copy-projection',
            import_sql_sha256=IMPORT_SQL_SHA256,
            persisted_bpr_partition=name!='SkuLocAttributeData')
    add('BPR/LastBatchRunTbl', _population(phase.late,'BPRLastBatchRunTbl'),
        'DBM/LastBatchRunTbl', ('LastRunDate',), 'late/BPRLastBatchRunTbl',
        'accepted-bpr-date-producer')

    expected_colours = native_colours()
    if (not is_record_rows(color_sequence) or list(color_sequence) != expected_colours
            or any(type(row.get('SequenceNo')) is not int for row in color_sequence)):
        raise ValueError('Pinned native ColorSequence rows differ')
    add('BPR/ColorSequence', color_sequence, 'reference/ColorSequence',
        ('Color','SequenceNo'), 'metadata/bpr/ColorSequence', 'pinned-native-reference',
        columns=dict(Color='nvarchar',SequenceNo='int'))
    remark_schema = SOURCE_FIELDS['BORReport_OARemarkDetails']
    remark_fields = ('SKUCode','WhCode','SupplierCode','Remark','RemarkDate')
    remark_types = {name: ('nvarchar' if remark_schema[name]['kind']=='text'
                          else remark_schema[name]['kind']) for name in remark_fields}
    add('BPR/BORReport_OARemarkDetails', _native_remarks(frozen_remarks),
        'ancillary/BORReport_OARemarkDetails', remark_fields,
        'sources/boroa/BORReport_OARemarkDetails', 'caller-authenticated-frozen-capture',
        columns=remark_types)
    return dict(schema=SCHEMA, sources=values, descriptors=descriptors)


def select(bundle, definition):
    """Return the exact logical roster consumed by one retained query."""
    spec = describe(definition)
    if (not isinstance(bundle, dict) or bundle.get('schema') != SCHEMA
            or spec['captured_source_id'] not in IDS):
        raise ValueError('Qualified PostBTR input bundle/query required')
    names = tuple(spec['sources'].values())
    if any(name not in bundle.get('sources',{}) or name not in bundle.get('descriptors',{})
           for name in names):
        raise ValueError('Required PostBTR logical source missing')
    return ({name:bundle['sources'][name] for name in names},
            {name:deepcopy(bundle['descriptors'][name]) for name in names})
