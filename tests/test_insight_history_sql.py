"""PostgreSQL differential tests for selective Guided history aggregates.

The database cases are opt-in because their generated SELECT statements require
PostgreSQL's casts and aggregation behavior.  Every source is an in-statement
VALUES bag; the tests never create, update, or delete database objects.
"""
import os
import unittest
from datetime import date, timedelta
from decimal import Decimal
from itertools import product
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import excess_insights, insight_history_sql, insights
from mta.presentation.excess import FIELDS as EXCESS_FIELDS
from mta.presentation.insight_filters import InsightPredicate
from mta.presentation.permissions import PermissionCodes, permission_multiplicity
from mta.runtime.relational_state import CATALOG, PG_TYPES, db_value, quote


POSTGRES = os.environ.get('VF_PORTFOLIO_POSTGRES_TESTS') == '1'


def group(attribute, value, operator='equalto'):
    return {'filters': [dict(attributeName=attribute, value=value,
                             operator=operator)]}


def full_row(table, **values):
    row = {name: None for name, _ in CATALOG['tables'][table]}
    row.update(values)
    return row


def wire(kind):
    if kind in ('int', 'bigint'):
        return 'int'
    if kind == 'bit':
        return 'bool'
    if kind in ('float', 'real'):
        return 'float'
    return 'str'


def values_relation(table, rows):
    """Return a fully typed native-schema VALUES SELECT and image metadata."""
    columns = CATALOG['tables'][table]
    casts = ['bigint'] + [PG_TYPES[kind] for _, kind in columns]
    records = []
    for ordinal, row in enumerate(rows):
        records.append([ordinal] + [db_value(row[name], kind)
                                    for name, kind in columns])
    tuples = ','.join(
        '(' + ','.join('%s::' + cast for cast in casts) + ')'
        for _ in records)
    names = ['vf_ordinal'] + [name for name, _ in columns]
    query = ('SELECT * FROM (VALUES ' + tuples + ') AS V(' +
             ','.join(quote(name) for name in names) + ') WHERE TRUE')
    metadata = {'fields': [[name, name, wire(kind)]
                           for name, kind in columns], 'count': len(rows)}
    return query, [value for record in records for value in record], metadata


def excess_values_relation(run_id, rows):
    kinds = {
        'Tags': 'text', 'SKUCode': 'text', 'WhCode': 'text',
        'ParentWhCode': 'text', 'Norm': 'bigint', 'VirtualNorm': 'bigint',
        'Stock': 'bigint', 'GIT': 'bigint', 'BlueReq': 'bigint',
        'RequiredQty': 'bigint', 'PhysicalInventoryPen': 'numeric',
        'PhysicalInventoryColor': 'text',
        'PipelineInventoryPen': 'numeric',
        'PipelineInventoryColor': 'text', 'ExcessQty': 'bigint',
        'Amount': 'bigint', 'ReportDate': 'date',
    }
    names = ['run_id', 'ordinal', *EXCESS_FIELDS]
    casts = ['text', 'bigint', *[kinds[name] for name in EXCESS_FIELDS]]
    records = []
    for ordinal, row in enumerate(rows):
        values = [run_id, ordinal]
        for name in EXCESS_FIELDS:
            value = row[name]
            if value is not None and kinds[name] == 'date':
                value = date.fromisoformat(str(value))
            elif value is not None and kinds[name] == 'numeric':
                value = Decimal(str(value))
            values.append(value)
        records.append(values)
    tuples = ','.join(
        '(' + ','.join('%s::' + cast for cast in casts) + ')'
        for _ in records)
    relation = ('(VALUES ' + tuples + ') AS excess_values(' +
                ','.join(quote(name) for name in names) + ')')
    return relation, [value for record in records for value in record]


