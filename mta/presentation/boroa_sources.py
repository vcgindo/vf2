"""Admission and exact readback of the isolated BOR-OA opening snapshot."""
from datetime import datetime
from decimal import Decimal,InvalidOperation
from django.db import connection
from mta.presentation.bor_sources import native_binding as bor_native_binding, capture_digest
from mta.presentation.boroa_contract import SOURCE_FIELDS,PINS,source_recipe
from mta.presentation.context import PublicationUnavailable
from mta.runtime.boroa_models import BorOaSourceRow,BorOaRequirement,BorOaInitialRemark,BorOaSourceReceipt

MODELS={'BORWithOrderAllocation':BorOaSourceRow,'BORReport_OARemarkDetails':BorOaInitialRemark,'BOROARequirement':BorOaRequirement}
DIGEST_FIELDS={'BORWithOrderAllocation':'allocation_digest','BORReport_OARemarkDetails':'history_digest','BOROARequirement':'requirement_digest'}







def native_binding(run=None):
    return bor_native_binding(run)

def validate_capture(name,rows, *, expected_count=None, expected_digest=None):
    if expected_count is None and expected_digest is None:
        raise ValueError('Explicit native source count/digest required')
    if type(expected_count) is not int or expected_count < 0 or not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise ValueError('Explicit source count/digest required')
    if len(rows)!=expected_count:raise ValueError('BOROA capture count differs: '+name)
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
    sha=capture_digest(rows)
    if sha!=expected_digest:raise ValueError('BOROA capture values differ: '+name)
    return sha

def verify_values(run):
    if run.kind == 'LEGACY_UI_FIXTURE':
        return _fixture_verify_values(run)
    values={}
    for name,model in MODELS.items():
        fields=list(SOURCE_FIELDS[name])
        def rows():
            records=model.objects.filter(run=run).order_by('ordinal').values('ordinal',*fields)
            for ordinal,record in enumerate(records.iterator(chunk_size=300)):
                if record.pop('ordinal') != ordinal:
                    raise PublicationUnavailable('BOROA_source_ordinal_population_changed:'+name)
                row={}
                for field,spec in SOURCE_FIELDS[name].items():
                    value=record[field]
                    if spec['kind']=='datetime' and value is not None:
                        value=value.isoformat()
                    elif spec['kind']=='decimal' and value is not None:
                        value=str(value)
                    row[field]=value
                yield row
        values[DIGEST_FIELDS[name]]=capture_digest(rows())
    return values

def admitted_sources(run=None):
    if run is None:
        run, _ = native_binding()
    if run.kind == 'LEGACY_UI_FIXTURE':
        return _fixture_admitted_sources()
    run,source=native_binding(run)
    receipt=BorOaSourceReceipt.objects.filter(run=run).first()
    expected=dict(source_digest=source,recipe_digest=production_source_recipe(),**verify_values(run))
    if receipt is None or any(getattr(receipt,key)!=value for key,value in expected.items()):
        raise PublicationUnavailable('BOROA_source_receipt_missing_or_changed')
    from mta.runtime.boroa_source_schema import verify_guards
    try: verify_guards(connection)
    except ValueError as exc: raise PublicationUnavailable('BOROA_source_guards_changed') from exc
    return run,receipt

from mta.presentation.boroa_contract import production_source_recipe
