"""Selected DBM ingestion preceding suspension/rule evaluation.

Canonical table-shaped rows are used at this boundary to keep state columns
explicit. This module performs no I/O and does not select a rule from a fixture.
Source/ownership contract: docs/block3/R2_INGESTION_CONTRACT.md.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend
presentation and behavior. No frontend redesign, substitute screens, refactoring
or MTO changes. Any future exception requires explicit human authorization.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from itertools import chain, groupby
from mta.domain.ordinal_lookup import OrdinalLookup
from mta.domain.sql_identity_keys import row_join_key, value_join_key
from mta.row_sequences import history_rows


def _day(value):
    if value is None:
        return None
    if type(value) is date:
        return value
    return date.fromisoformat(value)


def _key(row):
    return row_join_key(row)


def import_daily_observations(today, previous, raw, masters, bpr_daily,
                              distributor_transactions, vendor_transactions):
    """Replace current-date observations; preserve other history and SQL bags."""
    today = _day(today)
    excluded = {
        value_join_key(row['WhCode'])
        for row in (*distributor_transactions, *vendor_transactions)
        if _day(row['ReportDate']) == today and row['TransactedItemCount'] == 0
    }
    master_counts = {}
    for row in masters:
        master_counts[_key(row)] = master_counts.get(_key(row), 0) + 1
    blues = {}
    for row in bpr_daily:
        if _day(row['ReportDate']) == today:
            key = _key(row)
            if key in blues and blues[key] != row['BlueZone']:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting BPR BlueZone rows')
            blues[key] = row['BlueZone']
    retained = (deepcopy(row) for row in previous if _day(row['ReportDate']) != today)
    current = []
    for row in raw:
        key = _key(row)
        if _day(row['ReportDate']) != today or value_join_key(row['WhCode']) in excluded:
            continue
        for _ in range(master_counts.get(key, 0)):
            current.append({
                'SKUCode': row['SKUCode'], 'WhCode': row['WhCode'],
                **{field: row[field] for field in ('Stock', 'Consumption', 'GIT', 'Receipts')},
                'BlueZone': blues.get(key, 0), 'ReportDate': row['ReportDate'],
            })
    from mta.application.native_output_contracts import validate_produced_rows
    validate_produced_rows(current,'DBM/DailyConsumption',stage='dbm/ingestion-daily')
    return history_rows(chain(retained, current), like=previous)


def import_exclusions(exclusions, masters):
    return [dict(SKUCode=row['SKUCode'], WHCode=row['WhCode'],
                 IsRedEnabled=False, IsGreenEnabled=False)
            for row in exclusions for master in masters if _key(row) == _key(master)]


def import_orders(today, previous, raw):
    today = _day(today)
    current=[
        {field: row[field] for field in
         ('OrderID', 'SKUCode', 'WhCode', 'OrderQuantity', 'OrderDate', 'ImportDate')}
        for row in raw if _day(row['ImportDate']) == today
    ]
    from mta.application.native_output_contracts import validate_produced_rows
    validate_produced_rows(current,'DBM/OrderData',stage='dbm/ingestion-orders')
    return [deepcopy(row) for row in previous if _day(row['ImportDate']) != today] + current


def calculate_extended_ocp(today, attributes, masters, daily):
    """Match SQL observation groups, inclusive lower bound, and NULL OCP."""
    today = _day(today)
    result = deepcopy(attributes)
    with OrdinalLookup(masters) as master_index, OrdinalLookup(daily) as daily_index:
        for attr in result:
            matching = [row for row in master_index.matching(masters, _key(attr)) if _key(row) == _key(attr)]
            if not matching:
                continue
            if len(matching) != 1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: duplicate DBMMaster for ExtendedOCP')
            master = matching[0]
            ocp, rlt = master['OCP'], master['RLT']
            attr['ExtendedOCP'] = ocp
            if ocp is None:
                continue
            observations = sorted(
                (row for row in daily_index.matching(daily, _key(master)) if _key(row) == _key(master)
                 and _day(row['ReportDate']) >= today - timedelta(days=ocp)),
                key=lambda row: _day(row['ReportDate']),
            )
            for _, group in groupby(observations, key=lambda row: _day(row['ReportDate'])):
                # ROW_NUMBER orders only by date in both windows. Never manufacture
                # a deterministic order for differently classified tied observations.
                if len({row['Stock'] == 0 for row in group}) > 1:
                    raise ValueError('SOURCE_ORDER_AMBIGUITY: tied zero/nonzero observations')
            current = longest = 0
            for row in observations:
                current = current + 1 if row['Stock'] == 0 else 0
                longest = max(longest, current)
            if longest > rlt:
                attr['ExtendedOCP'] = ocp + longest - rlt
    return result


def ingest_dbm(today, state, facts):
    """Return independently derived closing tables without mutating openings.

    The caller must load its own persisted state. `facts['bpr_daily']` is the
    current upstream producer output, not a replacement for running BPR in the
    connected engine. Unknown state families are retained untouched.
    """
    result = deepcopy(state)
    result['DailyConsumption'] = import_daily_observations(
        today, state['DailyConsumption'], facts['daily_raw'], state['DBMMaster'],
        facts['bpr_daily'], facts['distributor_transactions'], facts['vendor_transactions'],
    )
    result['SuspendCustomSKUTbl'] = import_exclusions(facts['exclusions'], state['DBMMaster'])
    result['OrderData'] = import_orders(today, state['OrderData'], facts['order_raw'])
    result['SKULocStandardAttributes'] = calculate_extended_ocp(
        today, state['SKULocStandardAttributes'], state['DBMMaster'], result['DailyConsumption'],
    )
    return result
