"""Selected UpdateInTransitDataTags: standard-attribute tags, not GIT quantities."""
from copy import deepcopy
from mta.application.r1_norm_updates import key

FIELDS = ('SKUCode', 'WhCode', 'Tags')


def validate_tag_input(rows):
    if not isinstance(rows, list):
        raise ValueError('Transit tag source must be a row list')
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError('Invalid standard-attribute tag fields')
        if any(row[f] is not None and
               (not isinstance(row[f],str) or not row[f].strip()) for f in FIELDS[:2]):
            raise ValueError('Tag identity required')
        if row['Tags'] is not None and not isinstance(row['Tags'],str):
            raise ValueError('Tag must be text or null')


def update_transit_tags(rows, seasons, phase_out):
    validate_tag_input(rows)
    result = deepcopy(rows)
    # Canonical SQL includes statuses1 and7, and does not clear unrelated tags.
    # SQL equality joins never match a NULL identity, including NULL to NULL.
    seasonal = {key(r) for r in seasons
                if r['SKUCode'] is not None and r['WhCode'] is not None
                and r['Status'] is not None and r['Status'] not in (-1,21,22,23)}
    phase = {key(r) for r in phase_out
             if r['SKUCode'] is not None and r['WhCode'] is not None}
    phase |= {key(dict(SKUCode=r['PhaseInSKUCode'],WhCode=r['WhCode']))
              for r in phase_out if r.get('PhaseInSKUCode') is not None
              and r['WhCode'] is not None}
    for row in result:
        if row['SKUCode'] is None or row['WhCode'] is None:
            continue
        if key(row) in seasonal:
            row['Tags'] = 'Seasonality'
        if key(row) in phase:
            row['Tags'] = 'PIPO'
    return result
