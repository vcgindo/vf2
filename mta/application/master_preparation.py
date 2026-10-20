"""Changed dependency components use the existing canonical master producer.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

Unqualified and global cases retain the full canonical producer. No accepted
population cache or alternate rule engine is introduced.
"""
from copy import deepcopy

import json

from mta.application.r1_importer_master import (
    DESCRIPTIONS, PRIOR_TABLES, RAW_COLUMNS, TABLE_COLUMNS, _sql_key,
    apply_raw_ansi_padding, normalize_master_row, process_importer_master,
    validate_master_input,
)

from mta.serialization import digest, storage

CHANGE_FIELDS = frozenset(('sku', 'location', 'pair', 'retirement', 'global'))

SKU_TABLES = frozenset(('MasterData', 'SKUDescriptionTbl', 'SkuAttributeData',
    'SkuLocAttributeData', 'RetiredNormsTbl', 'RejectedMaster', 'ForceNormChange',
    'MasterDataRaw', 'MasterDataRawNonNMS', 'NoNormMasterRaw'))

LOCATION_TABLES = frozenset(('SiteDescriptionTbl', 'LocationAttributeData'))

def _ordered(rows):
    return sorted(deepcopy(rows), key=lambda row: json.dumps(row, sort_keys=True))

def _changes(value):
    if not isinstance(value, dict) or set(value) != CHANGE_FIELDS or type(value['global']) is not bool:
        return None
    if any(not isinstance(value[name], list) for name in ('sku', 'location', 'pair', 'retirement')):
        return None
    if any(not isinstance(item, str) or item == '' for name in ('sku', 'location')
           for item in value[name]):
        return None
    pairs = []
    for name in ('pair', 'retirement'):
        for row in value[name]:
            if (not isinstance(row, dict) or set(row) != {'SKUCode', 'WhCode'}
                    or any(not isinstance(row[key], str) or row[key] == ''
                           for key in ('SKUCode', 'WhCode'))):
                return None
            pairs.append(row)
    skus = {_sql_key(item) for item in value['sku']}
    locations = {_sql_key(item) for item in value['location']}
    skus.update(_sql_key(row['SKUCode']) for row in pairs)
    locations.update(_sql_key(row['WhCode']) for row in pairs)
    return skus, locations, value['global']

def _graph_rows(tables):
    return tables['MasterDataRaw'] + tables['MasterDataRawNonNMS']

def _closure(skus, locations, *populations):
    sku_locations = {}
    location_skus = {}
    for tables in populations:
        for row in _graph_rows(tables):
            sku = _sql_key(row.get('SKUCode'))
            if sku is None:
                continue
            for field in ('WhCode', 'ParentWhCode'):
                location = _sql_key(row.get(field))
                if location is not None:
                    sku_locations.setdefault(sku, set()).add(location)
                    location_skus.setdefault(location, set()).add(sku)
    affected_skus, affected_locations = set(skus), set(locations)
    while True:
        before = (len(affected_skus), len(affected_locations))
        for sku in tuple(affected_skus):
            affected_locations.update(sku_locations.get(sku, ()))
        for location in tuple(affected_locations):
            affected_skus.update(location_skus.get(location, ()))
        if before == (len(affected_skus), len(affected_locations)):
            return affected_skus, affected_locations

def _scope(name, row, skus, locations):
    if name in SKU_TABLES:
        return _sql_key(row.get('SKUCode')) in skus
    if name in LOCATION_TABLES:
        return _sql_key(row.get('WHCode')) in locations
    raise ValueError('Unclassified canonical master table: ' + name)

def _canonical_raw(rows, business_date):
    result = []
    for source in rows:
        row = deepcopy(source)
        apply_raw_ansi_padding(row)
        normalize_master_row(row, business_date, trim=False)
        result.append(row)
    return _ordered(result)

def _prior_canonical_raw(rows):
    try:
        result = [deepcopy(row) for row in rows]
    except (TypeError, ValueError):
        return None
    if any(not isinstance(row, dict) or set(row) != set(RAW_COLUMNS)
           for row in result):
        return None
    return _ordered(result)

