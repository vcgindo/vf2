"""Producer-owned rationing history and adjacent-date inferred dispatch."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from mta.domain.complete_daily_scalars import ascii_equal

raw = (Path(__file__).resolve().parents[1]/'config/btr_rationing_history_v1.json').read_bytes()
if hashlib.sha256(raw).hexdigest() != '6a8878abacc19604e2abc7cc5adf85e55bdd449e73b01fb235c6002a1be40764':
    raise ValueError('BTR rationing history schema identity differs')
COLUMNS = json.loads(raw)['columns']
FIELDS = tuple(c['name'] for c in COLUMNS)
INSERT_LITERALS = {'Receipts':0, 'Consumption':0, 'SupplierDispatchReq':0}
OMITTED = ('WhType', 'ParentWhType', 'Dispatch')
SOURCE_FIELDS = tuple(n for n in FIELDS if n not in (*INSERT_LITERALS, *OMITTED, 'ReportDate'))
POPULATION = 'RationingHistory'
STAGE = 'CollectRationingHistory.sql'


def integer(value, label):
    if type(value) is not int or not -(2**31) <= value < 2**31:
        raise ValueError('BTR history signed32 integer required: '+label)
    return value


def configuration(settings, importer_vf_settings=None):
    flag = settings.get('CaptureDispatchExecutionEfficiency')
    if type(flag) not in (int,str) or flag not in (0,1,'0','1'):
        raise ValueError('Explicit BTR history capture flag0/1 required')
    enabled = str(flag) == '1'
    if importer_vf_settings is not None or enabled:
        from mta.domain.dbm_conditional import validate_settings_rows
        validate_settings_rows(importer_vf_settings)
        observed = sum(ascii_equal(r['Parameter'],'CaptureDispatchExecutionEfficiency')
                       and ascii_equal(r['Value'],'1') for r in importer_vf_settings) == 1
        if observed != enabled:
            raise ValueError('BTR capture flag differs from owned Importer VFSettings COUNT=1')
    if enabled:
        integer(settings.get('RationingHistoryHorizonBTR'), 'RationingHistoryHorizonBTR')
    elif 'RationingHistoryHorizonBTR' in settings:
        integer(settings['RationingHistoryHorizonBTR'], 'RationingHistoryHorizonBTR')
    return enabled


def row_date(value):
    return date.fromisoformat(value) if type(value) is str else value


def pair(row, warehouse='WhCode'):
    values = row['SKUCode'], row[warehouse]
    if any(v is None for v in values):
        return None
    for value in values:
        ascii_equal(value, value)
    return tuple(v.rstrip(' ').upper() for v in values)


def validate_target(row):
    if set(row) != set(FIELDS):
        raise ValueError('Complete BTR history field roster required')
    for column in COLUMNS:
        name,kind = column['name'],column['type']
        value = row[name]
        if value is None:
            if not column['nullable']:
                raise ValueError('BTR history NOT NULL field required: '+name)
        elif kind == 'int':
            integer(value,name)
        elif kind == 'nvarchar':
            if type(value) is not str or '\0' in value or len(value.encode('utf-16-le')) > 2*column['length']:
                raise ValueError('BTR history target text width/type differs: '+name)
        elif kind == 'decimal':
            number=Decimal(str(value))
            if (not number.is_finite() or abs(number) >= Decimal('100000000')
                    or number != number.quantize(Decimal('.01'))):
                raise ValueError('BTR history decimal10,2 differs: '+name)
        elif kind == 'bit':
            if type(value) not in (bool,int) or value not in (0,1):
                raise ValueError('BTR history bit differs: '+name)
        elif kind == 'date':
            if type(row_date(value)) is not date:
                raise ValueError('BTR history date differs: '+name)


def source_value(column, value):
    # Native rationed output includes integral Decimal leftovers. The typed
    # integer target owns their representation; fractions are not qualified.
    if column['type']=='int' and value is not None and type(value) is not int:
        if type(value) not in (Decimal,str):
            raise ValueError('BTR history source integer type differs: '+column['name'])
        number=Decimal(value)
        if not number.is_finite() or number!=number.to_integral_value():
            raise ValueError('BTR history source integer fraction differs: '+column['name'])
        return integer(int(number),column['name'])
    return deepcopy(value)


def _unique_values(rows, key, fields, label):
    values={}
    for row in rows:
        identity=key(row)
        if identity is None:
            continue
        value=tuple(row[n] for n in fields)
        if identity in values and values[identity]!=value:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting BTR history '+label)
        values[identity]=value
    return values


def collect(today, prior, report, daily, supplier, horizon):
    """Only actual current producers and this engine's prior closing are inputs."""
    today=row_date(today)
    integer(horizon,'RationingHistoryHorizonBTR')
    integer(-horizon,'negative horizon')
    try:
        cutoff=today-timedelta(days=horizon)
    except (OverflowError,ValueError) as error:
        raise ValueError('BTR history cutoff outside date range') from error
    if not all(isinstance(rows,list) for rows in (prior,report,daily,supplier)):
        raise ValueError('Explicit BTR history owner populations required')
    for row in prior:
        validate_target(row)
    result=[deepcopy(row) for row in prior if row['ReportDate'] is None or
            row_date(row['ReportDate']) != today and row_date(row['ReportDate']) > cutoff]
    result.extend({c['name']:(today.isoformat() if c['name']=='ReportDate' else INSERT_LITERALS[c['name']]
                       if c['name'] in INSERT_LITERALS else None if c['name'] in OMITTED else source_value(c,row[c['name']]))
                   for c in COLUMNS} for row in report)
    today_rows=[row for row in result if row_date(row['ReportDate'])==today]
    target_keys={pair(r) for r in today_rows}
    receipts=_unique_values([r for r in daily if row_date(r['ReportDate'])==today and pair(r,'WHCode') in target_keys],
                           lambda r:pair(r,'WHCode'),('Receipts','Consumption'),'daily UPDATE')
    for row in today_rows:
        if pair(row) in receipts:
            row['Receipts'],row['Consumption']=receipts[pair(row)]
    # NOT NULL/int checks apply before arithmetic, as at the source INSERT/UPDATE.
    for row in result:
        validate_target(row)
    current={}
    for row in today_rows:
        current.setdefault(pair(row),[]).append(row)
    for row in result:
        if row_date(row['ReportDate'])==today-timedelta(days=1) and pair(row) in current:
            values=[]
            for incoming in current[pair(row)]:
                delta=integer(incoming['GIT']-row['GIT'],'GIT difference')
                values.append(integer(delta+incoming['Receipts'],'inferred Dispatch'))
            if len(set(values)) != 1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting BTR history adjacent-date UPDATE')
            row['Dispatch']=values[0]
        if row['Dispatch'] is not None and row['Dispatch']<0:
            row['Dispatch']=0
    totals={}
    for row in supplier:
        identity=pair(row,'WHCode')
        if identity is not None:
            totals.setdefault(identity,[]).append(row['DispatchReq'])
    for identity,values in totals.items():
        present=[integer(value,'DispatchReq') for value in values if value is not None]
        positive=sum(v for v in present if v>0)
        negative=sum(v for v in present if v<0)
        if positive and negative and (positive>=2**31 or negative<-(2**31)):
            raise ValueError('SOURCE_ORDER_AMBIGUITY: BTR history SUM accumulation overflow')
        totals[identity]=integer(sum(present),'SUM DispatchReq') if present else None
    for row in today_rows:
        if pair(row) in totals:
            row['SupplierDispatchReq']=totals[pair(row)]
    for row in result:
        validate_target(row)
    return result
