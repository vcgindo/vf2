"""Store calculated Pick bands as typed report facts; never calculate them here.

Operational requests use read_pick_bands only. The separately invoked restore
path is a one-time transfer from a run's verified modern calculation evidence;
it cannot select another run, change its accepted receipts, or read legacy rows.
"""
import json

from django.db import transaction

from mta.runtime.models import CalculationRun, Checkpoint, PickBand, PickProjection
from mta.serialization import digest

IDENTITY_FIELDS = ('sku_code', 'location_code', 'parent_location_code')
BAND_FIELDS = ('to_black', 'to_red', 'to_yellow', 'to_green', 'to_blue')
FIELDS = IDENTITY_FIELDS + BAND_FIELDS


def selected_bands(calculated):
    selected = [r['rows'] for r in calculated if r['capability'] == 'r1_ration_bifurcation']
    if len(selected) != 1:
        raise ValueError('Exactly one produced Pick-band population required')
    return selected[0]


def native_rows(run, rows):
    result = []
    for ordinal, row in enumerate(rows):
        if set(row) != set(FIELDS):
            raise ValueError('Pick-band producer shape differs')
        if any(not isinstance(row[k], str) or not row[k] or len(row[k]) > 50 for k in IDENTITY_FIELDS):
            raise ValueError('Pick-band identity is not a canonical code')
        values = {}
        for field in BAND_FIELDS:
            value = row[field]
            if not isinstance(value, str) or str(int(value)) != value:
                raise ValueError('Pick-band wire value is not a canonical integer string')
            values[field] = int(value)
        result.append(PickBand(run=run, ordinal=ordinal,
            **{k: row[k] for k in IDENTITY_FIELDS}, **values))
    return result


def read_pick_bands(run):
    """Only relational rows/metadata; no trace or synthetic fallback."""
    if getattr(run,'kind',None) == 'LEGACY_UI_FIXTURE':
        from mta.presentation.fixture import projection_rows
        return [{**row,**{field:str(row[field]) for field in BAND_FIELDS}}
                for row in projection_rows(run,PickBand)]
    receipt = PickProjection.objects.get(run=run)
    if receipt.version != 1:
        raise ValueError('Unsupported Pick projection version')
    if run.production_manifest.get('version')==2:
        from mta.runtime.receipt_integrity import verify_root
        verify_root(run)
    else:
        checkpoint = Checkpoint.objects.get(run=run, name='CalculationOutputs')
        if checkpoint.digest != receipt.calculation_digest:
            raise ValueError('Pick projection calculation identity differs')
    return _read_rows(run, receipt)


def _read_rows(run, receipt):
    records = list(PickBand.objects.filter(run=run).order_by('ordinal').values('ordinal', *FIELDS))
    if [r['ordinal'] for r in records] != list(range(receipt.row_count)):
        raise ValueError('Pick projection population/order drift')
    rows = [{**{k: r[k] for k in IDENTITY_FIELDS}, **{k: str(r[k]) for k in BAND_FIELDS}} for r in records]
    if digest(rows) != receipt.rows_digest:
        raise ValueError('Pick projection typed values/multiplicity drift')
    return rows


def write_pick_bands(run, calculated, *, provenance, calculation_digest=None):
    """Caller owns the production transaction; duplicate writes are forbidden."""
    if transaction.get_autocommit():
        raise ValueError('Pick projection requires the publication transaction')
    if len(json.dumps(provenance)) > 8192:
        raise ValueError('Pick provenance must remain bounded metadata')
    rows = selected_bands(calculated)
    records = native_rows(run, rows)
    receipt = PickProjection.objects.create(run=run, calculation_digest=calculation_digest or digest(calculated),
        rows_digest=digest(rows), row_count=len(rows), provenance=provenance)
    PickBand.objects.bulk_create(records, batch_size=500)
    if _read_rows(run, receipt) != rows:
        raise ValueError('Pick projection readback differs')
    return receipt


@transaction.atomic
def restore_pick_bands(run_id, *, expected_output_digest):
    """Explicit, idempotent read-model publication of an accepted retained run."""
    from mta.runtime.services import read_outputs
    from mta.runtime.validation_storage import evidence_path
    from parity.output_archive import iter_rows

    run = CalculationRun.objects.select_for_update().get(pk=run_id)
    if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED' or
            run.output_digest != expected_output_digest or
            run.parity_summary.get('status') not in ('PASS', 'PASS_WITH_LEGACY_FLAWS') or
            run.parity_summary.get('comparisons', {}).get('calculation/bifurcation') != 'PASS'):
        raise ValueError('Accepted explicit Pick calculation identity required')
    read_outputs(run)  # Validate unchanged native production/input identity first.
    if PickProjection.objects.filter(run=run).exists():
        read_pick_bands(run)
        return PickProjection.objects.get(run=run)
    checkpoint = Checkpoint.objects.get(run=run, name='CalculationOutputs')
    expected_path = str(run.pk) + '/CalculationOutputs.jsonl.gz'
    if checkpoint.evidence_path != expected_path or checkpoint.rows != []:
        raise ValueError('Retained Pick source owner/storage mismatch')
    metadata = dict(sha256=checkpoint.evidence_sha256,
                    digest=checkpoint.digest, row_count=checkpoint.row_count)
    # Exhaust the iterator: final count/logical-digest verification is mandatory.
    calculated = list(iter_rows(evidence_path(run, 'CalculationOutputs'), metadata))
    return write_pick_bands(run, calculated, provenance=dict(
        origin='retained-modern-calculation', output_digest=run.output_digest,
        production_digest=run.production_digest, evidence_path=checkpoint.evidence_path,
        evidence_sha256=checkpoint.evidence_sha256,
        parity_receipt_sha256=run.parity_summary['sha256']))
