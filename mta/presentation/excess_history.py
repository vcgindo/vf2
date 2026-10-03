"""Approved preview opening plus existing typed, per-run Excess projections.

This does not execute days or change their state. Publication is additive and
atomic, and requires a comparison against independently retained legacy facts.
"""
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction

from mta.presentation.context import PublicationUnavailable
from mta.presentation.excess import PRODUCER_SHA
from mta.presentation.excess_storage import read_excess, write_excess
from mta.presentation.selective import image_rows
from mta.runtime.models import CalculationRun, ExcessProjection
from mta.serialization import digest

TERMINAL_ID = 'ac1612c8-0e49-4155-83c3-f59f41422293'
TERMINAL_DIGEST = 'bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d'
OPENING = {'business_date': '2026-06-06', 'ExcessInventoryDetails': []}


def run_identity(run):
    return dict(run_id=str(run.pk), business_date=str(run.business_date),
        predecessor_id=str(run.predecessor_id) if run.predecessor_id else None,
        input_digest=run.input_digest, output_digest=run.output_digest,
        production_digest=run.production_digest, parity_digest=digest(run.parity_summary))


def check_binding(terminal, value):
    if (str(terminal.pk) != TERMINAL_ID or terminal.output_digest != TERMINAL_DIGEST or
            value.get('version') != 'fresh-excess-history-v1' or
            value.get('opening') != OPENING or value.get('retention_days') != 90 or
            value.get('producer_sha256') != PRODUCER_SHA):
        raise PublicationUnavailable('excess_history_approval_binding_mismatch')


def checked_chain(terminal, value, *, lookup=None):
    check_binding(terminal, value)
    runs, current = [], terminal
    while current is not None and len(runs) < 13:
        if (current.kind != 'DAILY_CHAIN' or current.status != 'SUCCEEDED' or
                current.parity_summary.get('status') not in ('PASS', 'PASS_WITH_LEGACY_FLAWS')):
            raise PublicationUnavailable('excess_history_requires_accepted_chain')
        runs.append(current)
        current = (lookup.get(str(current.predecessor_id)) if lookup is not None
                   else current.predecessor)
    runs.reverse()
    if (len(runs) != 12 or current is not None or runs[0].predecessor_id is not None or
            [run.business_date for run in runs] != [date(2026, 6, 6) + timedelta(days=i) for i in range(12)] or
            [run_identity(run) for run in runs] != value.get('runs')):
        raise PublicationUnavailable('excess_history_chain_mismatch')
    return runs


def persisted_chain(terminal, value):
    entries = value.get('runs')
    if not isinstance(entries, list) or len(entries) != 12:
        raise PublicationUnavailable('excess_history_chain_mismatch')
    lookup = {str(run.pk): run for run in CalculationRun.objects.filter(
        pk__in=[entry['run_id'] for entry in entries]).only('id', 'business_date',
            'predecessor_id', 'input_digest', 'output_digest', 'production_digest',
            'parity_summary', 'kind', 'status')}
    return checked_chain(terminal, value, lookup=lookup)


def selected_manifest(terminal):
    path = getattr(settings, 'VF_MTA_EXCESS_HISTORY_FILE', '')
    expected = getattr(settings, 'VF_MTA_EXCESS_HISTORY_SHA256', '')
    if not path or not expected:
        raise PublicationUnavailable('excess_history_input_not_configured')
    try:
        raw = Path(path).read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise PublicationUnavailable('excess_history_input_unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != expected:
        raise PublicationUnavailable('excess_history_input_hash_mismatch')
    check_binding(terminal, value)
    return value


def native_output(run):
    return dict(BPRReports=[{'vf_RationedReqReport': image_rows(run, 'reports/bpr/vf_RationedReqReport')}],
        ClosingState=[{'dbm': {'SKULocStandardAttributes': image_rows(run, 'closing/dbm/SKULocStandardAttributes')}}])


def projection_identity(run):
    fields = ('producer_sha256', 'source_digest', 'rows_digest', 'row_count')
    value = ExcessProjection.objects.filter(run=run).values(*fields).first()
    if value is None:
        raise PublicationUnavailable('excess_history_day_not_published:' + str(run.business_date))
    return dict(run_id=str(run.pk), **value)


def admission_identity(terminal, value, *, runs=None):
    runs = persisted_chain(terminal, value) if runs is None else runs
    records = {str(row['run_id']): {**row, 'run_id': str(row['run_id'])}
        for row in ExcessProjection.objects.filter(run__in=runs).values(
            'run_id', 'producer_sha256', 'source_digest', 'rows_digest', 'row_count')}
    actual = [records.get(str(run.pk)) for run in runs]
    if actual != value.get('projections'):
        raise PublicationUnavailable('excess_history_projection_identity_mismatch')
    return dict(runs=[run_identity(run) for run in runs], projections=actual)


def read_history(terminal, value):
    runs = persisted_chain(terminal, value)
    admission_identity(terminal, value, runs=runs)
    rows = []
    for run in runs:
        rows.extend(read_excess(run, output=native_output(run)))
    return rows


@transaction.atomic
def publish_history(terminal_id, value, comparison_path):
    """Explicit maintenance operation; never called by a reporting request."""
    terminal = CalculationRun.objects.select_for_update().get(pk=terminal_id)
    runs = persisted_chain(terminal, value)
    raw = Path(comparison_path).read_bytes()
    comparison = json.loads(raw)
    if (hashlib.sha256(raw).hexdigest() != value.get('comparison_sha256') or
            comparison.get('status') != 'PASS_EXCESS_HISTORY' or
            comparison.get('runs') != value['runs'] or comparison.get('opening') != OPENING or
            comparison.get('producer_sha256') != PRODUCER_SHA or
            comparison.get('projections') != value.get('projections')):
        raise PublicationUnavailable('excess_history_independent_comparison_required')
    for original in runs:
        run = CalculationRun.objects.select_for_update().get(pk=original.pk)
        if run_identity(run) != run_identity(original):
            raise PublicationUnavailable('excess_history_run_changed_during_publication')
        output = native_output(run)
        if ExcessProjection.objects.filter(run=run).exists():
            read_excess(run, output=output)
        else:
            write_excess(run, output)
    admission_identity(terminal, value)
    return [projection_identity(run) for run in runs]
