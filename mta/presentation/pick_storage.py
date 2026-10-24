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
    receipt = PickProjection.objects.get(run=run)
    if receipt.version != 1:
        raise ValueError('Unsupported Pick projection version')
    if run.production_manifest.get('version') in (2,3):
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
    return _write_pick_rows(run,rows,provenance=provenance,
                            calculation_digest=calculation_digest or digest(calculated))


def _write_pick_rows(run, rows, *, provenance, calculation_digest):
    """Shared typed writer; scoped callers bind rows to their accepted image."""
    if transaction.get_autocommit():
        raise ValueError('Pick projection requires the publication transaction')
    if len(json.dumps(provenance)) > 8192:
        raise ValueError('Pick provenance must remain bounded metadata')
    records = native_rows(run, rows)
    receipt = PickProjection.objects.create(run=run, calculation_digest=calculation_digest,
        rows_digest=digest(rows), row_count=len(rows), provenance=provenance)
    PickBand.objects.bulk_create(records, batch_size=500)
    if _read_rows(run, receipt) != rows:
        raise ValueError('Pick projection readback differs')
    return receipt
