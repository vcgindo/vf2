"""Typed shipment publication from explicit raw facts and current produced inputs.

This boundary cannot turn the seven-field ledger or aggregate GIT into shipment
metadata. It does not qualify the nonempty report consumers by publishing rows.
"""
from datetime import date, datetime
import inspect
import json

from django.db import transaction
from mta.application import daily_transit as processor
from mta.runtime.models import DailyTransitRaw, DailyTransitRow
from mta.runtime.relational_state import save_image, load_image, quote
from mta.serialization import digest, storage

RAW_PATH = 'sources/importer/InTransitDataRaw'
PATH = 'sources/bpr/InTransitData'
TRANSPORTER_PATH = 'sources/planning/GoodsInTransitTransporterMaster'
DIAGNOSTIC_PATH = 'sources/importer/TransitRejectedMaster'
MODELS = {RAW_PATH: (DailyTransitRaw, processor.RAW_FIELDS),
          PATH: (DailyTransitRow, processor.TRANSIT_FIELDS)}
DATES = frozenset(('CreationDate', 'GateOutDate', 'ETA', 'ReportDate'))
INTS = frozenset(('InTransitQty', 'Ageing', 'TLT', 'SLT'))


def recipe_digest():
    return digest(dict(version=1, producer=inspect.getsource(processor),
                       publisher=inspect.getsource(publish)))


def _decoded(rows, fields):
    if not isinstance(rows, list) or any(set(row) != set(fields) for row in rows):
        raise ValueError('Complete shipment row shape required')
    return [{key: (date.fromisoformat(value) if key in DATES and value is not None
                   else value) for key, value in row.items()} for row in rows]


def _save(run, path, rows):
    model, fields = MODELS[path]
    model.objects.bulk_create([model(run=run, ordinal=i, **row)
                              for i, row in enumerate(rows)])
    expected = storage(rows)
    item = dict(image=path, table=model._meta.db_table, count=len(rows),
                digest=digest(expected), fields=[
                    [field, field, 'int' if field in INTS else 'str'] for field in fields])
    if read_rows(run, path, item) != expected:
        raise ValueError('Typed transit readback differs')
    return item


def publish(run, source, *, standards, directory, rationed_report, super_delay_factor,
            run_timestamp):
    """Return source metadata inside finish_run's atomic transaction.

    Standards MUST be the current produced population, including its NULLs.
    No prior attributes are carried forward and no calculated output is edited.
    The caller supplies an explicitly declared source even for an empty bag.
    """
    if transaction.get_autocommit() or run.kind != 'DAILY_CHAIN' or run.status != 'RUNNING':
        raise ValueError('Transit publication requires running daily transaction')
    if (not isinstance(source, dict) or set(source) != {'schema', 'business_date', 'provenance', 'rows'}
            or source['schema'] != 'daily-transit-raw-v1'
            or source['business_date'] != run.business_date.isoformat()
            or not isinstance(source['provenance'], dict) or not source['provenance']
            or len(json.dumps(source['provenance'])) > 16384):
        raise ValueError('Explicit dated shipment provenance required')
    raw = _decoded(source['rows'], processor.RAW_FIELDS)
    validated = processor.validate_goods_in_transit(raw, standards, run.business_date,
                                                    run_timestamp)
    transporter = processor.transporter_master(validated['rows'], directory,
                                               rationed_report, standards, super_delay_factor)
    images = {RAW_PATH: _save(run, RAW_PATH, raw), PATH: _save(run, PATH, validated['rows'])}
    for path, binding, rows in (
            (TRANSPORTER_PATH, 'closing/consumer_context/GoodsInTransitTransporterMaster', transporter),
            (DIAGNOSTIC_PATH, 'closing/importer/RejectedMaster', validated['diagnostics'])):
        wire = storage(rows)
        images[path] = save_image(run, path, binding, wire)
        if load_image(run, images[path]) != wire:
            raise ValueError('Transit derived-source readback differs')
    ownership = dict(recipe_digest=recipe_digest(), provenance=source['provenance'],
                     source_digest=digest(source), standards_digest=digest(standards),
                     directory_digest=digest(directory), report_digest=digest(rationed_report),
                     super_delay_factor=storage(super_delay_factor),
                     run_timestamp=storage(run_timestamp))
    for item in images.values():
        item['producer'] = ownership
    return images


def read_rows(run, path, item):
    model, fields = MODELS[path]
    if item['table'] != model._meta.db_table or item['image'] != path:
        raise ValueError('Transit typed relation identity differs')
    records = list(model.objects.filter(run=run).order_by('ordinal').values('ordinal', *fields))
    if [row.pop('ordinal') for row in records] != list(range(item['count'])):
        raise ValueError('Transit occurrence population differs')
    rows = storage(records)
    if digest(rows) != item['digest']:
        raise ValueError('Transit occurrence values differ')
    return rows


def query(run, path):
    model, fields = MODELS[path]
    return ('SELECT ordinal AS vf_ordinal,' + ','.join(quote(name) for name in fields) +
            ' FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s'), [run.pk]
