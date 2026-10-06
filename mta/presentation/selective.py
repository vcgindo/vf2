"""Read only named accepted operational images; never a whole-run cache/trace."""
from django.db import connection
from mta.runtime.relational_state import load_image, CATALOG, table_sql, quote, wire_value
from mta.presentation.context import PublicationUnavailable


def image_metadata(run, path):
    if getattr(run,'kind',None) == 'LEGACY_UI_FIXTURE':
        from mta.presentation.fixture import image_metadata as fixture_metadata
        return fixture_metadata(run,path)
    from mta.presentation.daily_preparation import production_branch
    if production_branch(run) and (path == 'metadata/bpr/ColorSequence' or
            path.startswith('opening/supplier/') or path.startswith('sources/')):
        from mta.presentation.daily_sources import image_metadata as daily_metadata
        return daily_metadata(run, path)
    item = run.production_manifest.get('images', {}).get(path)
    if not item or item['image'] != path or item['table'] not in CATALOG['tables']:
        raise PublicationUnavailable('selected_report_image_not_published:' + path)
    allowed = {name for name, _ in CATALOG['tables'][item['table']]}
    if any(name not in allowed for _, name, _ in item['fields']):
        raise PublicationUnavailable('selected_report_image_column_mismatch')
    return item


def image_rows(run, path, *, metadata=None):
    from mta.presentation.daily_preparation import production_branch
    if (production_branch(run) and
            (path == 'metadata/bpr/ColorSequence' or path.startswith('opening/supplier/')
             or path.startswith('sources/'))):
        from mta.presentation.daily_sources import image_rows as daily_rows
        return daily_rows(run, path)
    item=metadata if metadata is not None else image_metadata(run,path)
    if getattr(run,'kind',None)=='LEGACY_UI_FIXTURE' and item['count']>1000000:
        raise PublicationUnavailable('fixture_bounded_history_reader_required:'+path)
    return load_image(run,item)


def image_field(run, path, field):
    item = image_metadata(run,path)
    selected = [entry for entry in item['fields'] if entry[0] == field]
    if len(selected) != 1:
        raise PublicationUnavailable('selected_metadata_column_not_published')
    from mta.presentation.daily_preparation import production_branch
    from mta.presentation import daily_opening_sob
    if production_branch(run) and path == daily_opening_sob.PATH:
        return [row[field] for row in daily_opening_sob.read(run, item)]
    _, column, kind = selected[0]
    with connection.cursor() as cursor:
        cursor.execute('SELECT vf_ordinal,'+quote(column)+' FROM '+table_sql(item['table'])+
            ' WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal',[run.pk,path])
        rows = cursor.fetchall()
    if [r[0] for r in rows] != list(range(item['count'])):
        raise ValueError('Operational metadata population/order drift')
    return [wire_value(value,kind) for _,value in rows]


def image_query(run, path, *, metadata=None):
    """Trusted manifest/schema-bound relation; values are always parameters."""
    item = metadata if metadata is not None else image_metadata(run, path)
    from mta.presentation.daily_preparation import production_branch
    from mta.presentation import daily_opening_sob
    if production_branch(run) and path == daily_opening_sob.PATH:
        return daily_opening_sob.query(run)
    from mta.presentation import daily_transit
    if production_branch(run) and path in daily_transit.MODELS:
        return daily_transit.query(run, path)
    if production_branch(run) and path in (
            'sources/bpr/BPRReport_RemarkDetails',
            'sources/bor/BORReport_RemarkDetails',
            'sources/boroa/BORReport_OARemarkDetails'):
        from mta.presentation.ancillary_live import image_query as remark_query
        return remark_query(run, path)
    if production_branch(run) and path == 'sources/planning/OpenExpediteRequests':
        from mta.presentation.daily_requests import query
        return query(run)
    if production_branch(run) and path == 'metadata/bpr/ColorSequence':
        from mta.runtime.models import DailyColorSequence
        return ('SELECT ordinal AS vf_ordinal,"Color","SequenceNo" FROM mta.' +
                quote(DailyColorSequence._meta.db_table) + ' WHERE run_id=%s'), [run.pk]
    return ('SELECT * FROM ' + table_sql(item['table']) +
            ' WHERE vf_run_id=%s AND vf_image=%s'), [run.pk, path]
