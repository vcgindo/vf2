"""Offline one-time installation of the two approved historical RRR traces."""
import hashlib
import json
import os
from pathlib import Path
from django.db import connection, transaction
from mta.presentation.daily_rrr_colour import OUTPUT_FIELDS, SOURCE_SQL_SHA256, norm_rrr_colour_rows
from mta.presentation.daily_rrr_storage import (
    VERSION, OWNER_GUC,
    _owned_scope, _publication_values, _read_rows)
from mta.runtime.daily_rrr_models import DailyRrrColourReceipt, DailyRrrColourRow
from mta.runtime.models import CalculationRun, Checkpoint
from mta.serialization import digest, storage

_EVIDENCE_ROOT = (Path('D:/freshvcf-build/evidence/daily-publication-3006-20261006-001')
                  if os.name == 'nt' else Path('/evidence'))
ORACLE_PROOFS = {
    '63c71fa7-944d-4547-a80f-2316a580d3c7': (
        _EVIDENCE_ROOT / 'rrr-colour-day1-producer-001.json',
        '5e9ac8ae3e6a81def2cd1c454c6c3941864219d594d304d46e878a19ff5a355e'),
    '17f0eb84-7b6d-40e9-a288-9441a4d7a860': (
        _EVIDENCE_ROOT / 'rrr-colour-day2-producer-002.json',
        'eb04a6f6f680674e73dac2f5226d4fc5c733dedab31573188a9c5f66159cff56'),
}
_CAPABILITIES = ('r1_requirement_band', 'r1_advance_stock_allocation',
                 'r1_order_route', 'r1_order_bpp')


def _one(calculated, name):
    matches = [entry['rows'] for entry in calculated
               if isinstance(entry, dict) and entry.get('capability') == name
               and set(entry) == {'capability', 'rows'}]
    if len(matches) != 1 or not isinstance(matches[0], list):
        raise ValueError('RRR colour requires exactly one complete capability: ' + name)
    return matches[0]


def _source_inputs(run, output, calculated):
    # read_daily names the verified production projection BPRReports; the
    # retained validation archive calls that same final producer BPRFinal.
    bpr_key = 'BPRReports' if 'BPRReports' in output else 'BPRFinal'
    if len(output.get(bpr_key, ())) != 1 or len(output.get('ClosingState', ())) != 1:
        raise ValueError('RRR colour requires one final BPR and closing state')
    capabilities = {name: _one(calculated, name) for name in _CAPABILITIES}
    # AllocatedOrders is not a modern capability. Its empty value is admitted
    # only for the two run IDs above after complete empty route/BPP populations
    # and every produced order-requirement bucket are checked by the producer.
    order = dict(r1_order_route=capabilities['r1_order_route'],
                 r1_order_bpp=capabilities['r1_order_bpp'], AllocatedOrders=[])
    source = dict(
        rationed_report=output[bpr_key][0]['vf_RationedReqReport'],
        requirement_bands=capabilities['r1_requirement_band'],
        bpr_master=output['ClosingState'][0]['bpr']['BPRMaster'],
        advance_stock_allocations=capabilities['r1_advance_stock_allocation'],
        order_capabilities=order,
        context=dict(run_id=str(run.pk), instance_port=3006, synthetic=True,
                     is_mto_environment=0, order_capabilities_complete=True))
    rows = storage(norm_rrr_colour_rows(**source))
    identity = storage(dict(rationed_report=source['rationed_report'],
        requirement_bands=source['requirement_bands'], bpr_master=source['bpr_master'],
        advance_stock_allocations=source['advance_stock_allocations'],
        r1_order_route=order['r1_order_route'], r1_order_bpp=order['r1_order_bpp'],
        allocated_orders_scope='proved-empty-for-approved-MTO0-smoke-runs-only'))
    return rows, digest(identity)


