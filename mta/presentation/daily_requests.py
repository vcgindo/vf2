"""Typed daily request input. Missing ownership is never an empty request bag.

This source boundary does not claim the absent SubmitRequest/action workflow or
nonempty prepared child-grid assembly is accepted. Their canonical port remains
separate from preserving an explicitly supplied current request population.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from django.db import transaction, connection
from mta.runtime.daily_request_models import (DailyRequestOwner, DailyOpenRequest,
    DailyRequestCapture, DailyCapturedRequest)
from mta.serialization import digest, storage

PATH = 'sources/planning/OpenExpediteRequests'
OWNER = 'OpenExpediteRequests'
FIELDS = ('SKUCode', 'WhCode', 'ParentWhCode', 'Request', 'RequestDate',
          'Action', 'ActionDate', 'UserId', 'ETA')
DATES = frozenset(('RequestDate', 'ActionDate', 'ETA'))
SCHEMA_SHA = '0cec4bea850da03b9e57d59fe114a15d68fb60254637988451b609995757a33c'


def _schema():
    raw = (Path(__file__).resolve().parents[2] /
           'baseline/planning-april-empty-requests-v1.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != SCHEMA_SHA:
        raise ValueError('Pinned deployed request schema changed')
    columns = json.loads(raw)['columns']
    if tuple(c['name'] for c in columns) != FIELDS:
        raise ValueError('Request field contract changed')


def _rows(query):
    return [{name: (value.replace(tzinfo=None).isoformat()
                   if name in DATES and value is not None else value)
             for name, value in row.items()}
            for row in query.order_by('ordinal').values(*FIELDS)]


def _typed(row):
    if not isinstance(row, dict) or set(row) != set(FIELDS):
        raise ValueError('Complete native request fields required')
    result = dict(row)
    for name, value in row.items():
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError('Request value must be native text/datetime or NULL')
        if name in DATES:
            stamp = datetime.fromisoformat(value)
            if stamp.tzinfo is not None:
                raise ValueError('Native request datetime must be a naive wall time')
            result[name] = stamp.replace(tzinfo=timezone.utc)
        elif name in FIELDS[:3] and len(value) > 50:
            raise ValueError('Request key exceeds canonical width')
    return result


@transaction.atomic
def initialize(rows, *, provenance):
    """Explicit one-time imported/initial current-state owner, including empty."""
    _schema()
    if (not isinstance(provenance, dict) or not provenance
            or len(json.dumps(provenance)) > 16384 or not isinstance(rows, list)):
        raise ValueError('Explicit bounded request provenance and rows required')
    values = [_typed(row) for row in rows]
    if DailyRequestOwner.objects.filter(pk=OWNER).exists():
        raise ValueError('Request owner already initialized')
    owner = DailyRequestOwner.objects.create(name=OWNER, provenance=provenance,
                                             provenance_digest=digest(provenance))
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.daily_request_owner',%s,true)", [OWNER])
    DailyOpenRequest.objects.bulk_create([DailyOpenRequest(owner=owner, ordinal=i,
        **row) for i, row in enumerate(values)])
    return owner


def snapshot():
    if transaction.get_autocommit():
        raise ValueError('Request snapshot requires daily input transaction')
    owner = DailyRequestOwner.objects.select_for_update().filter(pk=OWNER).first()
    if owner is None:
        return None
    _schema()
    if digest(owner.provenance) != owner.provenance_digest:
        raise ValueError('Request owner provenance drift')
    rows = _rows(DailyOpenRequest.objects.select_for_update().filter(owner=owner))
    return dict(owner=owner.pk, revision=owner.revision,
        provenance_digest=owner.provenance_digest, rows=rows, rows_digest=digest(rows))


def bind(run, value):
    if transaction.get_autocommit() or run.kind != 'DAILY_CHAIN' or run.status != 'RUNNING':
        raise ValueError('Request capture requires daily input transaction')
    if value is None:
        return
    if value['owner'] != OWNER or digest(value['rows']) != value['rows_digest']:
        raise ValueError('Frozen request source drift')
    owner = DailyRequestOwner.objects.get(pk=value['owner'])
    if owner.provenance_digest != value['provenance_digest']:
        raise ValueError('Frozen request owner drift')
    capture = DailyRequestCapture.objects.create(run=run, owner=owner,
        revision=value['revision'], provenance_digest=value['provenance_digest'],
        rows_digest=value['rows_digest'], row_count=len(value['rows']))
    DailyCapturedRequest.objects.bulk_create([DailyCapturedRequest(capture=capture,
        ordinal=i, **_typed(row)) for i, row in enumerate(value['rows'])])
    if rows(run) != value['rows']:
        raise ValueError('Typed request capture readback differs')


def rows(run):
    capture = DailyRequestCapture.objects.get(run=run)
    query = DailyCapturedRequest.objects.filter(capture=capture)
    result = _rows(query)
    if (list(query.order_by('ordinal').values_list('ordinal', flat=True)) !=
            list(range(capture.row_count)) or digest(result) != capture.rows_digest):
        raise ValueError('Request capture population/value drift')
    return result


def metadata(run):
    value = DailyRequestCapture.objects.get(run=run)
    rows(run)
    return dict(image=PATH, table=DailyCapturedRequest._meta.db_table,
        count=value.row_count, digest=value.rows_digest,
        owner=value.owner_id, revision=value.revision,
        provenance_digest=value.provenance_digest,
        fields=[[name, name, 'str'] for name in FIELDS])


def query(run):
    from mta.runtime.relational_state import quote
    metadata(run)
    return ('SELECT ordinal AS vf_ordinal,' + ','.join(map(quote, FIELDS)) +
        ' FROM mta.' + quote(DailyCapturedRequest._meta.db_table) +
        ' WHERE capture_id=%s'), [run.pk]