@unittest.skipUnless(POSTGRES, 'set VF_PORTFOLIO_POSTGRES_TESTS=1 for PostgreSQL')
class InsightHistorySqlPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if insight_history_sql.connection.vendor != 'postgresql':
            raise unittest.SkipTest('PostgreSQL connection required')

    def setUp(self):
        self.run = SimpleNamespace(
            pk='00000000-0000-0000-0000-000000000111',
            kind='LEGACY_UI_FIXTURE', business_date=date(2026, 6, 17))
        self.products = PermissionCodes({'SKU': 2, 'sku': 1})
        self.locations = PermissionCodes({'LOC': 3, 'loc': 2})
        self.skus = [
            full_row('BTR/SkuAttributeData', SKUCode='SKU', SL1='Family',
                     c1='sku-filter'),
            full_row('BTR/SkuAttributeData', SKUCode='SKU', SL1='Family',
                     c1='sku-filter'),
            full_row('BTR/SkuAttributeData', SKUCode='sku', SL1='Family',
                     c1='sku-filter'),
        ]
        self.locations_rows = [
            full_row('BTR/LocationAttributeData', WHCode='LOC',
                     LocationType='Leaf', LL1='Zone', c1='loc-filter'),
            full_row('BTR/LocationAttributeData', WHCode='LOC',
                     LocationType=None, LL1='Zone', c1='loc-filter'),
            full_row('BTR/LocationAttributeData', WHCode='loc',
                     LocationType='Lower', LL1='Zone', c1='loc-filter'),
            full_row('BTR/LocationAttributeData', WHCode='PARENT',
                     LocationType='Parent', LL1=None),
            full_row('BTR/LocationAttributeData', WHCode='PARENT',
                     LocationType='Parent', LL1=None),
        ]
        self.pairs = [
            full_row('BTR/SkuLocAttributeData', SKUCode='SKU', LocCode='LOC',
                     c1='pair-filter'),
            full_row('BTR/SkuLocAttributeData', SKUCode='SKU', LocCode='LOC',
                     c1='pair-filter'),
            full_row('BTR/SkuLocAttributeData', SKUCode='sku', LocCode='loc',
                     c1='pair-filter'),
        ]
        self.bpr = [
            full_row('BTR/BPR', SKUCode='SKU', WHCode='LOC',
                     ParentWhCode='PARENT', Norm=5,
                     PhysicalInventoryColor='Black', ReportDate='2026-06-16'),
            full_row('BTR/BPR', SKUCode='SKU', WHCode='LOC',
                     ParentWhCode='PARENT', Norm=5,
                     PhysicalInventoryColor='White', ReportDate='2026-06-16'),
            full_row('BTR/BPR', SKUCode='SKU', WHCode='LOC',
                     ParentWhCode='PARENT', Norm=5,
                     PhysicalInventoryColor=None, ReportDate='2026-06-16'),
            full_row('BTR/BPR', SKUCode='sku', WHCode='loc',
                     ParentWhCode='PARENT', Norm=6,
                     PhysicalInventoryColor='Green', ReportDate='2026-06-15'),
            full_row('BTR/BPR', SKUCode='SKU', WHCode='loc',
                     ParentWhCode='PARENT', Norm=6,
                     PhysicalInventoryColor='White', ReportDate='2026-06-15'),
            full_row('BTR/BPR', SKUCode='SKU', WHCode='LOC',
                     ParentWhCode='PARENT', Norm=5,
                     PhysicalInventoryColor='White', ReportDate='2026-06-12'),
        ]
        self.snapshots = [
            full_row('BTR/BTRSnapshotForUI', SKUCode='SKU', WhCode='LOC',
                     ParentWhCode='PARENT', AgePhysicalInv=4),
            full_row('BTR/BTRSnapshotForUI', SKUCode='SKU', WhCode='LOC',
                     ParentWhCode='PARENT', AgePhysicalInv=5),
            full_row('BTR/BTRSnapshotForUI', SKUCode='SKU', WhCode='LOC',
                     ParentWhCode='PARENT', AgePhysicalInv=3),
            full_row('BTR/BTRSnapshotForUI', SKUCode='sku', WhCode='loc',
                     ParentWhCode='PARENT', AgePhysicalInv=4),
        ]
        self.images = {
            'closing/btr/BPR': ('BTR/BPR', self.bpr),
            'closing/btr/SkuAttributeData':
                ('BTR/SkuAttributeData', self.skus),
            'closing/btr/LocationAttributeData':
                ('BTR/LocationAttributeData', self.locations_rows),
            'closing/btr/SkuLocAttributeData':
                ('BTR/SkuLocAttributeData', self.pairs),
            'closing/btr/BTRSnapshotForUI':
                ('BTR/BTRSnapshotForUI', self.snapshots),
        }

    def relation(self, _run, path):
        table, rows = self.images[path]
        query, params, _ = values_relation(table, rows)
        return query, params

    def metadata(self, _run, path):
        table, rows = self.images[path]
        _, _, metadata = values_relation(table, rows)
        return metadata

    def image_rows(self, _run, path):
        return self.images[path][1]

    def read(self, payload, kind):
        with patch.object(insight_history_sql, 'image_query',
                          side_effect=self.relation), \
             patch.object(insight_history_sql, 'image_metadata',
                          side_effect=self.metadata), \
             patch.object(insight_history_sql, 'image_rows',
                          side_effect=self.image_rows), \
             patch.object(insight_history_sql.hierarchy, 'selected_manifest',
                          return_value=None), \
             patch.object(insight_history_sql, 'scope',
                          return_value=(self.products, self.locations)):
            return insight_history_sql.read_history(self.run, payload, kind)

    def expected_availability(self, payload, kind):
        state = dict(BPR=self.bpr, SkuAttributeData=self.skus,
                     LocationAttributeData=self.locations_rows,
                     SkuLocAttributeData=self.pairs)
        joined = insights.availability_rows(state, filter_owners=True)
        predicate = InsightPredicate(payload, self.locations_rows, kind=kind)
        cutoff = self.run.business_date - timedelta(days=int(payload['horizon']))

        def selected_weight(row):
            return (permission_multiplicity(self.products, row['SKUCode']) *
                    permission_multiplicity(self.locations, row['WhCode']) *
                    predicate(row))

        joined = [row for row in joined
                  if date.fromisoformat(row['ReportDate']) > cutoff]
        if kind == 'availability-trend':
            selected = [row for row in joined
                        for _ in range(selected_weight(row))]
            return insights.availability_trend(selected)
        return insights.availability_ageing(
            joined, self.snapshots, int(payload['ageing']),
            predicate=selected_weight)

    def test_availability_trend_full_bag_filters_scope_and_horizon(self):
        payload = {'horizon': 5, 'filters': {
            'supplyChainFilter': group('forChildren', 'Parent'),
            'productFilter': group('p1', 'Family'),
            'locationFilter': group('l1', 'Zone'),
            'availabilityFilter': group('norm', '4', 'greaterthan'),
            'customAttributeFilter': group('skulocattr1', 'pair-filter'),
        }}
        expected = self.expected_availability(payload, 'availability-trend')
        self.assertEqual(expected, [
            {'week': '2026-06-15', 'percentage': 100,
             'locationtype': 'Lower'},
            {'week': '2026-06-16', 'percentage': 50,
             'locationtype': 'Leaf'},
            {'week': '2026-06-16', 'percentage': 50},
        ])
        self.assertEqual(self.read(payload, 'availability-trend'), expected)

    def test_availability_ageing_snapshot_and_parent_bags(self):
        payload = {'horizon': 5, 'ageing': 4, 'filters': {
            'supplyChainFilter': group('forChildren', 'Parent'),
            'productFilter': group('p1', 'Family'),
            'locationFilter': group('l1', 'Zone'),
            'customAttributeFilter': group('skuattr1', 'sku-filter'),
        }}
        expected = self.expected_availability(payload, 'availability-ageing')
        self.assertEqual(expected, [
            {'date': '2026-06-15', 'black': 0, 'red': 0, 'white': 0},
            {'date': '2026-06-16', 'black': 192, 'red': 0, 'white': 192},
        ])
        self.assertEqual(self.read(payload, 'availability-ageing'), expected)

    def test_availability_trend_unfiltered_pair_occurrence_weight(self):
        payload = {'horizon': 5, 'ageing': 'ignored-by-trend', 'filters': {}}
        expected = self.expected_availability(payload, 'availability-trend')
        self.assertEqual(self.read(payload, 'availability-trend'), expected)

    def test_availability_ageing_snapshot_predicate_uses_raw_occurrences(self):
        payload = {'horizon': 5, 'ageing': 4, 'filters': {}}
        predicate = SimpleNamespace(children=[], sql_terms=[
            ('compare', ('_snapshot', 'AgePhysicalInv'), 'greaterthan', '4'),
        ])
        state = dict(BPR=self.bpr, SkuAttributeData=self.skus,
                     LocationAttributeData=self.locations_rows,
                     SkuLocAttributeData=self.pairs)
        joined = [row for row in insights.availability_rows(
            state, filter_owners=True)
            if date.fromisoformat(row['ReportDate']) > date(2026, 6, 12)]

        def selected_weight(row):
            return (permission_multiplicity(self.products, row['SKUCode']) *
                    permission_multiplicity(self.locations, row['WhCode']) *
                    (row['_snapshot']['AgePhysicalInv'] > 4))

        expected = insights.availability_ageing(
            joined, self.snapshots, 4, predicate=selected_weight)
        with patch.object(insight_history_sql, 'InsightPredicate',
                          return_value=predicate):
            self.assertEqual(self.read(payload, 'availability-ageing'), expected)

    def test_excess_aggregates_match_project_with_values_fact_relation(self):
        excess_rows = [
            self.excess_row('SKU', 'LOC', 'White', 10, '2026-06-16'),
            self.excess_row('SKU', 'LOC', 'white', None, '2026-06-16'),
            self.excess_row('sku', 'loc', 'White', 7, '2026-06-15'),
            self.excess_row('SKU', 'loc', 'White', 99, '2026-06-15'),
            self.excess_row('SKU', 'LOC', 'Black', 20, '2026-06-16'),
            self.excess_row('SKU', 'LOC', 'White', 50, '2026-06-12'),
        ]
        self.images = {
            'closing/importer/SkuAttributeData':
                ('Importer/SkuAttributeData', [self.importer_row(
                    'Importer/SkuAttributeData', row) for row in self.skus]),
            'closing/importer/LocationAttributeData':
                ('Importer/LocationAttributeData', [self.importer_row(
                    'Importer/LocationAttributeData', row)
                    for row in self.locations_rows]),
            'closing/importer/SkuLocAttributeData':
                ('Importer/SkuLocAttributeData', [self.importer_row(
                    'Importer/SkuLocAttributeData', row) for row in self.pairs]),
        }
        payload = {'horison': 5, 'filters': {
            'supplyChainFilter': group('forChildren', 'Parent'),
            'productFilter': group('p1', 'Family'),
            'locationFilter': group('l1', 'Zone'),
            'customAttributeFilter': group('skulocattr1', 'pair-filter'),
        }}
        for kind, value in (('excess-sku', False), ('excess-value', True)):
            with self.subTest(kind=kind):
                actual = self.read_excess(payload, kind, excess_rows)
                expected = self.expected_excess(payload, kind, excess_rows,
                                                value=value)
                expected_explicit = ([
                    {'date': '2026-06-15', 'locationtype': 'Lower',
                     'value': 28},
                    {'date': '2026-06-16', 'locationtype': '-',
                     'value': 1440},
                    {'date': '2026-06-16', 'locationtype': 'Leaf',
                     'value': 1440},
                ] if value else [
                    {'date': '2026-06-15', 'locationtype': 'Lower',
                     'countSku': 4},
                    {'date': '2026-06-16', 'locationtype': '-',
                     'countSku': 96},
                    {'date': '2026-06-16', 'locationtype': 'Leaf',
                     'countSku': 96},
                ])
                self.assertEqual(expected, expected_explicit)
                self.assertEqual(actual, expected)

        unfiltered = {'horison': 5, 'filters': {}}
        actual = self.read_excess(unfiltered, 'excess-value', excess_rows)
        expected = self.expected_excess(
            unfiltered, 'excess-value', excess_rows, value=True)
        self.assertEqual(actual, expected)

    @staticmethod
    def importer_row(table, source):
        names = {name for name, _ in CATALOG['tables'][table]}
        return full_row(table, **{name: value for name, value in source.items()
                                  if name in names})

    @staticmethod
    def excess_row(sku, location, colour, amount, report_date):
        row = {name: None for name in EXCESS_FIELDS}
        row.update(SKUCode=sku, WhCode=location, ParentWhCode='PARENT',
                   PhysicalInventoryColor=colour, Amount=amount,
                   ReportDate=report_date)
        return row

    def read_excess(self, payload, kind, rows):
        real_cursor = insight_history_sql.connection.cursor
        relation, relation_params = excess_values_relation(self.run.pk, rows)
        target = 'mta.' + quote(
            insight_history_sql.ExcessInventoryRow._meta.db_table)

        class ValuesCursor:
            def __enter__(cursor_self):
                cursor_self.manager = real_cursor()
                cursor_self.cursor = cursor_self.manager.__enter__()
                return cursor_self

            def __exit__(cursor_self, *args):
                return cursor_self.manager.__exit__(*args)

            def execute(cursor_self, query, params=None):
                if query.startswith('SET LOCAL '):
                    return cursor_self.cursor.execute(query, params)
                if target not in query:
                    raise AssertionError('excess fact relation was not selected')
                return cursor_self.cursor.execute(
                    query.replace(target, relation),
                    relation_params + list(params))

            def fetchall(cursor_self):
                return cursor_self.cursor.fetchall()

        integers = {'Norm', 'VirtualNorm', 'Stock', 'GIT', 'BlueReq',
                    'RequiredQty', 'ExcessQty', 'Amount'}
        item = {'fields': list(EXCESS_FIELDS),
                'wire': ['int' if name in integers else 'str'
                         for name in EXCESS_FIELDS]}
        with patch.object(insight_history_sql, 'image_query',
                          side_effect=self.relation), \
             patch.object(insight_history_sql, 'image_metadata',
                          side_effect=self.metadata), \
             patch.object(insight_history_sql, 'image_rows',
                          side_effect=self.image_rows), \
             patch.object(insight_history_sql.hierarchy, 'selected_manifest',
                          return_value=None), \
             patch.object(insight_history_sql, 'scope',
                          return_value=(self.products, self.locations)), \
             patch('mta.presentation.fixture.binding',
                   return_value=(self.run, {})), \
             patch('mta.presentation.fixture.receipt', return_value=item), \
             patch.object(insight_history_sql.connection, 'cursor',
                          side_effect=ValuesCursor):
            return insight_history_sql.read_history(self.run, payload, kind)

    def expected_excess(self, payload, kind, rows, *, value):
        sku_rows = self.images['closing/importer/SkuAttributeData'][1]
        location_rows = self.images['closing/importer/LocationAttributeData'][1]
        pair_rows = self.images['closing/importer/SkuLocAttributeData'][1]
        predicate = InsightPredicate(payload, location_rows, kind=kind)
        cutoff = self.run.business_date - timedelta(days=int(payload['horison']))
        selected = []
        for row in rows:
            if date.fromisoformat(row['ReportDate']) <= cutoff:
                continue
            sku, location = row['SKUCode'], row['WhCode']
            populations = (
                [item for item in sku_rows if item['SKUCode'] == sku],
                [item for item in location_rows if item['WHCode'] == location],
                [item for item in pair_rows
                 if (item['SKUCode'], item['LocCode']) == (sku, location)] or
                [{}],
            )
            for sku_row, location_row, pair_row in product(*populations):
                joined = {**row, 'LocationType':
                          location_row.get('LocationType'), '_a': row,
                          '_sku': sku_row, '_location': location_row,
                          '_pair': pair_row}
                weight = (permission_multiplicity(self.products, sku) *
                          permission_multiplicity(self.locations, location) *
                          predicate(joined))
                selected.extend(dict(joined) for _ in range(weight))
        return excess_insights.project(selected, value=value)


if __name__ == '__main__':
    unittest.main()