def _raw_partition_maps(rows):
    sku, location, global_rows = {}, {}, []
    for row in rows:
        structural = {name: value for name, value in row.items() if name != 'Norm'}
        sku_key = _sql_key(row.get('SKUCode'))
        location_key = _sql_key(row.get('WhCode'))
        if sku_key is not None:
            sku.setdefault(sku_key, []).append(structural)
        elif location_key is not None:
            location.setdefault(location_key, []).append(structural)
        else:
            global_rows.append(structural)

    def partition_digest(grouped):
        return {key: digest(_ordered(values)) for key, values in grouped.items()}

    return partition_digest(sku), partition_digest(location), digest(_ordered(global_rows))

def _changed_raw_scope(row, skus, locations):
    sku = _sql_key(row.get('SKUCode'))
    if sku is not None:
        return sku in skus
    location = _sql_key(row.get('WhCode'))
    return location is not None and location in locations

def _changed_partial_payload(payload, tables, canonical_raw, skus, locations):
    result = deepcopy(payload)
    result['prior'] = {name: [deepcopy(row) for row in tables[name]
                              if _scope(name, row, skus, locations)]
                       for name in PRIOR_TABLES}
    result['raw_master'] = [deepcopy(row) for row in canonical_raw
                            if _changed_raw_scope(row, skus, locations)]
    result['raw_non_nms'] = []
    result['raw_no_norm'] = []
    return result

def _changed_merge(base, partial, skus, locations):
    result = deepcopy(base)
    for name in TABLE_COLUMNS:
        in_scope = ((lambda row: _changed_raw_scope(row, skus, locations))
                    if name == 'MasterDataRaw'
                    else (lambda row, table=name: _scope(table, row, skus, locations)))
        retained = [row for row in result['tables'][name] if not in_scope(row)]
        replaced = [row for row in partial['tables'][name] if in_scope(row)]
        result['tables'][name] = _ordered(retained + replaced)
    result['outcome'] = 'APPLIED'
    result['rejects_added'] = _ordered(partial['rejects_added'])
    result['retired_events_added'] = _ordered(partial['retired_events_added'])
    return result

def _changed_response(result, *, mode, qualified, reason, producer_calls,
                      producer_rows, prior_rows, current_rows,
                      affected_skus=0, affected_locations=0):
    return {
        'result': result,
        'eligibility': {'qualified': qualified, 'mode': mode, 'reason': reason},
        'work': {
            'producer_calls': producer_calls,
            'producer_rows': producer_rows,
            'affected_skus': affected_skus,
            'affected_locations': affected_locations,
            'prior_rows': prior_rows,
            'current_rows': current_rows,
        },
    }

def _changed_full(payload, mode, reason, *, prior_rows, current_rows=None,
                  calls=1, rows=None, affected_skus=0, affected_locations=0):
    result = process_importer_master(payload)
    current_rows = len(payload['raw_master']) if current_rows is None else current_rows
    return _changed_response(
        result, mode=mode, qualified=False, reason=reason,
        producer_calls=calls,
        producer_rows=len(payload['raw_master']) if rows is None else rows,
        prior_rows=prior_rows, current_rows=current_rows,
        affected_skus=affected_skus, affected_locations=affected_locations,
    )

