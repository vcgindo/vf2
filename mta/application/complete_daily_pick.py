"""Native Pick source joins and their existing allocation owner.

No keyed representative, cross-expansion or replacement of missing populations.
Unqualified native update ambiguity is rejected before calculation.
"""
from decimal import Decimal

from mta.domain.complete_daily_scalars import ascii_equal
from mta.domain.remaining_capabilities import calculate_pick_cases_state

BANDS = dict(TOR_B='to_black', TOR_R='to_red', TOY='to_yellow', TOG='to_green', TOBlue='to_blue')


def _equal(a, b):
    return a is not None and b is not None and ascii_equal(a, b)


def joined_cases(*, pick_rows, sku_attributes, location_attributes, vehicles, location_vehicles):
    """Canonical eligibility, occurrence joins, and DISTINCT parent/vehicle IDs.

    Returned source ordinals identify occurrences; they are not business ranks.
    The allocation owner retains its existing permissible order within ties.
    """
    groups = []
    for pick_ordinal, row in enumerate(pick_rows):
        if row['RationedReq'] is None or Decimal(str(row['RationedReq'])) <= 0:
            continue
        parent = row['ParentWhCode']
        group = next((g for g in groups if _equal(g['parent'], parent)), None)
        if group is None:
            applicable, ids = [], set()
            for mapping in location_vehicles:
                if not _equal(mapping['LocationID'], parent) or mapping['VehicleID'] in ids:
                    continue
                ids.add(mapping['VehicleID'])
                applicable.extend(v for v in vehicles if v['VehicleID'] is not None and v['VehicleID']==mapping['VehicleID'])
            if not applicable:
                continue  # Native inner vehicle join excludes this parent.
            vehicle = applicable[0]
            group = dict(parent=parent, vehicle=dict(name=vehicle['VehicleName'],
                weight_capacity=vehicle['Weight'], volume_capacity=vehicle['Volume']),
                vehicles=[dict(name=v['VehicleName'], weight_capacity=v['Weight'], volume_capacity=v['Volume'])
                          for v in applicable], items=[])
            groups.append(group)
        attributes = [(i, a) for i, a in enumerate(sku_attributes)
                      if _equal(a['SKUCode'], row['SKUCode'])
                      and (a['Weight'] is not None or a['Volume'] is not None)]
        for sku_ordinal, attr in attributes:
            for location_ordinal, location in enumerate(location_attributes):
                if not _equal(location['WHCode'], row['WhCode']):
                    continue
                buckets = {modern: row[native] for native, modern in BANDS.items()
                           if row[native] is not None and Decimal(str(row[native])) > 0}
                # UNPIVOT drops NULL; positive filter drops zero/negative. An
                # absent band has no allocation occurrence, not a NULL-to-zero
                # replacement in a stored native source row.
                group['items'].append(dict(case=f'pick-{pick_ordinal}-{sku_ordinal}-{location_ordinal}',
                    sku=row['SKUCode'], from_location=row['ParentWhCode'], to_location=row['WhCode'],
                    logistics_location=(location['LogisticsLocation'] if location['LogisticsLocation'] is not None
                                        else row['WhCode']), dispatch_color=row['DispatchColor'],
                    weight=attr['Weight'], volume=attr['Volume'], buckets=buckets,
                    _join_multiplicity=len(attributes),
                    source_occurrence=(pick_ordinal, sku_ordinal, location_ordinal)))
    return groups


def calculate_native_pick(**sources):
    cases = joined_cases(**sources)
    # The canonical second SKU join repeats cumulative rows, even for identical
    # duplicate attributes. Do not silently treat that as a single dimension.
    for case in cases:
        for item in case['items']:
            if not item['buckets']:
                continue  # No staged target exists for this excluded source row.
            attributes = [r for r in sources['sku_attributes'] if _equal(r['SKUCode'],item['sku'])]
            values = {(None if r['Weight'] is None else Decimal(str(r['Weight'])),
                       None if r['Volume'] is None else Decimal(str(r['Volume']))) for r in attributes}
            if len(values) != 1:
                raise ValueError('Native SKU UPDATE has differing dimension candidates (including unfiltered NULL rows); '
                                 f"SKU={item['sku']!r}, candidates={sorted(map(repr, values))}; "
                                 'rank qualification does not cover it')
    return calculate_pick_cases_state(cases, allow_priority_ties=True)