def _proof_rows(rows):
    if not isinstance(rows, list):
        raise ValueError('RRR colour independent SQL proof bag is unavailable')
    result = []
    for source in rows:
        if not isinstance(source, dict) or set(source) != set(OUTPUT_FIELDS):
            raise ValueError('RRR colour independent SQL proof row shape differs')
        row = dict(source)
        value = row['RationedCasePacks']
        if value is not None:
            try:
                integer = int(value)
            except (TypeError, ValueError):
                raise ValueError('RRR colour proof case-pack representation differs') from None
            if str(integer) != str(value):
                raise ValueError('RRR colour proof case-pack representation differs')
            row['RationedCasePacks'] = integer
        result.append(row)
    return storage(result)


def _proof(run, rows):
    path, expected_sha = ORACLE_PROOFS[str(run.pk)]
    raw = path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError('RRR colour independent SQL proof checksum differs')
    value = json.loads(raw)
    expected = dict(run_id=str(run.pk), output_digest=run.output_digest,
        producer_sha256=SOURCE_SQL_SHA256,
        gate='approved-MTO0-exception-not-canonical-gating-parity', status='PASS')
    if any(value.get(key) != item for key, item in expected.items()):
        raise ValueError('RRR colour independent SQL proof identity differs')
    if (_proof_rows(value.get('modern')) != rows
            or _proof_rows(value.get('legacy')) != rows
            or value.get('missing') != [] or value.get('extra') != []):
        raise ValueError('RRR colour independent SQL proof bag differs')
    return dict(path=path.name, sha256=actual_sha, status=value['status'],
                gate=value['gate'])


def _metadata(run, checkpoint, proof):
    value = dict(schema=VERSION, scope='owned-3006-two-run-norm-only',
        sql_sha256=SOURCE_SQL_SHA256, calculation_checkpoint=dict(
            digest=checkpoint.digest, row_count=checkpoint.row_count,
            evidence_path=checkpoint.evidence_path,
            evidence_sha256=checkpoint.evidence_sha256), oracle_proof=proof,
        parity_receipt_sha256=run.parity_summary.get('sha256'))
    if len(json.dumps(value, sort_keys=True, default=str)) > 16384:
        raise ValueError('RRR colour receipt metadata is not bounded')
    return storage(value)


@transaction.atomic
def install(run_id, *, expected_output_digest, expected_seal):
    """Offline one-time transfer from verified accepted trace to typed rows."""
    from mta.runtime.services import read_outputs
    from development.validation_storage import evidence_path
    from parity.output_archive import iter_rows

    run = CalculationRun.objects.select_for_update().get(pk=run_id)
    _owned_scope(run)
    expected = _publication_values(run, expected_output_digest=expected_output_digest,
                                   expected_seal=expected_seal)
    output = read_outputs(run)
    checkpoint = Checkpoint.objects.get(run=run, name='CalculationOutputs')
    expected_path = str(run.pk) + '/CalculationOutputs.jsonl.gz'
    if checkpoint.rows != [] or checkpoint.evidence_path != expected_path:
        raise ValueError('RRR colour retained calculation source owner/storage differs')
    calculated = list(iter_rows(evidence_path(run, 'CalculationOutputs'), dict(
        sha256=checkpoint.evidence_sha256, digest=checkpoint.digest,
        row_count=checkpoint.row_count)))
    rows, source_inputs_digest = _source_inputs(run, output, calculated)
    proof = _proof(run, rows)
    metadata = _metadata(run, checkpoint, proof)
    identities = dict(**expected, source_inputs_digest=source_inputs_digest,
        row_count=len(rows), rows_digest=digest(rows), metadata=metadata,
        metadata_digest=digest(metadata))
    prior = DailyRrrColourReceipt.objects.filter(run=run).first()
    if prior is not None:
        if any(getattr(prior, field) != value for field, value in identities.items()):
            raise ValueError('RRR colour idempotent receipt identity differs')
        if _read_rows(prior) != rows:
            raise ValueError('RRR colour idempotent typed readback differs')
        return prior
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s,%s,true)", [OWNER_GUC, str(run.pk)])
    receipt = DailyRrrColourReceipt.objects.create(run=run, **identities)
    DailyRrrColourRow.objects.bulk_create([
        DailyRrrColourRow(receipt=receipt, ordinal=ordinal, **row)
        for ordinal, row in enumerate(rows)
    ], batch_size=500)
    if _read_rows(receipt) != rows:
        raise ValueError('RRR colour typed readback differs')
    return receipt

