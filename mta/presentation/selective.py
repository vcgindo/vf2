"""Read only named accepted operational images; never a whole-run cache/trace."""
from django.db import connection
from mta.runtime.relational_state import load_image, CATALOG, table_sql, quote, wire_value
from mta.presentation.context import PublicationUnavailable


def image_metadata(run, path):
    item = run.production_manifest.get('images', {}).get(path)
    if not item or item['image'] != path or item['table'] not in CATALOG['tables']:
        raise PublicationUnavailable('selected_report_image_not_published:' + path)
    allowed = {name for name, _ in CATALOG['tables'][item['table']]}
    if any(name not in allowed for _, name, _ in item['fields']):
        raise PublicationUnavailable('selected_report_image_column_mismatch')
    return item


def image_rows(run, path):
    return load_image(run, image_metadata(run, path))


def image_field(run, path, field):
    item = image_metadata(run,path)
    selected = [entry for entry in item['fields'] if entry[0] == field]
    if len(selected) != 1:
        raise PublicationUnavailable('selected_metadata_column_not_published')
    _, column, kind = selected[0]
    with connection.cursor() as cursor:
        cursor.execute('SELECT vf_ordinal,'+quote(column)+' FROM '+table_sql(item['table'])+
            ' WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal',[run.pk,path])
        rows = cursor.fetchall()
    if [r[0] for r in rows] != list(range(item['count'])):
        raise ValueError('Operational metadata population/order drift')
    return [wire_value(value,kind) for _,value in rows]


def image_query(run, path):
    """Trusted manifest/schema-bound relation; values are always parameters."""
    item = image_metadata(run, path)
    return ('SELECT * FROM ' + table_sql(item['table']) +
            ' WHERE vf_run_id=%s AND vf_image=%s'), [run.pk, path]
