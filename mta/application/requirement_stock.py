"""Connect explicit raw requirement stock to the existing StockOpening primitive.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from decimal import Decimal
from mta.application.r1_importer_master import _sql_key
FIELDS={'SKUCode','WhCode','StockForReqCalc','ReportDate'}
def validate(records,business_date):
    if not isinstance(records,list):raise ValueError('Explicit requirement-stock population required')
    for row in records:
        if not isinstance(row,dict) or set(row)!=FIELDS:raise ValueError('Requirement-stock field roster differs')
        for field in ('SKUCode','WhCode'):
            value=row[field]
            if not isinstance(value,str) or not value.strip() or not value.isascii() or len(value)>50:raise ValueError('Requirement-stock identity differs')
        value=row['StockForReqCalc']
        if value is not None and (type(value) is not int or not -2**31<=value<2**31):raise ValueError('Requirement-stock must retain signed SQL int orNULL')
        if row['ReportDate']!=business_date:raise ValueError('Requirement-stock date differs')
    return records

def apply(source,records,business_date):
    validate(records,business_date)
    targets={}
    for row in source['stock_openings']:
        key=(_sql_key(row['sku_code']),_sql_key(row['location_code']))
        if key in targets:raise ValueError('Duplicate calculation stock grain')
        targets[key]=row
    groups={}
    for row in records:groups.setdefault((_sql_key(row['SKUCode']),_sql_key(row['WhCode'])),[]).append(row)
    for key,rows in groups.items():
        if key not in targets:raise ValueError('Requirement-stock outside consuming master closure')
        target=targets[key]
        if target['stock'] is None:raise ValueError('Current physical stock remains unavailable; no invented zero')
        current=Decimal(str(target['stock']))
        candidates={current if row['StockForReqCalc'] is None else Decimal(row['StockForReqCalc']) for row in rows}
        if len(candidates)!=1:raise ValueError('Ambiguous requirement-stock UPDATE candidates')
        # SQL ISNULL(override,currentStock), already ported by StockOpening.
        target['stock_for_requirement_override']=rows[0]['StockForReqCalc']
    return source
