"""Differential capture join proof against retained pre-index functions; no DB."""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vectorflow.settings")
os.environ.setdefault("VF_SECRET_KEY", "indexed-capture-unit-only")
import django
django.setup()

# Exact functions captured before the indexed edit; the external copy and hashes
# are retained in D:/freshvcf-build/evidence/indexed-mdm-capture-20261020.
_RETAINED_DAILY = r'''
def _unique(rows, keys, label):
    matches = [row for row in rows if all(sql_key(row.get(k)) == sql_key(v)
                                         for k, v in keys.items())]
    clean = [{k: v for k, v in row.items() if k != 'id'} for row in matches]
    if clean and any(row != clean[0] for row in clean[1:]):
        raise ValueError('canonical %s UPDATE has incomparable duplicate source values' % label)
    return clean[0] if clean else None

def compose(snapshot, master_rows, *, last_run_date, master_columns=RAW_COLUMNS):
    """Apply the qualified MasterDataRaw statements in their native order."""
    result = deepcopy(list(master_rows))
    if snapshot['schema'] != SCHEMA or digest({k: v for k, v in snapshot.items()
            if k != 'revision_digest'}) != snapshot['revision_digest']:
        raise ValueError('MDM daily input revision drift')
    if not snapshot['nms_active']:
        return result
    if tuple(master_columns) != tuple(RAW_COLUMNS) or any(set(row) != set(master_columns) for row in result):
        raise ValueError('composed MDM input requires complete MasterDataRaw columns')
    rows = snapshot['rows']; blank = lambda: dict.fromkeys(master_columns)
    pair = lambda row, wh='WhCode': (sql_key(row.get('SKUCode')), sql_key(row.get(wh)))

    # NMSNewItems is staged and anti-joined before any standalone additions.
    existing = {pair(row) for row in result}
    pair_adds = [row for row in rows['skuloc']['additions']
                 if row['Approved'] and pair(row) not in existing]
    for staged in pair_adds:
        row = blank()
        for name in ('SKUCode', 'WhCode', 'Norm', 'MinNorm', 'RLT', 'RCP', 'GCP',
                     'OCP', 'ParentWhCode', 'PackSize', 'SpikeThreshold', 'PSOThreshold',
                     'FGRMFlag', 'NormPercentReservation', 'MinOrderCount'):
            row[name] = staged[name]
        row['SKUIntroDate'] = last_run_date
        row['StockPercentForRationing'] = staged['StockPercentForRat']
        result.append(row)

    sku_codes = {sql_key(row.get('SKUCode')) for row in result}
    additions = []
    for staged in rows['sku']['descriptions']:
        if sql_key(staged['SKUCode']) not in sku_codes:
            row = {**blank(), 'SKUCode': staged['SKUCode'],
                   'SKUDescription': staged['SKUDescription']}
            if row not in additions: additions.append(row)  # SELECT DISTINCT
    result.extend(additions)
    location_codes = {sql_key(row.get('WhCode')) for row in result}
    additions = []
    for staged in rows['location']['descriptions']:
        if sql_key(staged['WHCode']) not in location_codes:
            row = {**blank(), 'WhCode': staged['WHCode'],
                   'WHDescription': staged['WHDescription']}
            additions.append(row)  # Native SiteDescription insert has no DISTINCT.
    result.extend(additions)

    sku_codes = {sql_key(row.get('SKUCode')) for row in result}
    additions = []
    for staged in rows['sku']['approved']:
        if staged['Approved'] and staged['ActionType'] == 1 and sql_key(staged['SKUCode']) not in sku_codes:
            row = {**blank(), **{k: staged[k] for k in ('SKUCode', 'SKUDescription',
                'ElephantOrderCapping', 'Weight', 'Volume', *('SL%d' % i for i in range(1, 6)))}}
            if row not in additions: additions.append(row)  # SELECT DISTINCT
    result.extend(additions)
    location_codes = {sql_key(row.get('WhCode')) for row in result}
    for staged in rows['location']['approved']:  # native statement has no DISTINCT
        if staged['Approved'] and staged['ActionType'] == 1 and sql_key(staged['WHCode']) not in location_codes:
            result.append({**blank(), 'WhCode': staged['WHCode'], **{k: staged[k] for k in
                ('WHDescription', 'LocationType', 'LogisticsLocation',
                 *('LL%d' % i for i in range(1, 6)))}})

    removed_locations = {sql_key(r['WHCode']) for r in rows['location']['approved']
                         if r['Approved'] and r['ActionType'] == 0 and r['WHCode'] is not None}
    result = [r for r in result if r.get('WhCode') is None or sql_key(r['WhCode']) not in removed_locations]
    removed_skus = {sql_key(r['SKUCode']) for r in rows['sku']['approved']
                    if r['Approved'] and r['ActionType'] == 0 and r['SKUCode'] is not None}
    result = [r for r in result if r.get('SKUCode') is None or sql_key(r['SKUCode']) not in removed_skus]
    removed_pairs = {pair(r) for r in rows['skuloc']['removals'] if r['Approved']
                     and r['SKUCode'] is not None and r['WhCode'] is not None}
    result = [r for r in result if pair(r) not in removed_pairs]

    sku_overlay = [r for r in rows['sku']['approved'] if r['Approved'] and r['ActionType'] == 1]
    for row in result:
        if row.get('SKUCode') is None: continue
        key = {'SKUCode': row['SKUCode']}
        attr = _unique(rows['sku']['attributes'], key, 'SKU')
        desc = _unique(rows['sku']['descriptions'], key, 'SKU')
        approved = _unique(sku_overlay, key, 'SKU')
        for name in SKU_FIELDS:
            target = 'SKUAtt' + name[1:].zfill(2) if name.startswith('c') else name
            if approved is not None: row[target] = approved[name]
            elif name == 'SKUDescription': row[target] = desc[name] if desc is not None else None
            elif attr is not None: row[target] = attr[name]
            elif name.startswith('c'): row[target] = None

    location_overlay = [r for r in rows['location']['approved'] if r['Approved'] and r['ActionType'] == 1]
    location_master = {sql_key(r['WHCode']) for r in
                       (*rows['location']['descriptions'], *rows['location']['approved'])}
    for row in result:
        if row.get('WhCode') is None or sql_key(row['WhCode']) not in location_master: continue
        key = {'WHCode': row['WhCode']}
        attr = _unique(rows['location']['attributes'], key, 'Location')
        desc = _unique(rows['location']['descriptions'], key, 'Location')
        approved = _unique(location_overlay, key, 'Location')
        for name in LOCATION_FIELDS:
            target = 'LocAtt' + name[1:].zfill(2) if name.startswith('c') else name
            if approved is not None: row[target] = approved[name]
            elif name == 'WHDescription': row[target] = desc[name] if desc is not None else None
            elif attr is not None: row[target] = attr[name]

    pair_modify = [r for r in rows['skuloc']['modifications'] if r['Approved']]
    core = ('ParentWhCode', 'MinNorm', 'RLT', 'RCP', 'GCP', 'OCP', 'MinOrderCount')
    pair_core = {}
    for row in result:
        current_pair = pair(row)
        if None in current_pair: continue
        values = tuple(row.get(name) for name in core)
        if current_pair in pair_core and pair_core[current_pair] != values:
            raise ValueError('canonical SKULocMaster DISTINCT join is incomparable')
        pair_core[current_pair] = values
    for row in result:
        if None in pair(row): continue
        keys = {'SKUCode': row['SKUCode'], 'LocCode': row['WhCode']}
        attr = _unique(rows['skuloc']['attributes'], keys, 'SKU-location')
        added = _unique(pair_adds, {'SKUCode': row['SKUCode'], 'WhCode': row['WhCode']}, 'SKU-location')
        modified = _unique(pair_modify, {'SKUCode': row['SKUCode'], 'WhCode': row['WhCode']}, 'SKU-location')
        if attr is not None:
            for name in ('PackSize', 'SpikeThreshold', 'PSOThreshold', 'FGRMFlag',
                         'StockPercentForRationing', 'NormPercentReservation'):
                row[name] = attr[name]
            for i in range(1, 16): row['SKULocAtt%02d' % i] = attr['c%d' % i]
        if added is not None:
            for name in ('PackSize', 'SpikeThreshold', 'PSOThreshold', 'FGRMFlag',
                         'NormPercentReservation', *('SKULocAtt%02d' % i for i in range(1, 16))):
                row[name] = added[name]
            row['StockPercentForRationing'] = added['StockPercentForRat']
        if modified is not None:
            for name in ('ParentWhCode', 'MinNorm', 'RLT', 'RCP', 'GCP', 'PackSize',
                         'FGRMFlag', 'NormPercentReservation', 'MinOrderCount', 'OCP',
                         *('SKULocAtt%02d' % i for i in range(1, 16))):
                if modified[name] is not None: row[name] = modified[name]
            row['SpikeThreshold'] = modified['SpikeThreshold']
            row['PSOThreshold'] = modified['PSOThreshold']
            if modified['StockPercentForRat'] is not None:
                row['StockPercentForRationing'] = modified['StockPercentForRat']
    # The pinned script normalizes location descriptions before rebuilding the
    # parent description after pair modifications.  Its final LEFT JOIN writes
    # ND for both NULL and unknown parents.
    for row in result:
        if row.get('WHDescription') is None:
            row['WHDescription'] = 'ND'
        parent = row.get('ParentWhCode')
        parent_row = None
        if parent is not None and sql_key(parent) in location_master:
            key = {'WHCode': parent}
            description = _unique(rows['location']['descriptions'], key, 'Location')
            approved = _unique(location_overlay, key, 'Location')
            parent_row = approved if approved is not None else description
        row['ParentDescription'] = (parent_row['WHDescription']
                                    if parent_row is not None and parent_row.get('WHDescription') is not None
                                    else 'ND')
    return result
'''

