"""Native BOR/BOROA source and stable-occurrence preparation for one daily run."""
import hashlib
import inspect
import json
from datetime import datetime, timezone
from decimal import Decimal

from django.db import connection, transaction

from mta.presentation.context import PublicationUnavailable
from mta.presentation.selective import image_metadata, image_rows
from mta.runtime.relational_state import quote
from mta.serialization import digest


PATHS = {
    'bor': {
        'SupplierDispatchReq': 'sources/production/SupplierDispatchReq',
        'SOBData': 'opening/supplier/SOBData',
        'MOQData': 'opening/supplier/MOQData',
        'BORReport_RemarkDetails': 'sources/bor/BORReport_RemarkDetails',
    },
    'boroa': {
        'BORWithOrderAllocation': 'sources/production/BORWithOrderAllocation',
        'BOROARequirement': 'sources/production/BOROARequirement',
        'BORReport_OARemarkDetails': 'sources/boroa/BORReport_OARemarkDetails',
    },
}


def _fail(message):
    raise PublicationUnavailable(message)


def _modules(layer):
    if layer == 'bor':
        from mta.presentation import bor_sources as sources, bor_preparation as prepared
        from mta.presentation.bor_contract import FIELDS, production_recipe_digest as source_recipe
        from mta.presentation.bor_prepared_fields import production_recipe_digest as prepared_recipe
        from mta.runtime.models import BorSourceReceipt, BorPreparedReceipt, BorPreparedRow
        from mta.runtime import bor_source_schema, bor_prepared_schema
        return (sources, prepared, FIELDS, source_recipe, prepared_recipe,
                BorSourceReceipt, BorPreparedReceipt, BorPreparedRow,
                bor_source_schema, bor_prepared_schema)
    if layer == 'boroa':
        from mta.presentation import boroa_sources as sources, boroa_preparation as prepared
        from mta.presentation.boroa_contract import (SOURCE_FIELDS as FIELDS,
            production_source_recipe as source_recipe, production_prepared_recipe as prepared_recipe)
        from mta.runtime.boroa_models import (BorOaSourceReceipt, BorOaPreparedReceipt,
                                              BorOaPreparedRow)
        from mta.runtime import boroa_source_schema, boroa_prepared_schema
        return (sources, prepared, FIELDS, source_recipe, prepared_recipe,
                BorOaSourceReceipt, BorOaPreparedReceipt, BorOaPreparedRow,
                boroa_source_schema, boroa_prepared_schema)
    raise ValueError('unknown_native_bor_layer:' + str(layer))


def production_recipe_digest(layer):
    modules = _modules(layer)
    from mta.application.production_output_policy import contract
    from mta.presentation.native_report_colours import reference
    return digest(dict(version=1, layer=layer, output_contract=contract(),
        static_colour_reference=reference() if layer == 'boroa' else None,
        source_recipe=modules[3](), prepared_recipe=modules[4](),
        query=inspect.getsource(modules[1].query),
        builder=inspect.getsource(__import__(__name__, fromlist=['prepare']))))


def _binding(run):
    from mta.presentation.daily_preparation import production_branch, source_digest
    if run is None or not production_branch(run):
        _fail('native_bor_daily_publication_build_required')
    from mta.presentation.native_publication import identity
    identity(run)
    from mta.presentation.bor_sources import _production_policy
    _production_policy(run)
    return source_digest(run)


def _source_rows(run, layer, name, fields):
    path = PATHS[layer][name]
    item = image_metadata(run, path)
    published = [entry[0] for entry in item['fields']]
    if item['count'] and (published != list(fields) if path.startswith('sources/production/')
                          else not set(fields) <= set(published)):
        _fail(layer.upper() + '_native_source_fields_changed:' + name)
    if path.startswith('sources/production/'):
        from mta.application.production_output_policy import require
        from mta.runtime.production_report_storage import TABLES
        table = 'production/' + name
        if item.get('table') != table or (item['count'] and [field for field, _ in TABLES.get(table, ())] != published):
            _fail(layer.upper() + '_native_source_storage_changed:' + name)
        producer = item.get('producer')
        try:
            require(producer['policy']['output_contract'])
        except (KeyError, TypeError, ValueError) as exc:
            raise PublicationUnavailable(layer.upper() +
                '_native_source_output_contract_changed:' + name) from exc
        if producer.get('input_digest') != run.input_digest:
            _fail(layer.upper() + '_native_source_input_changed:' + name)
    rows = image_rows(run, path)
    if len(rows) != item['count']:
        _fail(layer.upper() + '_native_source_count_changed:' + name)
    return rows


