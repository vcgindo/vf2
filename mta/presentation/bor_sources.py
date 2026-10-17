"""BOR-only source admission over unchanged native fixture identity."""
import hashlib
import json
from datetime import datetime, timezone
from django.db import connection
from mta.presentation import fixture
from mta.presentation.bor_contract import RUN_ID, BUSINESS_DATE, NATIVE_DIGEST, FIELDS, PINS, recipe_digest
from mta.presentation.context import PublicationUnavailable
from mta.runtime.models import BorSourceReceipt, BorSourceRow, BorSobRow, BorMoqRow, BorInitialRemark
from mta.runtime.bor_source_schema import verify_guards

MODELS = dict(zip(FIELDS, (BorSourceRow, BorSobRow, BorMoqRow, BorInitialRemark)))
DIGEST_FIELDS = dict(zip(FIELDS, ('bor_digest','sob_digest','moq_digest','history_digest')))


def _fixture_native_binding():
    run, source = fixture.binding()
    if (str(run.pk)!=RUN_ID or str(run.business_date)!=BUSINESS_DATE or
            run.kind!='LEGACY_UI_FIXTURE' or source!=NATIVE_DIGEST):
        raise PublicationUnavailable('BOR_snapshot_identity_changed')
    return run, source


def wire_rows(name, rows):
    result=[]
    for row in rows:
        values={}
        for field,kind in FIELDS[name].items():
            value=row[field]
            if kind=='datetime' and isinstance(value,datetime):
                value=value.astimezone(timezone.utc).replace(tzinfo=None).isoformat() if value.tzinfo else value.isoformat()
            values[field]=value
        result.append(values)
    return result


def _fixture_validate_capture(name, rows):
    if not isinstance(rows,list) or len(rows)!=PINS[name][0]:
        raise ValueError('BOR capture count differs: '+name)
    for row in rows:
        if list(row)!=list(FIELDS[name]):
            raise ValueError('BOR capture field order differs: '+name)
        for field,kind in FIELDS[name].items():
            v=row[field]
            if v is None and kind.startswith('nullable'): continue
            if kind=='int' and type(v) is int and -(2**31)<=v<2**31: continue
            if kind=='float' and type(v) is float: continue
            if kind=='datetime' and type(v) is str:
                datetime.fromisoformat(v)
                continue
            if kind in ('text50','nullable50','nullable100','nullable_text') and type(v) is str:
                limit=100 if kind=='nullable100' else 50
                if kind=='nullable_text' or len(v)<=limit: continue
            raise ValueError('BOR capture type/length differs: '+name+'/'+field)
    checksum=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if checksum!=PINS[name][1]:
        raise ValueError('BOR capture values differ: '+name)
    return checksum


def _fixture_verify_values(run):
    values={}
    for name,model in MODELS.items():
        records=list(model.objects.filter(run=run).order_by('ordinal').values('ordinal',*FIELDS[name]))
        if [r['ordinal'] for r in records]!=list(range(PINS[name][0])):
            raise ValueError('BOR source occurrence identity changed: '+name)
        values[DIGEST_FIELDS[name]]=validate_capture(name,wire_rows(name,records))
    return values


def _fixture_admitted_sources():
    from mta.presentation.daily_preparation import require_report
    require_report('bor')
    run,source=native_binding()
    receipt=BorSourceReceipt.objects.filter(run=run).first()
    expected={'source_digest':source,'recipe_digest':recipe_digest(),
              **{DIGEST_FIELDS[n]:pin[1] for n,pin in PINS.items()}}
    if receipt is None or any(getattr(receipt,k)!=v for k,v in expected.items()):
        raise PublicationUnavailable('BOR_snapshot_receipt_missing_or_changed')
    try: verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('BOR_snapshot_guards_changed') from exc
    return run,receipt