_RETAINED_SUPPLIER = r'''
def location_master(location_rows):
    """NMSImportData LocationMaster FULL JOIN plus approved description UPDATE."""
    descriptions = location_rows['descriptions']; approved = location_rows['approved']
    equal = lambda a, b: a is not None and b is not None and sql_key(a) == sql_key(b)
    rows = []
    for left in descriptions:
        matches = [r for r in approved if equal(left['WHCode'], r['WHCode'])] or [None]
        for right in matches:
            rows.append(dict(WHCode=left['WHCode'], WHDescription=left['WHDescription']
                if left['WHDescription'] is not None else right['WHDescription'] if right else None))
    rows.extend(dict(WHCode=r['WHCode'], WHDescription=r['WHDescription']) for r in approved
                if not any(equal(r['WHCode'], left['WHCode']) for left in descriptions))
    for row in rows:
        values = [r['WHDescription'] for r in approved if r['Approved'] and r['ActionType'] == 1
                  and equal(row['WHCode'], r['WHCode'])]
        if values:
            if any(value != values[0] for value in values[1:]):
                raise ValueError('SOURCE_ORDER_AMBIGUITY: supplier LocationMaster UPDATE')
            row['WHDescription'] = values[0]
    return rows
'''

_RETAINED_SUPPLIER_INPUT = r'''
def compose_supplier_inputs(raw, queues, *, moq_format, locations):
    """Delete-before-insert; preserve every occurrence and native marker value."""
    if moq_format not in FORMATS:
        raise ValueError('Explicit canonical NMSMOQInputDataFormat required')
    if any(name not in raw for name in RAW) or any(name not in queues for name in QUEUES):
        raise ValueError('Explicit supplier raw and approval populations required')
    result = deepcopy(raw)
    selected = [('SOBDataRaw', 'NMSSOB', 'SOB', True),
                ('MOQDataRaw2', 'NMSMOQWithDestination', 'MOQ', True)
                if moq_format == 'WithDestLoc' else
                ('MOQDataRaw1', 'NMSMOQWithoutDestination', 'MOQ', False)]
    descriptions = {}
    for row in locations:
        key = _key(row['WHCode'])
        if key is not None:
            descriptions.setdefault(key, []).append(row['WHDescription'])
    for raw_name, queue_name, scalar, destination in selected:
        eligible = [row for row in queues[queue_name] if row['Approved'] == 1]
        deleted = {_identity(row, destination, queue=True) for row in eligible}
        deleted.discard(None)  # SQL NULL does not join to NULL.
        rows = [row for row in result[raw_name] if _identity(row, destination) not in deleted]
        for row in eligible:
            # Authorized correction: a destination MOQ modification replaces
            # the matching raw value; it must not silently delete the MOQ.
            if row['ActionType'] != 1 and not (
                    queue_name == 'NMSMOQWithDestination' and row['ActionType'] == 2):
                continue
            item = {'SKUCode': row['SKUCode'], 'SupplierCode': row['SupplierCode'],
                    'SupplierDescription': 'ND', scalar: row[scalar]}
            if destination:
                item['WHCode'] = row['WhCode']
            rows.append(item)
        for row in rows:
            matches = descriptions.get(_key(row['SupplierCode']), [None])
            values = ['ND' if value is None else value for value in matches]
            if any(value != values[0] for value in values[1:]):
                raise ValueError('SOURCE_ORDER_AMBIGUITY: supplier description UPDATE')
            row['SupplierDescription'] = values[0]
        result[raw_name] = rows
    return result
'''

