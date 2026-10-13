"""Explicit external shipment and transporter inputs for native daily producers.

These are facts, never an aggregate-GIT reconstruction or a calculated report.
The existing transit processor owns joins, diagnostics, dates and multiplicity.
"""
from datetime import date, datetime
import json

from mta.application import daily_transit

SCHEMA = 'fresh-production-source-inputs-v1'
from mta.application.production_output_policy import SOURCE_SCHEMA as OUTPUT_SCHEMA
DIRECTORY_FIELDS = ('TransporterCode', 'TransporterName', 'TransporterContact')
RAW_TABLE = 'input/production_shipment'
DIRECTORY_TABLE = 'input/production_transporter'
TABLES = {
    RAW_TABLE: [(field, 'date' if field in ('CreationDate', 'GateOutDate', 'ReportDate')
                 else 'int' if field == 'InTransitQty' else 'nvarchar')
                for field in daily_transit.RAW_FIELDS],
    DIRECTORY_TABLE: [(field, 'nvarchar') for field in DIRECTORY_FIELDS],
}

REQUEST_TABLE='input/production_request'
TABLES[REQUEST_TABLE]=[(name,'datetime' if name in ('RequestDate','ActionDate','ETA') else 'nvarchar')
    for name in ('SKUCode','WhCode','ParentWhCode','Request','RequestDate','Action','ActionDate','UserId','ETA')]
CONSUMER_PATHS={'input/request_inputs/rows/values':REQUEST_TABLE}
for _family,_supplier in (('BPRReport_RemarkDetails',False),('BORReport_RemarkDetails',True),('BORReport_OARemarkDetails',True)):
    _table='input/production_remark_'+('bpr' if not _supplier else 'boroa' if _family=='BORReport_OARemarkDetails' else 'bor')
    TABLES[_table]=[('source_ordinal','bigint'),('SKUCode','nvarchar'),('WhCode','nvarchar'),
        *([('SupplierCode','nvarchar')] if _supplier else []),('Remark','nvarchar'),('Username','nvarchar'),('RemarkDate','datetimetz')]
    CONSUMER_PATHS['input/remark_inputs/'+_family+'/rows/values']=_table


def validate(value, business_date):
    if (not isinstance(value, dict) or set(value) != {'schema', 'shipments', 'transporters', 'report_policy', 'report_opening'}
            or value['schema'] not in (SCHEMA, OUTPUT_SCHEMA)):
        raise ValueError('Explicit production shipment/transporter source roster required')
    policy = value['report_policy']
    policy_fields = {'bor_history_horizon', 'rrr_history_horizon'}
    if value['schema'] == OUTPUT_SCHEMA:
        from mta.application.production_output_policy import require
        policy_fields.add('output_contract')
        require(policy.get('output_contract') if isinstance(policy, dict) else None)
    if (not isinstance(policy, dict) or set(policy) != policy_fields
            or any(type(item) is not int or item < 0 for key,item in policy.items() if key != 'output_contract')):
        raise ValueError('Explicit native report history horizons required')
    opening = value['report_opening']
    if opening is not None and opening != {'BOR_OrderAllocationHistory': [], 'RRR_OrderAllocationHistory': []}:
        raise ValueError('Fresh native report opening requires explicit empty histories; calculated seeds forbidden')
    for name, fields in (('shipments', daily_transit.RAW_FIELDS),
                         ('transporters', DIRECTORY_FIELDS)):
        source = value[name]
        if (not isinstance(source, dict)
                or set(source) != {'schema', 'business_date', 'provenance', 'rows'}
                or source['schema'] != ('daily-transit-raw-v1' if name == 'shipments'
                                        else 'daily-transporter-raw-v1')
                or source['business_date'] != business_date
                or not isinstance(source['provenance'], dict) or not source['provenance']
                or len(json.dumps(source['provenance'])) > 16384
                or not isinstance(source['rows'], list)):
            raise ValueError('Explicit dated production source required: ' + name)
        for row in source['rows']:
            if not isinstance(row, dict) or set(row) != set(fields):
                raise ValueError('Complete production source field roster required: ' + name)
            for field, scalar in row.items():
                if field in ('CreationDate', 'GateOutDate', 'ReportDate'):
                    if scalar is not None and (not isinstance(scalar, str)
                            or date.fromisoformat(scalar).isoformat() != scalar):
                        raise ValueError('ISO source date required: ' + field)
                elif field == 'InTransitQty':
                    daily_transit._integer(scalar, field)
                else:
                    limit = (125 if field == 'TransporterName' else
                             20 if field == 'TransporterContact' else
                             None if field == 'Remark' else 50)
                    daily_transit._text(scalar, field, limit)
    return value


def validate_initial_remarks(remarks, business_date):
    """Initial external remarks retain their supplied user, timestamp and order."""
    if not isinstance(remarks, dict) or set(remarks) != {'bpr', 'bor', 'boroa'}:
        raise ValueError('Explicit initial remark family roster required')
    for family, rows in remarks.items():
        fields = {'SKUCode', 'WhCode', 'Remark', 'Username', 'RemarkDate'}
        if family != 'bpr':
            fields.add('SupplierCode')
        if not isinstance(rows, list):
            raise ValueError('Explicit initial remark population required: ' + family)
        for row in rows:
            if not isinstance(row, dict) or set(row) != fields:
                raise ValueError('Complete initial remark fields required: ' + family)
            for field, value in row.items():
                if field == 'RemarkDate':
                    if not isinstance(value, str):
                        raise ValueError('Explicit initial remark timestamp required')
                    timestamp = datetime.fromisoformat(value)
                    if timestamp.tzinfo is None or timestamp.date() >= date.fromisoformat(business_date):
                        raise ValueError('Initial remark must be dated before its first business day with timezone')
                else:
                    limit = (None if field == 'Remark' else
                             100 if field == 'Username' and family != 'boroa' else 50)
                    daily_transit._text(value, field, limit)
                    if value is None and field not in ('Remark', 'Username'):
                        raise ValueError('Initial remark identity cannot be NULL: ' + field)
    return remarks
