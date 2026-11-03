"""Public read dispatch for dated reports. The v2 storage recipe is retained verbatim."""
from mta.presentation.btr_calendar_images_v2 import FORMAT, load, owns, save, verified_rows
from mta.presentation.btr_calendar_sources import _trend_query


def published_directory(run, item):
    from mta.presentation.operational_reports import generation
    owner = generation(run)
    if owner.version not in (2, 3) or owner.metadata['images'].get(item['image']) != item or not owns(item):
        raise ValueError('Dated BTR image does not belong to the sealed report generation')
    return owner.metadata['btr_calendar']


def published_query(run, item):
    return _trend_query(run, published_directory(run, item), item['image'].removeprefix('closing/btr/'))