def _production_policy(run):
    from mta.application.production_output_policy import SOURCE_SCHEMA, contract, require
    from mta.runtime.input_reader import read_input
    day = read_input(run, components=('day',)).get('day')
    if (not isinstance(day, dict) or day.get('production_report_schema') != SOURCE_SCHEMA
            or not isinstance(day.get('production_report_policy'), dict)):
        raise PublicationUnavailable('native_bor_output_contract_required')
    try:
        require(day['production_report_policy'].get('output_contract'))
    except ValueError as exc:
        raise PublicationUnavailable('native_bor_output_contract_required') from exc
    return contract()

def native_binding(run=None):
    from mta.presentation import native_publication
    if run is None:
        if not native_publication.enabled():
            return _fixture_native_binding()
        from mta.presentation.context import selected_run
        run = selected_run()
    if run.kind == 'LEGACY_UI_FIXTURE':
        selected, source = _fixture_native_binding()
        if selected.pk != run.pk:
            raise PublicationUnavailable('BOR_snapshot_identity_changed')
        return selected, source
    native_publication.require_mode()
    from mta.presentation.daily_preparation import production_branch, source_digest
    if not production_branch(run):
        raise PublicationUnavailable('native_bor_daily_publication_required')
    from mta.presentation.native_publication import identity
    identity(run)
    _production_policy(run)
    return run, source_digest(run)

def validate_capture(name, rows, *, expected_count=None, expected_digest=None):
    if expected_count is None and expected_digest is None:
        return _fixture_validate_capture(name, rows)
    if type(expected_count) is not int or expected_count < 0 or not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise ValueError('Explicit source count/digest required')
    if not isinstance(rows,list) or len(rows)!=expected_count:
        raise ValueError('BOR capture count differs: '+name)
    for row in rows:
        if list(row)!=list(FIELDS[name]):
            raise ValueError('BOR capture field order differs: '+name)
        for field,kind in FIELDS[name].items():
            v=row[field]
            if v is None and kind.startswith('nullable'): continue
            if kind=='int' and type(v) is int and -(2**31)<=v<2**31: continue
            if kind=='float' and type(v) is float: continue
            if kind=='datetime' and type(v) is str:
                datetime.fromisoformat(v)
                continue
            if kind in ('text50','nullable50','nullable100','nullable_text') and type(v) is str:
                limit=100 if kind=='nullable100' else 50
                if kind=='nullable_text' or len(v)<=limit: continue
            raise ValueError('BOR capture type/length differs: '+name+'/'+field)
    checksum=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if checksum!=expected_digest:
        raise ValueError('BOR capture values differ: '+name)
    return checksum

def verify_values(run):
    if run.kind == 'LEGACY_UI_FIXTURE':
        return _fixture_verify_values(run)
    values={}
    for name,model in MODELS.items():
        fields=list(FIELDS[name])
        records=list(model.objects.filter(run=run).order_by('ordinal').values('ordinal',*fields))
        if [row.pop('ordinal') for row in records] != list(range(len(records))):
            raise PublicationUnavailable('BOR_source_ordinal_population_changed:'+name)
        rows=wire_rows(name,records)
        raw=json.dumps(rows,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
        values[DIGEST_FIELDS[name]]=hashlib.sha256(raw).hexdigest()
    return values

def admitted_sources(run=None):
    if run is None:
        run, _ = native_binding()
    if run.kind == 'LEGACY_UI_FIXTURE':
        return _fixture_admitted_sources()
    run,source=native_binding(run)
    receipt=BorSourceReceipt.objects.filter(run=run).first()
    expected=dict(source_digest=source,recipe_digest=production_recipe_digest(),**verify_values(run))
    if receipt is None or any(getattr(receipt,key)!=value for key,value in expected.items()):
        raise PublicationUnavailable('BOR_source_receipt_missing_or_changed')
    try: verify_guards(connection)
    except ValueError as exc: raise PublicationUnavailable('BOR_source_guards_changed') from exc
    return run,receipt

from mta.presentation.bor_contract import production_recipe_digest
