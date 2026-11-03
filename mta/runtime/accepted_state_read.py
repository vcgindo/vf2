"""Internal decoding of relational populations already accepted by their owner.

Callers establish admission, authorization and the selected run before reading.
These readers preserve persisted values and occurrence order without repeating
the diagnostic readers' content audits. They retain no rows between calls.
"""
from django.db import connection

from mta.row_sequences import RecordRows
from mta.runtime.relational_state import STORAGE_TABLES, quote, table_sql, wire_value


def _records(cursor):
    while batch := cursor.fetchmany(500):
        yield from batch


def iter_accepted_image(run, item, *, table_registry=None):
    registry = STORAGE_TABLES if table_registry is None else table_registry
    if item['table'] not in registry:
        raise ValueError('Unknown operational table')
    from mta.runtime import btr_import_image, rationing_reader, dated_history_reader
    if dated_history_reader.owns(item):
        yield from dated_history_reader.iter_image(run,item)
        return
    if btr_import_image.owns(item):
        yield from btr_import_image.iter_image(run,item,audit=False)
        return
    if rationing_reader.uses_occurrences(item):
        yield from rationing_reader.iter_image(run, item)
        return
    fields = item['fields']
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT vf_ordinal' +
            (' ,' + ','.join(quote(name) for _, name, _ in fields) if fields else '') +
            ' FROM ' + table_sql(item['table']) +
            ' WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal',
            [run.pk, item['image']])
        for record in _records(cursor):
            yield {field: wire_value(value, kind)
                   for (field, _, kind), value in zip(fields, record[1:])}


def load_accepted_image(run, item, *, table_registry=None):
    registry = STORAGE_TABLES if table_registry is None else table_registry
    if item['table'] not in registry:
        raise ValueError('Unknown operational table')
    from mta.runtime import btr_import_image, rationing_reader, dated_history_reader
    if dated_history_reader.owns(item):
        return dated_history_reader.load_image(run,item)
    if btr_import_image.owns(item):
        return btr_import_image.load(run,item,audit=False)
    if rationing_reader.uses_occurrences(item):
        return rationing_reader.load_image(run, item)
    def records():
        return iter_accepted_image(run, item, table_registry=table_registry)
    return RecordRows(item['count'], records) if item['count'] > 10000 else list(records())


def _export_value(kind, typed):
    return None if kind == 'null' else typed[('str', 'int', 'float', 'bool').index(kind)]


def iter_accepted_export(run, item):
    """Decode both persisted variable-width export formats without an audit."""
    with connection.chunked_cursor() as cursor:
        if item.get('version') == 2:
            cursor.execute('SELECT row_ordinal,0::integer AS record_kind,column_count,'
                'NULL::bigint AS column_ordinal,NULL::text AS value_type,'
                'NULL::text AS text_value,NULL::bigint AS integer_value,'
                'NULL::double precision AS real_value,NULL::boolean AS boolean_value '
                'FROM mta_state.report_export_row WHERE vf_run_id=%s AND vf_image=%s '
                'UNION ALL SELECT row_ordinal,1::integer,NULL::integer,column_ordinal,'
                'value_type,text_value,integer_value,real_value,boolean_value '
                'FROM mta_state.report_export_cell WHERE vf_run_id=%s AND vf_image=%s '
                'ORDER BY row_ordinal,record_kind,column_ordinal',
                [run.pk, item['image'], run.pk, item['image']])
            values = None
            for record in _records(cursor):
                if record[1] == 0:
                    if values is not None:
                        yield {'values': values}
                    values = []
                else:
                    values.append(_export_value(record[4], record[5:]))
            if values is not None:
                yield {'values': values}
        else:
            cursor.execute('SELECT row_ordinal,column_ordinal,value_type,text_value,'
                'integer_value,real_value,boolean_value '
                'FROM mta_state.report_export_cell WHERE vf_run_id=%s AND vf_image=%s '
                'ORDER BY row_ordinal,column_ordinal', [run.pk, item['image']])
            records = iter(_records(cursor))
            for size in item['lengths']:
                values = []
                for _ in range(size):
                    record = next(records)
                    values.append(_export_value(record[2], record[3:]))
                yield {'values': values}


def load_accepted_export(run, item):
    def records():
        return iter_accepted_export(run, item)
    return RecordRows(item['count'], records) if item['count'] > 10000 else list(records())


def read_accepted_daily(run, *, include_reports=True):
    """Reconstruct the accepted daily graph, leaving deferred reports deferred."""
    manifest = run.production_manifest

    def resolve(node):
        if 'image' in node:
            return load_accepted_image(run, manifest['images'][node['image']])
        if 'metadata' in node:
            return node['metadata']
        if 'export' in node:
            return load_accepted_export(run, node['export'])
        if 'scratch_kind' in node:
            records = [(name, resolve(value)) for name, value in node['items']]
            return (dict(records) if node['scratch_kind'] == 'dict' else
                    [{'table': name, 'rows': rows} for name, rows in records])
        return {name: resolve(value) for name, value in node['tables'].items()}

    closing = {section: resolve(state) for section, state in manifest['closing'].items()}
    reports = []
    if include_reports:
        for row in manifest['reports']:
            report = dict(stage=row['stage'], tables={name: resolve(value)
                          for name, value in row['tables'].items()})
            if 'deferred' in row:
                report.update(deferred=row['deferred'], sources={name: resolve(value)
                              for name, value in row['sources'].items()})
            reports.append(report)
    result = dict(ClosingState=[closing], DBMFinal=[closing['dbm']], Reports=reports,
        BPRReports=[{name: resolve(value) for name, value in manifest['bpr'].items()}]
                   if include_reports else [],
        Lineage=manifest['lineage'], PublicationContext=manifest['publication'])
    if 'btr' in closing:
        result['BTRFinal'] = [closing['btr']]
    return result
