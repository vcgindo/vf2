"""Native Pick source joins and their existing allocation owner.

No keyed representative, cross-expansion or replacement of missing populations.
Unqualified native update ambiguity is rejected before calculation.
"""
from decimal import Decimal

from mta.domain.remaining_capabilities import calculate_pick_cases_state

BANDS = dict(TOR_B='to_black', TOR_R='to_red', TOY='to_yellow', TOG='to_green', TOBlue='to_blue')


def _text_key(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.isascii():
        raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: ASCII SQL text equality')
    return value.rstrip(' ').upper()


def _ordered_multimap(rows, field, *, include=None):
    result = {}
    for ordinal, row in enumerate(rows):
        if include is not None and not include(row):
            continue
        key = _text_key(row[field])
        if key is not None:
            result.setdefault(key, []).append((ordinal, row))
    return result


def _input_indexes(*, sku_attributes, location_attributes, vehicles, location_vehicles):
    sku_all = _ordered_multimap(sku_attributes, 'SKUCode')
    sku_eligible = _ordered_multimap(sku_attributes, 'SKUCode',
        include=lambda row: row['Weight'] is not None or row['Volume'] is not None)
    locations = _ordered_multimap(location_attributes, 'WHCode')
    parent_mappings = _ordered_multimap(location_vehicles, 'LocationID')
    vehicles_by_id = {}
    for vehicle in vehicles:
        vehicle_id = vehicle['VehicleID']
        if vehicle_id is not None:
            vehicles_by_id.setdefault(vehicle_id, []).append(vehicle)
    return dict(sku_all=sku_all, sku_eligible=sku_eligible, locations=locations,
                parent_mappings=parent_mappings, vehicles_by_id=vehicles_by_id)


def _joined_cases(pick_rows, indexes):
    groups, groups_by_parent = [], {}
    for pick_ordinal, row in enumerate(pick_rows):
        if row['RationedReq'] is None or Decimal(str(row['RationedReq'])) <= 0:
            continue
        parent = row['ParentWhCode']
        parent_key = _text_key(parent)
        group = groups_by_parent.get(parent_key)
        if group is None:
            applicable, ids = [], set()
            for _, mapping in indexes['parent_mappings'].get(parent_key, ()):
                vehicle_id = mapping['VehicleID']
                if vehicle_id in ids:
                    continue
                ids.add(vehicle_id)
                applicable.extend(indexes['vehicles_by_id'].get(vehicle_id, ()))
            if not applicable:
                continue  # Native inner vehicle join excludes this parent.
            vehicle = applicable[0]
            group = dict(parent=parent, vehicle=dict(name=vehicle['VehicleName'],
                weight_capacity=vehicle['Weight'], volume_capacity=vehicle['Volume']),
                vehicles=[dict(name=v['VehicleName'], weight_capacity=v['Weight'], volume_capacity=v['Volume'])
                          for v in applicable], items=[])
            groups.append(group)
            groups_by_parent[parent_key] = group
        sku_key = _text_key(row['SKUCode'])
        location_key = _text_key(row['WhCode'])
        attributes = indexes['sku_eligible'].get(sku_key, ())
        for sku_ordinal, attr in attributes:
            for location_ordinal, location in indexes['locations'].get(location_key, ()):
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


def joined_cases(*, pick_rows, sku_attributes, location_attributes, vehicles, location_vehicles):
    """Canonical eligibility, occurrence joins, and DISTINCT parent/vehicle IDs.

    Returned source ordinals identify occurrences; they are not business ranks.
    The allocation owner retains its existing permissible order within ties.
    """
    sources = dict(sku_attributes=sku_attributes, location_attributes=location_attributes,
                   vehicles=vehicles, location_vehicles=location_vehicles)
    return _joined_cases(pick_rows, _input_indexes(**sources))


def calculate_native_pick(**sources):
    indexes = _input_indexes(**{name: sources[name] for name in
        ('sku_attributes', 'location_attributes', 'vehicles', 'location_vehicles')})
    cases = _joined_cases(sources['pick_rows'], indexes)
    # The canonical second SKU join repeats cumulative rows, even for identical
    # duplicate attributes. Do not silently treat that as a single dimension.
    for case in cases:
        for item in case['items']:
            if not item['buckets']:
                continue  # No staged target exists for this excluded source row.
            attributes = [row for _, row in indexes['sku_all'].get(_text_key(item['sku']), ())]
            values = {(None if r['Weight'] is None else Decimal(str(r['Weight'])),
                       None if r['Volume'] is None else Decimal(str(r['Volume']))) for r in attributes}
            if len(values) != 1:
                raise ValueError('Native SKU UPDATE has differing dimension candidates (including unfiltered NULL rows); '
                                 f"SKU={item['sku']!r}, candidates={sorted(map(repr, values))}; "
                                 'rank qualification does not cover it')
    state=calculate_pick_cases_state(cases, allow_priority_ties=True)
    from mta.application.native_output_contracts import validate_rows
    for name in ('LogisticPickList','PickListDataForTruckFormation'):
        validate_rows(state[name],'complete/BPR/'+name,stage='pick/'+name)
    return state
