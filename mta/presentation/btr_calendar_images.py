"""Public read dispatch for dated reports. The v2 storage recipe is retained verbatim."""
from mta.presentation.btr_calendar_images_v2 import FORMAT, load, owns, save, verified_rows
from mta.presentation.btr_calendar_sources import _trend_query


def published_directory(run, item):
    from mta.presentation.operational_reports import generation
    owner = generation(run)
    if owner.version not in (2, 3) or owner.metadata['images'].get(item['image']) != item or not owns(item):
        raise ValueError('Dated BTR image does not belong to the sealed report generation')
    return owner.metadata['btr_calendar']


def published_query(run, item, *, required_fields=None):
    if required_fields is not None:
        from mta.runtime.relational_state import STORAGE_TABLES
        fields = set(required_fields)
        if not fields or not fields.issubset(dict(STORAGE_TABLES[item['table']])):
            raise ValueError('Unknown BTR trend projection fields')
        days = fields & {f'D{i}' for i in range(1,91)}
        colour = item['image'].rsplit('/',1)[1] in ('BufferTrendPhysicalInv','BufferTrendDispatch')
        if not days or (colour and days=={'D90'}):
            from mta.presentation.btr_page_dates import roster_query
            return roster_query(run, item, current_colour=bool(days))
    return _trend_query(run, published_directory(run, item), item['image'].removeprefix('closing/btr/'))