def prepare_changed(payload, prior_raw, changed):
    """Run one proved changed dependency component or the canonical full producer.

    ``prior_raw`` is the direct predecessor's canonical ``MasterDataRaw``
    reconstruction.  Current operational tables always come from
    ``payload['prior']``; no prior producer result is retained or copied here.
    This changed-only entry point deliberately has no zero-work path.
    """
    prior = _prior_canonical_raw(prior_raw)
    prior_count = 0 if prior is None else len(prior)
    claimed = _changes(changed)
    if claimed is None or not any((claimed[0], claimed[1], claimed[2])):
        return _changed_full(
            payload, 'FULL_UNQUALIFIED', 'changed-path-metadata-unqualified',
            prior_rows=prior_count,
        )

    typed = validate_master_input(payload)
    current_input = typed['MasterDataRaw']
    current = _canonical_raw(current_input, payload['business_date'])
    skus, locations, global_change = claimed

    if prior is None:
        return _changed_full(
            payload, 'FULL_UNQUALIFIED', 'prior-canonical-raw-unqualified',
            prior_rows=0, current_rows=len(current),
        )
    if global_change:
        return _changed_full(
            payload, 'FULL_GLOBAL', 'declared-global-master-change',
            prior_rows=len(prior), current_rows=len(current),
        )
    active = sum(row['Parameter'] == 'NMSActive' and row['Value'] == 1
                 for row in payload['settings'])
    inactive = sum(row['Parameter'] == 'NMSActive' and row['Value'] == 0
                   for row in payload['settings'])
    if active != 1 or inactive or not current:
        return _changed_full(
            payload, 'FULL_UNSTABLE', 'requires-active-nms-master-processing',
            prior_rows=len(prior), current_rows=len(current),
        )
    if payload['import_non_nms'] or typed['MasterDataRawNonNMS']:
        return _changed_full(
            payload, 'FULL_NON_NMS', 'non-nms-master-requires-global-producer',
            prior_rows=len(prior), current_rows=len(current),
        )
    if typed['NoNormMasterRaw']:
        return _changed_full(
            payload, 'FULL_NO_NORM', 'no-norm-master-requires-global-producer',
            prior_rows=len(prior), current_rows=len(current),
        )
    if any(row['SKUIntroDate'] is None for row in current_input):
        return _changed_full(
            payload, 'FULL_DATE', 'date-derived-sku-introduction-requires-global-producer',
            prior_rows=len(prior), current_rows=len(current),
        )

    previous_skus, previous_locations, previous_global = _raw_partition_maps(prior)
    current_skus, current_locations, current_global = _raw_partition_maps(current)
    actual_skus = {key for key in set(previous_skus) | set(current_skus)
                   if previous_skus.get(key) != current_skus.get(key)}
    actual_locations = {key for key in set(previous_locations) | set(current_locations)
                        if previous_locations.get(key) != current_locations.get(key)}

    previous_tables = {'MasterDataRaw': prior, 'MasterDataRawNonNMS': []}
    current_tables = {'MasterDataRaw': current, 'MasterDataRawNonNMS': []}
    affected_skus, affected_locations = _closure(
        skus, locations, previous_tables, current_tables,
    )
    if (previous_global != current_global
            or not actual_skus <= affected_skus
            or not actual_locations <= affected_locations):
        return _changed_full(
            payload, 'FULL_UNREPORTED', 'effective-change-outside-declared-closure',
            prior_rows=len(prior), current_rows=len(current),
            affected_skus=len(affected_skus),
            affected_locations=len(affected_locations),
        )

    all_skus = {_sql_key(row.get('SKUCode')) for row in prior + current
                if row.get('SKUCode') is not None}
    if affected_skus >= all_skus:
        return _changed_full(
            payload, 'FULL_CLOSURE', 'dependency-closure-is-full-catalogue',
            prior_rows=len(prior), current_rows=len(current),
            affected_skus=len(affected_skus),
            affected_locations=len(affected_locations),
        )

    partial_payload = _changed_partial_payload(
        payload, typed, current, affected_skus, affected_locations,
    )
    if not partial_payload['raw_master']:
        return _changed_full(
            payload, 'FULL_EMPTY_CLOSURE', 'retirement-closure-needs-global-producer',
            prior_rows=len(prior), current_rows=len(current),
            affected_skus=len(affected_skus),
            affected_locations=len(affected_locations),
        )

    partial = process_importer_master(partial_payload)
    if partial['outcome'] != 'APPLIED':
        return _changed_full(
            payload, 'FULL_EARLY_RETURN',
            'partial-canonical-producer-triggered-global-outcome',
            prior_rows=len(prior), current_rows=len(current), calls=2,
            rows=len(partial_payload['raw_master']) + len(payload['raw_master']),
            affected_skus=len(affected_skus),
            affected_locations=len(affected_locations),
        )

    base_tables = {name: _ordered(typed[name]) for name in TABLE_COLUMNS}
    base_tables['MasterDataRaw'] = current
    base = {'outcome': 'APPLIED', 'tables': base_tables,
            'rejects_added': [], 'retired_events_added': []}
    result = _changed_merge(base, partial, affected_skus, affected_locations)
    return _changed_response(
        result, mode='SCOPED', qualified=True,
        reason='complete-sql-key-dependency-component', producer_calls=1,
        producer_rows=len(partial_payload['raw_master']),
        prior_rows=len(prior), current_rows=len(current),
        affected_skus=len(affected_skus),
        affected_locations=len(affected_locations),
    )
