"""Live transactional capture only; accepted runs cannot be backfilled here."""
from django.db import connection, transaction
from mta.application.operational_capture import BAND_MAP, STOCK_FIELDS, CAPTURE_POLICY, capture_rows
from mta.runtime.operational_source_models import (
    OperationalCaptureAuthorization, OperationalCalculationSource, OperationalRequirementBand, OperationalAdvanceStock,
)
from mta.serialization import digest


def authorize_new_run(run):
    from mta.runtime.input_reader import read_input
    if (transaction.get_autocommit() or run.status != 'RUNNING' or run.completed_at is not None
            or run.output_digest or run.production_digest):
        raise ValueError('Operational authorization requires a new uncalculated run')
    profile = read_input(run, components=('profile',))['profile']
    if profile.get('operational_sources') != CAPTURE_POLICY:
        raise ValueError('Persisted operational source opt-in required')
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.operational_capture_authorize', %s, true)", [str(run.pk)])
    return OperationalCaptureAuthorization.objects.create(run=run, policy=CAPTURE_POLICY,
                                                          input_digest=run.input_digest)


def _rows(source):
    output = {}
    for name, model, fields, count in (
        ('requirement_bands', OperationalRequirementBand, [name for name, _ in BAND_MAP], source.band_count),
        ('advance_stock_allocations', OperationalAdvanceStock, STOCK_FIELDS, source.stock_count),
    ):
        rows = []
        for ordinal, row in enumerate(model.objects.filter(source=source).order_by('ordinal').values('ordinal', *fields)):
            if row.pop('ordinal') != ordinal:
                raise ValueError('Operational producer ordinal drift')
            rows.append(row)
        if len(rows) != count:
            raise ValueError('Operational producer population drift')
        output[name] = rows
    if digest(output) != source.rows_digest:
        raise ValueError('Operational producer value drift')
    return output


def write_source(run, calculated, *, calculation_digest):
    _require_writer(run)
    if calculation_digest != digest(calculated):
        raise ValueError('Operational live calculation identity differs')
    return _store_rows(run,capture_rows(calculated),calculation_digest=calculation_digest)


def _require_writer(run):
    from mta.runtime.input_reader import read_input
    if transaction.get_autocommit() or run.status != 'RUNNING':
        raise ValueError('Live operational capture requires the production transaction')
    authorization = OperationalCaptureAuthorization.objects.get(run=run)
    if (authorization.policy != CAPTURE_POLICY or authorization.input_digest != run.input_digest
            or read_input(run, components=('profile',))['profile'].get('operational_sources') != CAPTURE_POLICY):
        raise ValueError('Immutable operational source authorization differs')
    if OperationalCalculationSource.objects.filter(run=run).exists():
        raise ValueError('Operational producer already captured')


def _write_source_rows(run, rows, *, calculation_digest):
    """Finite rows captured at BPR; caller must prove their accepted snapshot."""
    from mta.runtime.ingestion_context import sha
    _require_writer(run)
    sha(calculation_digest)
    return _store_rows(run,rows,calculation_digest=calculation_digest)


def _store_rows(run,rows,*,calculation_digest):
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.operational_capture_run', %s, true)", [str(run.pk)])
    source = OperationalCalculationSource.objects.create(run=run, policy=CAPTURE_POLICY,
        input_digest=run.input_digest, calculation_digest=calculation_digest,
        rows_digest=digest(rows), band_count=len(rows['requirement_bands']),
        stock_count=len(rows['advance_stock_allocations']))
    for name, model in (('requirement_bands', OperationalRequirementBand),
                        ('advance_stock_allocations', OperationalAdvanceStock)):
        model.objects.bulk_create([model(source=source, ordinal=i, **row)
                                   for i, row in enumerate(rows[name])], batch_size=200)
    if _rows(source) != rows:
        raise ValueError('Live operational capture readback differs')
    return source


def read_source(run):
    if run.status != 'SUCCEEDED':
        raise ValueError('Operational materialization requires a completed calculation')
    source = OperationalCalculationSource.objects.get(run=run)
    if source.policy != CAPTURE_POLICY or source.input_digest != run.input_digest:
        raise ValueError('Operational producer source owner differs')
    return _rows(source)
