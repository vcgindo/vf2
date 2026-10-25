"""BOR-only source admission over unchanged native fixture identity."""
import hashlib
import json
from datetime import datetime, timezone
from django.db import connection
from mta.presentation.bor_contract import RUN_ID, BUSINESS_DATE, NATIVE_DIGEST, FIELDS, PINS, recipe_digest
from mta.presentation.context import PublicationUnavailable
from mta.row_sequences import RecordRows
from mta.runtime.models import BorSourceReceipt, BorSourceRow, BorSobRow, BorMoqRow, BorInitialRemark
from mta.runtime.bor_source_schema import verify_guards

MODELS = dict(zip(FIELDS, (BorSourceRow, BorSobRow, BorMoqRow, BorInitialRemark)))
DIGEST_FIELDS = dict(zip(FIELDS, ('bor_digest','sob_digest','moq_digest','history_digest')))




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








def _production_policy(run):
    from mta.application.production_output_policy import SOURCE_SCHEMA, contract, require
    from mta.runtime.input_reader import read_input
    from mta.runtime.captured_input import SCHEMAS, origin
    from mta.runtime.input_v3 import V3
    physical = origin(run) if run.input_payload.get('schema') in SCHEMAS else run
    # V3 supports authenticated nested component reads. Fetch only this policy,
    # rather than unpacking the day's unrelated facts on every BOR request.
    components = (('input/day/production_report_schema', 'input/day/production_report_policy')
                  if physical.input_payload.get('schema') == V3 else ('day',))
    day = read_input(physical, components=components).get('day')
    from mta.presentation import terminal_bpr_delivery
    if terminal_bpr_delivery.applicable(run):
        return terminal_bpr_delivery.output_policy(run, day)
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
            raise PublicationUnavailable('historical_bor_importer_removed')
        from mta.presentation.context import selected_run
        run = selected_run()
    native_publication.require_mode()
    from mta.presentation.daily_preparation import production_branch, source_digest
    if not production_branch(run):
        raise PublicationUnavailable('native_bor_daily_publication_required')
    from mta.presentation.native_publication import identity
    identity(run)
    _production_policy(run)
    return (run, source_digest(run))

def capture_digest(rows):
    """Exact source JSON array checksum, preserving declared field insertion order."""
    checksum = hashlib.sha256(b'[')
    encoder = json.JSONEncoder(ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    for ordinal, row in enumerate(rows):
        if ordinal:
            checksum.update(b',')
        for part in encoder.iterencode(row):
            checksum.update(part.encode())
    checksum.update(b']')
    return checksum.hexdigest()


def validate_capture(name, rows, *, expected_count=None, expected_digest=None):
    if expected_count is None and expected_digest is None:
        raise ValueError('Explicit native source count/digest required')
    if type(expected_count) is not int or expected_count < 0 or not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise ValueError('Explicit source count/digest required')
    if not isinstance(rows,(list,RecordRows)) or len(rows)!=expected_count:
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
    checksum=capture_digest(rows)
    if checksum!=expected_digest:
        raise ValueError('BOR capture values differ: '+name)
    return checksum

def verify_values(run):
    values = {}
    for name, model in MODELS.items():
        fields = list(FIELDS[name])
        def rows():
            records = model.objects.filter(run=run).order_by('ordinal').values('ordinal', *fields)
            for ordinal, record in enumerate(records.iterator(chunk_size=300)):
                if record.pop('ordinal') != ordinal:
                    raise PublicationUnavailable('BOR_source_ordinal_population_changed:' + name)
                yield wire_rows(name, [record])[0]
        values[DIGEST_FIELDS[name]] = capture_digest(rows())
    return values

def admitted_sources(run=None):
    if run is None:
        run, _ = native_binding()
    run, source = native_binding(run)
    receipt = BorSourceReceipt.objects.filter(run=run).first()
    expected = dict(source_digest=source, recipe_digest=production_recipe_digest(), **verify_values(run))
    if receipt is None or any((getattr(receipt, key) != value for key, value in expected.items())):
        raise PublicationUnavailable('BOR_source_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('BOR_source_guards_changed') from exc
    return (run, receipt)

from mta.presentation.bor_contract import production_recipe_digest