from copy import deepcopy
from decimal import Decimal
import random
import unittest
from unittest.mock import patch

from mta.mdm import daily_input, supplier_capture, supplier_input
from mta.serialization import digest
from tests import test_mdm_daily_input as fixtures

_REFERENCE_DAILY = dict(vars(daily_input))
exec(compile(_RETAINED_DAILY, '<retained-daily-input>', 'exec'), _REFERENCE_DAILY)
_REFERENCE_SUPPLIER = dict(vars(supplier_capture))
exec(compile(_RETAINED_SUPPLIER, '<retained-supplier-capture>', 'exec'), _REFERENCE_SUPPLIER)
_REFERENCE_SUPPLIER_INPUT = dict(vars(supplier_input))
exec(compile(_RETAINED_SUPPLIER_INPUT, '<retained-supplier-input>', 'exec'), _REFERENCE_SUPPLIER_INPUT)


def outcome(fn, *args, **kwargs):
    try:
        return ('result', fn(*args, **kwargs))
    except Exception as error:
        return ('error', type(error).__name__, str(error))


def reseal(snapshot):
    snapshot['revision_digest'] = digest({k: v for k, v in snapshot.items() if k != 'revision_digest'})
    return snapshot


def populated(size=1):
    snapshot = fixtures.snapshot()
    master = []
    for i in range(size):
        sku, loc = 'S%d' % i, 'L%d' % i
        master.append(fixtures.blank(SKUCode=sku, WhCode=loc, ParentWhCode='P',
                                     Norm=i+10, MinNorm=1, RLT=3, RCP=3, GCP=3))
        sa = fixtures.approved_sku(sku, 1)
        la = fixtures.approved_location(loc, 1)
        for item in (sa, la):
            for name in ('ActionType', 'Approved', 'Reverted'):
                item.pop(name)
        sa.pop('SKUDescription'); la.pop('WHDescription')
        sa.update(id=i+1, Weight='1.25', c15='sku-final')
        la.update(id=i+1, LocationType='Warehouse', c15='location-final')
        snapshot['rows']['sku']['attributes'].append(sa)
        snapshot['rows']['sku']['descriptions'].append(dict(SKUCode=sku, SKUDescription='product'+str(i)))
        snapshot['rows']['location']['attributes'].append(la)
        snapshot['rows']['location']['descriptions'].append(dict(WHCode=loc, WHDescription='location'+str(i)))
        pair = dict.fromkeys(daily_input.PAIR_ATTRIBUTES)
        pair.update(id=i+1, SKUCode=sku, LocCode=loc, PackSize=2,
                    StockPercentForRationing=75, NormPercentReservation=5, c15='pair-final')
        snapshot['rows']['skuloc']['attributes'].append(pair)
    return reseal(snapshot), master