def _source_expected(run, layer, sources, fields, source_recipe):
    captures = {}
    for name in sources.MODELS:
        rows = _source_rows(run, layer, name, fields[name])
        wire = []
        for row in rows:
            value = {}
            for field in fields[name]:
                item = row[field]
                if isinstance(item, datetime):
                    item = item.isoformat()
                elif isinstance(item, Decimal):
                    item = str(item)
                if name == 'SOBData' and field == 'SOB' and item is not None:
                    item = float(item)
                if name == 'BORReport_RemarkDetails' and field == 'RemarkDate':
                    stamp = datetime.fromisoformat(item)
                    item = (stamp.astimezone(timezone.utc).replace(tzinfo=None)
                            if stamp.tzinfo else stamp).isoformat()
                value[field] = item
            wire.append(value)
        raw = json.dumps(wire, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        checksum = hashlib.sha256(raw).hexdigest()
        sources.validate_capture(name, wire, expected_count=len(wire), expected_digest=checksum)
        captures[name] = wire
    return captures, dict(recipe_digest=source_recipe())


def _to_model_values(fields, name, row):
    result = dict(row)
    if name == 'BORReport_RemarkDetails':
        result['RemarkDate'] = datetime.fromisoformat(result['RemarkDate'])
        if result['RemarkDate'].tzinfo is None:
            result['RemarkDate'] = result['RemarkDate'].replace(tzinfo=timezone.utc)
    elif name == 'BORReport_OARemarkDetails':
        result['RemarkDate'] = datetime.fromisoformat(result['RemarkDate'])
        if result['RemarkDate'].tzinfo is None:
            result['RemarkDate'] = result['RemarkDate'].replace(tzinfo=timezone.utc)
    return result


def _prepare_source(run, layer, source, modules, *, verify_only):
    (sources, _, fields, source_recipe, _, SourceReceipt, _, _,
     source_schema, _) = modules
    captures, expected = _source_expected(run, layer, sources, fields, source_recipe)
    expected['source_digest'] = source
    receipt = SourceReceipt.objects.filter(run=run).first()
    if receipt is None:
        if verify_only:
            _fail(layer.upper() + '_source_receipt_absent')
        if any(model.objects.filter(run=run).exists() for model in sources.MODELS.values()):
            _fail('unsealed_' + layer + '_source_rows_exist')
        source_schema.verify_guards(connection)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config(%s,%s,true)",
                           ['fresh.' + layer + '_source_build', str(run.pk)])
        for name, rows in captures.items():
            model = sources.MODELS[name]
            model.objects.bulk_create([
                model(run=run, ordinal=ordinal, **_to_model_values(fields, name, row))
                for ordinal, row in enumerate(rows)], batch_size=300)
        actual = sources.verify_values(run)
        expected_values = {sources.DIGEST_FIELDS[name]: hashlib.sha256(json.dumps(
            rows, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            for name, rows in captures.items()}
        if actual != expected_values:
            _fail(layer.upper() + '_source_typed_readback_changed')
        expected.update(actual)
        receipt = SourceReceipt.objects.create(run=run, **expected)
    else:
        expected.update(sources.verify_values(run))
        expected_values = {sources.DIGEST_FIELDS[name]: hashlib.sha256(json.dumps(
            rows, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            for name, rows in captures.items()}
        if any(expected[key] != value for key, value in expected_values.items()):
            _fail(layer.upper() + '_source_producer_values_changed')
    if any(getattr(receipt, key) != value for key, value in expected.items()):
        _fail(layer.upper() + '_source_receipt_changed')
    sources.admitted_sources(run)
    return receipt


def _prepare_occurrences(run, source_receipt, layer, modules, *, verify_only):
    (sources, prepared, _, _, prepared_recipe, _, PreparedReceipt, PreparedRow,
     _, prepared_schema) = modules
    receipt = PreparedReceipt.objects.filter(run=run).first()
    if receipt is None:
        if verify_only:
            _fail(layer.upper() + '_prepared_receipt_absent')
        if PreparedRow.objects.filter(run=run).exists():
            _fail('unsealed_' + layer + '_prepared_rows_exist')
        prepared_schema.verify_guards(connection)
        sql, params, columns = prepared.query(run)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config(%s,%s,true)",
                           ['fresh.' + layer + '_prepared_build', str(run.pk)])
            cursor.execute('INSERT INTO mta.' + quote(PreparedRow._meta.db_table) +
                ' (run_id,' + ','.join(map(quote, columns)) +
                ') SELECT %s,prepared.* FROM (' + sql + ') prepared', [run.pk, *params])
        count, rows_digest = prepared.row_receipt(run)
        receipt = PreparedReceipt.objects.create(run=run,
            source_digest=source_receipt.source_digest, recipe_digest=prepared_recipe(),
            row_count=count, rows_digest=rows_digest)
    count, rows_digest = prepared.row_receipt(run)
    expected = dict(source_digest=source_receipt.source_digest,
        recipe_digest=prepared_recipe(), row_count=count, rows_digest=rows_digest)
    if any(getattr(receipt, key) != value for key, value in expected.items()):
        _fail(layer.upper() + '_prepared_receipt_changed')
    prepared_schema.verify_guards(connection)
    return receipt


def prepare(run, layer, *, verify_only=False):
    source = _binding(run)
    modules = _modules(layer)
    with transaction.atomic():
        if not verify_only:
            type(run).objects.select_for_update().get(pk=run.pk)
        from mta.presentation.daily_preparation import assert_unchanged
        assert_unchanged(run, source)
        source_receipt = _prepare_source(run, layer, source, modules,
                                         verify_only=verify_only)
        prepared_receipt = _prepare_occurrences(run, source_receipt, layer, modules,
                                                verify_only=verify_only)
        assert_unchanged(run, source)
    source_values = {field: getattr(source_receipt, field)
                     for field in modules[0].DIGEST_FIELDS.values()}
    return dict(source_digest=source, recipe_digest=production_recipe_digest(layer),
        rows_digest=digest(dict(source=source_values, prepared=prepared_receipt.rows_digest)),
        row_count=sum(model.objects.filter(run=run).count()
                      for model in modules[0].MODELS.values()) + prepared_receipt.row_count,
        source_receipt=source_values, prepared_rows_digest=prepared_receipt.rows_digest)
