"""Admission and exact readback of the isolated BOR-OA opening snapshot."""
import hashlib,json
from datetime import datetime
from decimal import Decimal,InvalidOperation
from django.db import connection
from mta.presentation.bor_sources import native_binding
from mta.presentation.boroa_contract import SOURCE_FIELDS,PINS,source_recipe
from mta.presentation.context import PublicationUnavailable
from mta.runtime.boroa_models import BorOaSourceRow,BorOaRequirement,BorOaInitialRemark,BorOaSourceReceipt

MODELS={'BORWithOrderAllocation':BorOaSourceRow,'BORReport_OARemarkDetails':BorOaInitialRemark,'BOROARequirement':BorOaRequirement}
DIGEST_FIELDS={'BORWithOrderAllocation':'allocation_digest','BORReport_OARemarkDetails':'history_digest','BOROARequirement':'requirement_digest'}

def validate_capture(name,rows):
    if len(rows)!=PINS[name][0]:raise ValueError('BOROA capture count differs: '+name)
    for row in rows:
        if list(row)!=list(SOURCE_FIELDS[name]):raise ValueError('BOROA capture field order differs')
        for field,spec in SOURCE_FIELDS[name].items():
            value=row[field];kind=spec['kind']
            if value is None and spec['nullable']:continue
            if kind=='int' and type(value)is int and -(2**31)<=value<2**31:continue
            if kind=='text' and isinstance(value,str) and (spec['length'] is None or len(value)<=spec['length']):continue
            if kind=='datetime' and isinstance(value,str):datetime.fromisoformat(value);continue
            if kind=='decimal' and isinstance(value,str):
                try:
                    d=Decimal(value)
                    if d.is_finite() and d==d.quantize(Decimal(1).scaleb(-spec['scale'])):continue
                except InvalidOperation:pass
            raise ValueError('BOROA capture type differs: '+field)
    sha=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if sha!=PINS[name][1]:raise ValueError('BOROA capture values differ: '+name)
    return sha

def verify_values(run):
    result={}
    for name,model in MODELS.items():
        records=list(model.objects.filter(run=run).order_by('ordinal').values('ordinal',*SOURCE_FIELDS[name]))
        if [r.pop('ordinal') for r in records]!=list(range(PINS[name][0])):raise ValueError('BOROA source ordinal drift')
        for row in records:
            for field,spec in SOURCE_FIELDS[name].items():
                if spec['kind']=='decimal' and row[field] is not None:row[field]=format(row[field],'.'+str(spec['scale'])+'f')
                elif spec['kind']=='datetime' and row[field] is not None:row[field]=row[field].replace(tzinfo=None).isoformat()
        result[DIGEST_FIELDS[name]]=validate_capture(name,records)
    return result

def admitted_sources():
    from mta.runtime.boroa_source_schema import verify_guards
    run,source=native_binding();receipt=BorOaSourceReceipt.objects.filter(run=run).first()
    expected=dict(source_digest=source,recipe_digest=source_recipe(),**{DIGEST_FIELDS[n]:v[1] for n,v in PINS.items()})
    if receipt is None or any(getattr(receipt,k)!=v for k,v in expected.items()):raise PublicationUnavailable('BOROA_source_receipt_missing_or_changed')
    try:verify_guards(connection)
    except ValueError as exc:raise PublicationUnavailable('BOROA_source_guards_changed') from exc
    with connection.cursor() as c:
        c.execute('SELECT row_count,values_sha256 FROM stage2_owner.tables WHERE source=%s AND table_name=%s',['Demo_BPR_1','ColorSequence'])
        if c.fetchall()!=[(7,'df43531ad52b0a1d52eafc644be78ec74366c0c1ad3feeef894bfbcb22efa5b5')]:raise PublicationUnavailable('BOROA_color_source_changed')
    return run,receipt
