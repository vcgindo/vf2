"""Offline typed installation and trace-free serving for approved RRR colour rows."""
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import connection

from mta.presentation.daily_rrr_colour import (
    APPROVED_SMOKE_RUN_IDS, OUTPUT_FIELDS, SMOKE_EXCEPTION, SOURCE_SQL_SHA256,
)
from mta.runtime.daily_rrr_models import DailyRrrColourReceipt, DailyRrrColourRow
from mta.serialization import digest, storage


VERSION = 'daily-rrr-colour-smoke-v1'
OWNER_GUC = 'fresh.daily_rrr_colour_install'
APPROVED_OUTPUTS = {
    '63c71fa7-944d-4547-a80f-2316a580d3c7':
        'f14806c1397661e2380ae59282db86bd1b5ca629351a61e73a3b09a407a2388b',
    '17f0eb84-7b6d-40e9-a288-9441a4d7a860':
        'e9777b060d27a77584fcc20734e5f1daba7fab38f8e1eaf99bec907cc278233f',
}



def producer_digest():
    """Bind the deployed SQL plus pure producer and storage implementation bytes."""
    from mta.presentation import daily_rrr_colour
    return digest(dict(version=VERSION, sql=SOURCE_SQL_SHA256,
        producer_sha256=hashlib.sha256(Path(daily_rrr_colour.__file__).read_bytes()).hexdigest(),
        storage_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))


def exception_digest():
    return digest(dict(version=VERSION, approval=dict(SMOKE_EXCEPTION),
                       runs=sorted(APPROVED_SMOKE_RUN_IDS)))


def _owned_scope(run):
    if getattr(settings, 'VF_MTA_RRR_COLOUR_EXTENSION', '') != VERSION:
        raise ValueError('RRR colour extension is not explicitly enabled')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        if cursor.fetchone()[0] != 'daily_3006':
            raise ValueError('RRR colour extension requires its owned daily_3006 database')
    run_id = str(run.pk)
    if (run_id not in APPROVED_OUTPUTS or run_id not in APPROVED_SMOKE_RUN_IDS
            or run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED'
            or run.output_digest != APPROVED_OUTPUTS[run_id]
            or run.parity_summary.get('status') not in ('PASS', 'PASS_WITH_LEGACY_FLAWS')):
        raise ValueError('RRR colour extension requires an exact accepted smoke run')


def _publication_values(run, *, expected_output_digest=None, expected_seal=None):
    from mta.presentation.daily_activation import require_activation
    from mta.presentation.daily_publication import require_ready, source_identity
    publication = require_ready(run)
    activation = require_activation(run, publication)
    if expected_output_digest is not None and run.output_digest != expected_output_digest:
        raise ValueError('RRR colour expected output digest differs')
    if expected_seal is not None and publication.seal_digest != expected_seal:
        raise ValueError('RRR colour expected original publication seal differs')
    if publication.output_digest != run.output_digest:
        raise ValueError('RRR colour original publication output differs')
    source = source_identity(run)
    if publication.source_digest != source:
        raise ValueError('RRR colour original publication source differs')
    return dict(output_digest=run.output_digest,
        publication_seal=publication.seal_digest,
        activation_digest=activation.activation_digest,
        publication_source_digest=source,
        producer_digest=producer_digest(), exception_digest=exception_digest())












def _read_rows(receipt):
    records = list(DailyRrrColourRow.objects.filter(receipt=receipt)
                   .order_by('ordinal').values('ordinal', *OUTPUT_FIELDS))
    if [record['ordinal'] for record in records] != list(range(receipt.row_count)):
        raise ValueError('RRR colour typed population/order drift')
    rows = storage([{field: record[field] for field in OUTPUT_FIELDS}
                    for record in records])
    if digest(rows) != receipt.rows_digest:
        raise ValueError('RRR colour typed values/multiplicity drift')
    return rows


def read(run):
    """Validate identities and return typed rows without reading trace evidence."""
    run.refresh_from_db()
    _owned_scope(run)
    expected = _publication_values(run)
    receipt = DailyRrrColourReceipt.objects.get(run=run)
    if any(getattr(receipt, field) != value for field, value in expected.items()):
        raise ValueError('RRR colour receipt identity differs')
    if (receipt.metadata_digest != digest(receipt.metadata)
            or receipt.metadata.get('schema') != VERSION
            or receipt.metadata.get('sql_sha256') != SOURCE_SQL_SHA256):
        raise ValueError('RRR colour receipt metadata differs')
    return _read_rows(receipt)
