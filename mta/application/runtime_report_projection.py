"""Finite retained-query dispatch over explicit logical database source bags.

This is not a SQL interpreter, runtime owner or file publisher. The caller must
authenticate and decode each required source at its accepted placement. Database
qualifiers are deliberately retained: BTR attributes cannot become BPR/Importer
attributes merely because their column names match.
"""
from collections.abc import Mapping
from datetime import date, datetime
import hashlib

from mta.application import runtime_bor_report as bor
from mta.application import runtime_demand_reports as demand
from mta.application import runtime_history_reports as history
from mta.row_sequences import is_record_rows


def describe(definition):
    if not isinstance(definition, Mapping) or type(definition.get('Query')) is not str:
        raise ValueError('Explicit RuntimeReports definition required')
    checksum = hashlib.sha256(definition['Query'].encode('utf-8')).hexdigest()
    base = '%BPRDatabase%'
    if checksum in bor.QUERY_PINS:
        source_id = bor.QUERY_PINS[checksum][0]
        columns = bor.COLUMNS
        sources = dict(bor_with_order_allocation='BPR/BORWithOrderAllocation',
            color_sequence='BPR/ColorSequence', sku_descriptions='BPR/SKUDescriptionTbl',
            site_descriptions='BPR/SiteDescriptionTbl', sku_loc_attributes='BPR/SkuLocAttributeData',
            sku_attributes='BPR/SkuAttributeData')
    elif checksum in history.QUERY_PINS:
        source_id = history.QUERY_PINS[checksum]
        if source_id in (2, 3):
            base = '%BufferTrendDatabase%'
            columns = history.EFFICIENCY_COLUMNS
            sources = dict(today='BTR/LastBatchRunTbl', rationing_history='BTR/RationingHistory',
                sku_loc_attributes='BTR/SkuLocAttributeData', pick_report='BPR/vf_PickListReport')
        else:
            columns = history.ALLOCATION_COLUMNS
            sources = dict(today='BPR/LastBatchRunTbl', bor_history='BPR/BOR_OrderAllocationHistory',
                color_sequence='BPR/ColorSequence', sku_descriptions='BPR/SKUDescriptionTbl',
                site_descriptions='BPR/SiteDescriptionTbl', requirements='BPR/vf_ReqCalculation',
                sku_loc_attributes='BPR/SkuLocAttributeData', sku_attributes='BPR/SkuAttributeData',
                remarks='BPR/BORReport_OARemarkDetails')
    elif checksum == demand.SPIKE_QUERY:
        source_id, columns = 7, demand.SPIKE_FIELDS
        sources = dict(spike_order_data='BPR/SpikeOrderData')
    elif checksum == demand.TOTAL_QUERY:
        source_id, columns = 10, demand.TOTAL_COLUMNS
        sources = dict(rationed_report='BPR/vf_RationedReqReport',
            supplier_dispatch='BPR/SupplierDispatchReq', site_descriptions='BPR/SiteDescriptionTbl',
            sku_loc_attributes='BPR/SkuLocAttributeData', sku_attributes='BPR/SkuAttributeData',
            location_attributes='BPR/LocationAttributeData')
    else:
        raise ValueError('RuntimeReports query has no implemented projection')
    if definition.get('BaseDB') != base:
        raise ValueError('RuntimeReports query BaseDB contract differs')
    return dict(query_sha256=checksum, captured_source_id=source_id, base_db=base,
                columns=tuple(columns), sources=sources)


def _today(rows):
    """Native scalar subquery then assignment to date; no business-date fallback."""
    if not is_record_rows(rows) or len(rows) > 1:
        raise ValueError('Native report LastBatchRunTbl scalar population differs')
    if not rows:
        return None
    row = rows[0]
    if not isinstance(row, Mapping) or 'LastRunDate' not in row:
        raise ValueError('Native report LastRunDate column missing')
    value = row['LastRunDate']
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value) if len(value) > 10 else date.fromisoformat(value)
    if type(value) is datetime and value.tzinfo is None:
        return value.date()
    if type(value) is date:
        return value
    raise ValueError('Native report LastRunDate must be a naive date/timestamp')


def project(definition, sources):
    """Return column-expression labels and cells; no header/encoding/READY claim."""
    spec = describe(definition)
    if not isinstance(sources, Mapping) or set(sources) != set(spec['sources'].values()):
        raise ValueError('Exact logical RuntimeReports source roster required')
    values = {argument: sources[name] for argument, name in spec['sources'].items()}
    if 'today' in values:
        values['today'] = _today(values['today'])
    source_id = spec['captured_source_id']
    function = (bor.project if source_id in (4, 5, 6) else
                history.efficiency if source_id in (2, 3) else
                history.allocation_history if source_id == 8 else
                demand.spike_orders if source_id == 7 else demand.total_requirements)
    return dict(columns=spec['columns'], rows=function(definition, **values))