class IndexedMdmCaptureTests(unittest.TestCase):
    def compare_compose(self, snapshot, master):
        before = deepcopy((snapshot, master))
        args = dict(last_run_date='2026-10-19')
        expected = outcome(_REFERENCE_DAILY['compose'], snapshot, master, **args)
        actual = outcome(daily_input.compose, snapshot, master, **args)
        self.assertEqual(actual, expected)
        self.assertEqual((snapshot, master), before)
        return actual

    def test_unique_null_normalization_duplicate_identity_and_lazy_ambiguity(self):
        rows = [dict(id=1, SKUCode='S', value=None, revision=1),
                dict(id=2, SKUCode='S', value=None, revision=1),
                dict(id=3, SKUCode=None, value=9),
                dict(id=4, SKUCode='UNUSED', value=1),
                dict(id=5, SKUCode='UNUSED', value=2)]
        indexed = daily_input._UniqueRows(rows, ('SKUCode',))
        for key in ('S', 's ', None, 'missing', 'UNUSED'):
            self.assertEqual(outcome(daily_input._unique, indexed, dict(SKUCode=key), 'SKU'),
                             outcome(_REFERENCE_DAILY['_unique'], rows, dict(SKUCode=key), 'SKU'))
        for changed in ('revision', 'SKUCode', 'value'):
            values = [dict(id=1, SKUCode='S', value=1, revision=1)] * 2
            values[1] = dict(values[1], **{changed: 's ' if changed == 'SKUCode' else 2})
            self.assertEqual(outcome(daily_input._unique, daily_input._UniqueRows(values, ('SKUCode',)), dict(SKUCode='s '), 'SKU'),
                             outcome(_REFERENCE_DAILY['_unique'], values, dict(SKUCode='s '), 'SKU'))

    def test_compose_all_fields_duplicates_null_and_unused_ambiguity(self):
        snapshot, master = populated(3)
        for family in ('sku', 'location', 'skuloc'):
            rows = snapshot['rows'][family]['attributes']
            rows.append(dict(rows[0], id=999))
            extra = dict(rows[0], id=1000, SKUCode='UNUSED') if family != 'location' else dict(rows[0], id=1000, WHCode='UNUSED')
            rows.extend([extra, dict(extra, id=1001, c15='different')])
        master.extend([deepcopy(master[0]), fixtures.blank(SKUCode=None, WhCode=None)])
        result = self.compare_compose(reseal(snapshot), master)
        self.assertEqual(result[0], 'result')
        self.assertEqual(result[1][0]['SKUAtt15'], 'sku-final')
        self.assertEqual(result[1][0]['LocAtt15'], 'location-final')
        self.assertEqual(result[1][0]['SKULocAtt15'], 'pair-final')
        for family in ('sku', 'location', 'skuloc'):
            changed = deepcopy(snapshot)
            changed['rows'][family]['attributes'].append(dict(changed['rows'][family]['attributes'][0], c15='conflict'))
            self.assertEqual(self.compare_compose(reseal(changed), master)[0], 'error')

    def test_unique_cache_retains_only_validated_source_references(self):
        source = dict(id=1, SKUCode='S', value=None, revision=7)
        unused = [dict(SKUCode='UNUSED', value=1), dict(SKUCode='UNUSED', value=2)]
        indexed = daily_input._UniqueRows([source, dict(source, id=2), *unused], ('SKUCode',))
        self.assertEqual(indexed.resolved, {})
        first = daily_input._unique(indexed, dict(SKUCode='s '), 'SKU')
        second = daily_input._unique(indexed, dict(SKUCode='S'), 'SKU')
        self.assertEqual(first, dict(SKUCode='S', value=None, revision=7))
        self.assertEqual(second, first)
        self.assertIsNot(first, second)
        self.assertIs(indexed.resolved[('s',)], source)
        first['value'] = 'consumer-only'
        self.assertEqual(daily_input._unique(indexed, dict(SKUCode='S'), 'SKU'), second)
        self.assertIsNone(daily_input._unique(indexed, dict(SKUCode='missing'), 'SKU'))
        self.assertIsNone(indexed.resolved[('missing',)])
        self.assertNotIn(('unused',), indexed.resolved)
        with self.assertRaisesRegex(ValueError, 'incomparable duplicate source values'):
            daily_input._unique(indexed, dict(SKUCode='UNUSED'), 'SKU')
        self.assertNotIn(('unused',), indexed.resolved)

    def test_compose_stage_order_and_randomized_complete_results_or_errors(self):
        rng = random.Random(3005)
        for iteration in range(120):
            snapshot, master = populated(3)
            for row in master:
                if rng.randrange(2):
                    row['SKUCode'] = row['SKUCode'].lower() + ' '
                if rng.randrange(2):
                    row['WhCode'] = row['WhCode'].lower() + ' '
                row['ParentWhCode'] = rng.choice(['L0', 'l1 ', 'missing', None])
            if iteration % 4 == 0:
                master.append(fixtures.blank(SKUCode=None, WhCode='L0'))
            snapshot['rows']['sku']['approved'] = [fixtures.approved_sku(rng.choice(['S0', 'NEW']), rng.randrange(2))]
            snapshot['rows']['location']['approved'] = [fixtures.approved_location(rng.choice(['L0', 'NEW']), rng.randrange(2))]
            snapshot['rows']['skuloc']['additions'] = [fixtures.pair_add(rng.choice(['S0', 'NEW']), rng.choice(['L0', 'NEW']))]
            if iteration % 3 == 0:
                modified = fixtures.pair_add('S1', 'L1')
                modified.update(ParentWhCode='l0 ', SpikeThreshold=None, PSOThreshold=None)
                snapshot['rows']['skuloc']['modifications'] = [modified]
            if iteration % 5 == 0:
                snapshot['rows']['skuloc']['removals'] = [dict(SKUCode='S2', WhCode='L2', Approved=True)]
            if iteration % 7 == 0:
                snapshot['rows']['sku']['attributes'].append(dict(snapshot['rows']['sku']['attributes'][0], revision=2))
            self.compare_compose(reseal(snapshot), master)

    def test_location_full_join_fanout_order_null_and_update_ambiguity(self):
        rng = random.Random(3305)
        for _ in range(250):
            locations = dict(descriptions=[dict(WHCode=rng.choice(['L','l ',None,'OTHER']), WHDescription=rng.choice(['first',None])) for _ in range(rng.randrange(8))],
                approved=[dict(WHCode=rng.choice(['L','l ',None,'OTHER']), WHDescription=rng.choice(['first','second',None]), Approved=bool(rng.randrange(2)), ActionType=rng.randrange(2)) for _ in range(rng.randrange(8))])
            before = deepcopy(locations)
            self.assertEqual(outcome(supplier_capture.location_master, locations),
                             outcome(_REFERENCE_SUPPLIER['location_master'], locations))
            self.assertEqual(locations, before)
        locations = dict(descriptions=[dict(WHCode='L', WHDescription=None)] * 2,
                         approved=[dict(WHCode='L', WHDescription='first', Approved=False, ActionType=1)] * 3)
        actual = supplier_capture.location_master(locations)
        self.assertEqual(actual, [dict(WHCode='L', WHDescription='first')] * 6)

    def test_compose_lookup_work_scales_linearly(self):
        totals = []
        slow_totals = []
        for size in (32, 64):
            snapshot, master = populated(size)
            with patch.object(daily_input, 'sql_key', wraps=daily_input.sql_key) as calls:
                actual = daily_input.compose(snapshot, master, last_run_date='2026-10-19')
                totals.append(calls.call_count)
            original = _REFERENCE_DAILY['sql_key']
            with patch.dict(_REFERENCE_DAILY, sql_key=original):
                with patch.object(daily_input, 'sql_key', wraps=original) as calls:
                    _REFERENCE_DAILY['sql_key'] = calls
                    expected = _REFERENCE_DAILY['compose'](snapshot, master, last_run_date='2026-10-19')
                    slow_totals.append(calls.call_count)
            self.assertEqual(actual, expected)
        self.assertLess(totals[1], totals[0] * 2.2)
        self.assertGreater(slow_totals[1], slow_totals[0] * 3.5)
        self.assertLess(totals[1], slow_totals[1] // 8)

    def test_supplier_lookup_work_scales_linearly(self):
        counts = []
        for size in (64, 128):
            locations = dict(descriptions=[dict(WHCode='L'+str(i), WHDescription=None) for i in range(size)],
                approved=[dict(WHCode='l'+str(i)+' ', WHDescription=str(i), Approved=True, ActionType=1) for i in range(size)])
            with patch.object(supplier_capture, 'sql_key', wraps=supplier_capture.sql_key) as calls:
                actual = supplier_capture.location_master(locations)
                counts.append(calls.call_count)
            self.assertEqual(actual, _REFERENCE_SUPPLIER['location_master'](locations))
        self.assertEqual(counts[1], counts[0] * 2)

    def test_distinct_projection_preserves_exact_numeric_null_order_and_fallback(self):
        fields = ('SKUCode', 'quantity', 'description')
        rows = [dict(SKUCode=None, quantity=value, description=None)
                for value in (1, True, Decimal('1'), 1.0, 0, -0.0, None)]
        rows.extend(dict(SKUCode=code, quantity=3, description=None)
                    for code in ('S', 's', 'S ', 'S'))
        rows.extend(dict(SKUCode='nested', quantity=value, description=None)
                    for value in ([1], [1], (1,), {'x': 1}, {'x': 1}, {1}, frozenset({1})))
        for population in (rows, list(reversed(rows))):
            expected = []
            actual = daily_input._DistinctRows(fields)
            for row in population:
                if row not in expected:
                    expected.append(row)
                actual.append(row)
            self.assertEqual(actual.rows, expected)
            self.assertTrue(all(left is right for left, right in zip(actual.rows, expected)))

    def test_distinct_projection_retains_original_comparison_error(self):
        rows = [dict(value=Decimal('1')), dict(value=Decimal('sNaN'))]
        def original():
            result = []
            for row in rows:
                if row not in result:
                    result.append(row)
            return result
        def indexed():
            result = daily_input._DistinctRows(('value',))
            for row in rows:
                result.append(row)
            return result.rows
        self.assertEqual(outcome(indexed), outcome(original))

    def test_compose_many_distinct_description_and_approved_rows_matches_retained_source(self):
        for kind in ('descriptions', 'approved'):
            snapshot = fixtures.snapshot()
            for i in range(96):
                row = (dict(SKUCode='S'+str(i), SKUDescription='product'+str(i))
                       if kind == 'descriptions' else fixtures.approved_sku('S'+str(i), 1))
                snapshot['rows']['sku'][kind].extend([row, dict(row), dict(row)])
            result = self.compare_compose(reseal(snapshot), [])
            self.assertEqual(result[0], 'result')
            self.assertEqual([r['SKUCode'] for r in result[1]], ['S'+str(i) for i in range(96)])

    def test_distinct_projection_comparison_work_scales_linearly_with_duplicates(self):
        class CountedText(str):
            comparisons = 0
            def __eq__(self, other):
                type(self).comparisons += 1
                return super().__eq__(other)
            __hash__ = str.__hash__

        fast_counts, slow_counts = [], []
        for size in (64, 128):
            rows = [dict(SKUCode=CountedText('S'+str(i)), quantity=None) for i in range(size)]
            rows.extend(dict(SKUCode=CountedText('S'+str(i)), quantity=None) for i in range(size))
            CountedText.comparisons = 0
            expected = []
            for row in rows:
                if row not in expected:
                    expected.append(row)
            slow_counts.append(CountedText.comparisons)
            CountedText.comparisons = 0
            actual = daily_input._DistinctRows(('SKUCode', 'quantity'))
            for row in rows:
                actual.append(row)
            fast_counts.append(CountedText.comparisons)
            self.assertEqual(actual.rows, expected)
        self.assertLessEqual(fast_counts[1], fast_counts[0] * 2.2)
        self.assertGreater(slow_counts[1], slow_counts[0] * 3.8)
        self.assertLess(fast_counts[1], slow_counts[1] // 20)

    def test_supplier_description_cache_complete_differential_results_and_errors(self):
        rng = random.Random(5305)
        for _ in range(180):
            raw = {}
            for name in supplier_input.RAW:
                scalar = 'SOB' if name == 'SOBDataRaw' else 'MOQ'
                raw[name] = [dict(SKUCode=rng.choice(['S','s ',None]), SupplierCode=rng.choice(['V','v ',None,'OTHER']),
                                  SupplierDescription='opening', **{scalar: rng.choice([0, 5, 15])},
                                  **({'WHCode': rng.choice(['L',None])} if name != 'MOQDataRaw1' else {}))
                             for _ in range(rng.randrange(6))]
            queues = {name: [dict(SKUCode='S', WhCode='L', SupplierCode=rng.choice(['V','v ',None]),
                                 SOB=25, MOQ=10, Approved=rng.randrange(2), Reverted=False, ActionType=rng.randrange(4))
                             for _ in range(rng.randrange(4))] for name in supplier_input.QUEUES}
            locations = [dict(WHCode=rng.choice(['V','v ',None,'UNUSED']), WHDescription=rng.choice([None,'ND','vendor','different']))
                         for _ in range(rng.randrange(8))]
            before = deepcopy((raw, queues, locations))
            kwargs = dict(moq_format=rng.choice(supplier_input.FORMATS), locations=locations)
            self.assertEqual(outcome(supplier_input.compose_supplier_inputs, raw, queues, **kwargs),
                             outcome(_REFERENCE_SUPPLIER_INPUT['compose_supplier_inputs'], raw, queues, **kwargs))
            self.assertEqual((raw, queues, locations), before)

    def test_supplier_description_unused_conflicts_null_nd_and_full_multiplicity(self):
        raw = dict(SOBDataRaw=[dict(SKUCode='S', WHCode='L', SupplierCode=code, SupplierDescription='old', SOB=1)
                               for code in ('V', 'v ', None, 'MISSING', 'V')], MOQDataRaw1=[], MOQDataRaw2=[])
        queues = dict.fromkeys(supplier_input.QUEUES, [])
        locations = [dict(WHCode='v ', WHDescription=None), dict(WHCode='V', WHDescription='ND'),
                     dict(WHCode=None, WHDescription='not joined'), dict(WHCode='UNUSED', WHDescription='first'),
                     dict(WHCode='UNUSED', WHDescription='conflict')]
        args = dict(moq_format='WithDestLoc', locations=locations)
        actual = supplier_input.compose_supplier_inputs(raw, queues, **args)
        self.assertEqual(actual, _REFERENCE_SUPPLIER_INPUT['compose_supplier_inputs'](raw, queues, **args))
        self.assertEqual([r['SupplierCode'] for r in actual['SOBDataRaw']], ['V', 'v ', None, 'MISSING', 'V'])
        self.assertEqual([r['SupplierDescription'] for r in actual['SOBDataRaw']], ['ND'] * 5)

    def test_supplier_description_comparison_work_scales_linearly(self):
        class CountedDescription(str):
            comparisons = 0
            def __ne__(self, other):
                type(self).comparisons += 1
                return super().__ne__(other)
        fast_counts, slow_counts = [], []
        for size in (32, 64):
            raw = dict(SOBDataRaw=[dict(SKUCode='S', WHCode='L', SupplierCode='V', SupplierDescription='old', SOB=1)] * size,
                       MOQDataRaw1=[], MOQDataRaw2=[dict(SKUCode='S', WHCode='L', SupplierCode='v ', SupplierDescription='old', MOQ=1)] * size)
            queues = dict.fromkeys(supplier_input.QUEUES, [])
            locations = [dict(WHCode='V', WHDescription=CountedDescription('vendor')) for _ in range(size)]
            args = dict(moq_format='WithDestLoc', locations=locations)
            CountedDescription.comparisons = 0
            expected = _REFERENCE_SUPPLIER_INPUT['compose_supplier_inputs'](raw, queues, **args)
            slow_counts.append(CountedDescription.comparisons)
            CountedDescription.comparisons = 0
            actual = supplier_input.compose_supplier_inputs(raw, queues, **args)
            fast_counts.append(CountedDescription.comparisons)
            self.assertEqual(actual, expected)
        self.assertLess(fast_counts[1], fast_counts[0] * 2.1)
        self.assertGreater(slow_counts[1], slow_counts[0] * 3.8)
        self.assertLess(fast_counts[1], slow_counts[1] // 50)


if __name__ == '__main__':
    unittest.main()
