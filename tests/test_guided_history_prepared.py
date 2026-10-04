"""Focused PostgreSQL differential for sealed Guided history occurrences.

All prepared and source bags are substituted with typed VALUES relations.  The
test performs SELECTs only and never creates, updates, or deletes database rows.
"""
import os
import unittest
from datetime import date, timedelta
from itertools import product
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import excess_insights, guided_history_prepared, insights
from mta.presentation.bpr_sql import _values_cte
from mta.presentation.excess import FIELDS as EXCESS_FIELDS
from mta.presentation.guided_history_fields import ROW_FIELDS, schema_digest
from mta.presentation.insight_filters import InsightPredicate
from mta.presentation.insight_history_sql import _result
from mta.presentation.permissions import PermissionCodes, permission_multiplicity
from mta.runtime.relational_state import CATALOG, quote


POSTGRES = os.environ.get('VF_PORTFOLIO_POSTGRES_TESTS') == '1'


def full_row(table, **values):
    return {**{name: None for name, _ in CATALOG['tables'][table]}, **values}


def group(attribute, value, operator='equalto'):
    return {'filters': [dict(attributeName=attribute, value=value,
                             operator=operator)]}


def source_relation(table, rows):
    fields = CATALOG['tables'][table]
    names = ('vf_ordinal', *[name for name, _ in fields])
    casts = {'vf_ordinal': '::bigint'}
    pg = {'int': 'bigint', 'bigint': 'bigint', 'bit': 'boolean',
          'date': 'date', 'datetime': 'timestamp', 'decimal': 'numeric',
          'numeric': 'numeric', 'float': 'double precision',
          'real': 'double precision', 'nchar': 'text', 'nvarchar': 'text',
          'varchar': 'text', 'xml': 'text'}
    casts.update({name: '::' + pg[kind] for name, kind in fields})
    query, params = _values_cte(
        [dict(vf_ordinal=ordinal, **row) for ordinal, row in enumerate(rows)],
        names, casts)
    metadata = {'fields': [(name, name,
                 'int' if kind in ('int', 'bigint') else
                 'bool' if kind == 'bit' else 'str')
                 for name, kind in fields]}
    return query, params, metadata


def literal(value, cast):
    if value is None:
        return 'NULL::' + cast
    if cast in ('bigint', 'numeric'):
        return str(value) + '::' + cast
    escaped = str(value).replace("'", "''")
    return "'" + escaped + "'::" + cast


def literal_relation(rows, fields, casts):
    records = ','.join('(' + ','.join(literal(row.get(name), casts[name])
                                       for name in fields) + ')'
                       for row in rows)
    return '(VALUES ' + records + ') AS prepared(' + \
        ','.join(quote(name) for name in fields) + ')'


@unittest.skipUnless(POSTGRES, 'set VF_PORTFOLIO_POSTGRES_TESTS=1 for PostgreSQL')
class GuidedHistoryPreparedPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if guided_history_prepared.connection.vendor != 'postgresql':
            raise unittest.SkipTest('PostgreSQL connection required')

    def setUp(self):
        self.run = SimpleNamespace(
            pk='00000000-0000-0000-0000-000000000321',
            kind='LEGACY_UI_FIXTURE', business_date=date(2026, 6, 17))
        self.products = PermissionCodes({'S1': 2, 'S2': 1})
        self.allowed_locations = PermissionCodes({'L1': 3, 'L2': 2})
        self.skus = [
            full_row('BTR/SkuAttributeData', SKUCode='S1', SL1='Family', c1='a'),
            full_row('BTR/SkuAttributeData', SKUCode='S1', SL1='Family', c1='b'),
            full_row('BTR/SkuAttributeData', SKUCode='S2', SL1='Other', c1='z'),
            full_row('BTR/SkuAttributeData', SKUCode=None, c1='null-sku'),
        ]
        self.locations = [
            full_row('BTR/LocationAttributeData', WHCode='L1',
                     LocationType='Leaf', LL1='Zone', c1='x'),
            full_row('BTR/LocationAttributeData', WHCode='L1',
                     LocationType=None, LL1='Zone', c1='y'),
            full_row('BTR/LocationAttributeData', WHCode='L2',
                     LocationType='Lower', LL1='Other', c1='x'),
            full_row('BTR/LocationAttributeData', WHCode='PARENT',
                     LocationType='Parent'),
            full_row('BTR/LocationAttributeData', WHCode='PARENT',
                     LocationType='Parent'),
            full_row('BTR/LocationAttributeData', WHCode=None,
                     LocationType='Null', c1='null-location'),
        ]
        self.pairs = [
            full_row('BTR/SkuLocAttributeData', SKUCode='S1', LocCode='L1', c1='pair-a'),
            full_row('BTR/SkuLocAttributeData', SKUCode='S1', LocCode='L1', c1='pair-b'),
            full_row('BTR/SkuLocAttributeData', SKUCode=None, LocCode=None, c1='null-pair'),
        ]
        self.bpr = [
            full_row('BTR/BPR', SKUCode='S1', WHCode='L1', ParentWhCode='PARENT',
                     Norm=5, PhysicalInventoryColor='Black', ReportDate='2026-06-16'),
            full_row('BTR/BPR', SKUCode='S1', WHCode='L1', ParentWhCode='PARENT',
                     Norm=6, PhysicalInventoryColor='White', ReportDate='2026-06-16'),
            full_row('BTR/BPR', SKUCode='S2', WHCode='L2', ParentWhCode='PARENT',
                     Norm=7, PhysicalInventoryColor='Red', ReportDate='2026-06-15'),
            full_row('BTR/BPR', SKUCode='S1', WHCode='L1', ParentWhCode='PARENT',
                     Norm=8, PhysicalInventoryColor='White', ReportDate='2026-06-13'),
            full_row('BTR/BPR', SKUCode=None, WHCode=None, ParentWhCode=None,
                     PhysicalInventoryColor='White', ReportDate='2026-06-16'),
        ]
        self.snapshots = [
            full_row('BTR/BTRSnapshotForUI', SKUCode='S1', WhCode='L1',
                     ParentWhCode='PARENT', AgePhysicalInv=4),
            full_row('BTR/BTRSnapshotForUI', SKUCode='S1', WhCode='L1',
                     ParentWhCode='PARENT', AgePhysicalInv=5),
            full_row('BTR/BTRSnapshotForUI', SKUCode='S1', WhCode='L1',
                     ParentWhCode='PARENT', AgePhysicalInv=3),
            full_row('BTR/BTRSnapshotForUI', SKUCode='UNMATCHED', WhCode='NOWHERE',
                     ParentWhCode='PARENT', AgePhysicalInv=9),
        ]
        self.excess = [
            self.excess_row('S1', 'L1', 'White', 10, '2026-06-16'),
            self.excess_row('S1', 'L1', 'white', None, '2026-06-16'),
            self.excess_row('S2', 'L2', 'White', 7, '2026-06-15'),
            self.excess_row('S1', 'L1', 'Black', 20, '2026-06-16'),
            self.excess_row('S1', 'L1', 'White', 50, '2026-06-13'),
            self.excess_row(None, None, 'White', 99, '2026-06-16'),
        ]
        self.importer_skus = [self.importer_row('Importer/SkuAttributeData', row)
                              for row in self.skus]
        self.importer_locations = [self.importer_row('Importer/LocationAttributeData', row)
                                   for row in self.locations]
        self.importer_pairs = [self.importer_row('Importer/SkuLocAttributeData', row)
                               for row in self.pairs]
        self.prepared_availability = self.prepare_availability()
        self.prepared_snapshot = self.prepare_snapshots()
        self.prepared_excess = self.prepare_excess()

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

    @staticmethod
    def matching(rows, field, value):
        if value is None:
            return []
        return [(ordinal, row) for ordinal, row in enumerate(rows)
                if row[field] is not None and row[field] == value]

    def joined(self, facts, skus, locations, pairs, *, excess=False):
        result = []
        for fact_ordinal, fact in enumerate(facts):
            sku = fact['SKUCode']; location = fact['WhCode' if excess else 'WHCode']
            sku_rows = self.matching(skus, 'SKUCode', sku)
            location_rows = self.matching(locations, 'WHCode', location)
            pair_rows = [(ordinal, row) for ordinal, row in enumerate(pairs)
                         if sku is not None and location is not None and
                         row['SKUCode'] == sku and row['LocCode'] == location]
            pair_rows = pair_rows or [(None, {})]
            for (sku_ordinal, sku_row), (location_ordinal, location_row), \
                    (pair_ordinal, pair_row) in product(sku_rows, location_rows, pair_rows):
                result.append((fact_ordinal, fact, sku_ordinal, sku_row,
                               location_ordinal, location_row, pair_ordinal, pair_row))
        return result

    def snapshot_anchors(self):
        anchors = {}
        for ordinal, row in enumerate(self.snapshots):
            anchors.setdefault((row['SKUCode'], row['WhCode']), ordinal)
        return anchors

    def prepare_availability(self):
        anchors = self.snapshot_anchors(); rows = []
        for occurrence in self.joined(self.bpr, self.skus, self.locations, self.pairs):
            fact_ordinal, fact, sku_ordinal, _, location_ordinal, location, pair_ordinal, _ = occurrence
            rows.append(dict(run_id=self.run.pk, ordinal=len(rows), fact_ordinal=fact_ordinal,
                sku_ordinal=sku_ordinal, location_ordinal=location_ordinal,
                pair_ordinal=pair_ordinal,
                snapshot_anchor_ordinal=anchors.get((fact['SKUCode'], fact['WHCode'])),
                report_date=fact['ReportDate'], sku_code=fact['SKUCode'],
                location_code=fact['WHCode'], parent_location_code=fact['ParentWhCode'],
                location_type=location['LocationType'],
                physical_inventory_color=fact['PhysicalInventoryColor']))
        return rows

    def prepare_snapshots(self):
        anchors = self.snapshot_anchors()
        return [dict(run_id=self.run.pk,
                     snapshot_anchor_ordinal=anchors[(row['SKUCode'], row['WhCode'])],
                     snapshot_ordinal=ordinal,
                     age_physical_inventory=row['AgePhysicalInv'])
                for ordinal, row in enumerate(self.snapshots)]

    def prepare_excess(self):
        rows = []
        for occurrence in self.joined(self.excess, self.importer_skus,
                                      self.importer_locations,
                                      self.importer_pairs, excess=True):
            fact_ordinal, fact, sku_ordinal, _, location_ordinal, location, pair_ordinal, _ = occurrence
            rows.append(dict(run_id=self.run.pk, ordinal=len(rows), fact_ordinal=fact_ordinal,
                sku_ordinal=sku_ordinal, location_ordinal=location_ordinal,
                pair_ordinal=pair_ordinal, report_date=fact['ReportDate'],
                sku_code=fact['SKUCode'], location_code=fact['WhCode'],
                parent_location_code=fact['ParentWhCode'],
                location_type=location['LocationType'],
                physical_inventory_color=fact['PhysicalInventoryColor'], amount=fact['Amount']))
        return rows

    def sources(self, family):
        if family == 'availability':
            return {
                'closing/btr/SkuAttributeData': ('BTR/SkuAttributeData', self.skus),
                'closing/btr/LocationAttributeData': ('BTR/LocationAttributeData', self.locations),
                'closing/btr/SkuLocAttributeData': ('BTR/SkuLocAttributeData', self.pairs),
                'closing/btr/BTRSnapshotForUI': ('BTR/BTRSnapshotForUI', self.snapshots),
            }
        return {
            'closing/importer/SkuAttributeData': ('Importer/SkuAttributeData', self.importer_skus),
            'closing/importer/LocationAttributeData': ('Importer/LocationAttributeData', self.importer_locations),
            'closing/importer/SkuLocAttributeData': ('Importer/SkuLocAttributeData', self.importer_pairs),
        }

    def read(self, kind, cutoff, predicate, minimum_age=None):
        family = 'excess' if kind.startswith('excess-') else 'availability'
        sources = self.sources(family)
        prepared = {
            guided_history_prepared.GuidedAvailabilityHistoryRow._meta.db_table:
                (self.prepared_availability, ROW_FIELDS['availability']),
            guided_history_prepared.GuidedAvailabilitySnapshotReference._meta.db_table:
                (self.prepared_snapshot, ROW_FIELDS['snapshot']),
            guided_history_prepared.GuidedExcessHistoryRow._meta.db_table:
                (self.prepared_excess, ROW_FIELDS['excess']),
        }
        casts = {'run_id': 'text', 'ordinal': 'bigint', 'fact_ordinal': 'bigint',
                 'sku_ordinal': 'bigint', 'location_ordinal': 'bigint',
                 'pair_ordinal': 'bigint', 'snapshot_anchor_ordinal': 'bigint',
                 'snapshot_ordinal': 'bigint', 'report_date': 'date',
                 'sku_code': 'text', 'location_code': 'text',
                 'parent_location_code': 'text', 'location_type': 'text',
                 'physical_inventory_color': 'text', 'amount': 'bigint',
                 'age_physical_inventory': 'bigint'}
        replacements = {}
        for table, (rows, fields) in prepared.items():
            relation_fields = ('run_id', *fields)
            replacements['mta.' + quote(table)] = literal_relation(
                rows, relation_fields, casts)
        real_cursor = guided_history_prepared.connection.cursor

        class ValuesCursor:
            def __enter__(cursor_self):
                cursor_self.manager = real_cursor()
                cursor_self.cursor = cursor_self.manager.__enter__()
                return cursor_self

            def __exit__(cursor_self, *args):
                return cursor_self.manager.__exit__(*args)

            def execute(cursor_self, query, params=None):
                selected = [target for target in replacements if target in query]
                if not selected:
                    raise AssertionError('prepared relation was not selected')
                for target in selected:
                    query = query.replace(target, replacements[target])
                return cursor_self.cursor.execute(query, params)

            def fetchall(cursor_self):
                return cursor_self.cursor.fetchall()

        def image(_run, path):
            table, rows = sources[path]
            query, params, _ = source_relation(table, rows)
            return query, params

        def metadata(_run, path):
            table, rows = sources[path]
            return source_relation(table, rows)[2]

        receipt = SimpleNamespace(source_digest='source', schema_digest=schema_digest())
        receipt_query = SimpleNamespace(first=lambda: receipt)
        with patch.object(guided_history_prepared.settings, 'VF_GUIDED_PREPARED', True, create=True), \
             patch.object(guided_history_prepared.fixture, 'enabled', return_value=True), \
             patch.object(guided_history_prepared.fixture, 'binding',
                          return_value=(self.run, 'source')), \
             patch.object(guided_history_prepared, 'verify_guards'), \
             patch.object(guided_history_prepared.GuidedHistoryPreparedProjection.objects,
                          'filter', return_value=receipt_query), \
             patch.object(guided_history_prepared, 'image_query', side_effect=image), \
             patch.object(guided_history_prepared, 'image_metadata', side_effect=metadata), \
             patch.object(guided_history_prepared.connection, 'cursor', side_effect=ValuesCursor):
            rows = guided_history_prepared.read_prepared(
                self.run, cutoff, predicate, self.products,
                self.allowed_locations, kind, minimum_age=minimum_age)
        return _result(rows, kind)

    def expected(self, kind, cutoff, predicate, minimum_age=None):
        if kind.startswith('availability-'):
            joined = []
            for occurrence in self.joined(self.bpr, self.skus, self.locations, self.pairs):
                _, fact, _, sku, _, location, _, pair_row = occurrence
                if date.fromisoformat(fact['ReportDate']) <= cutoff:
                    continue
                joined.append({**fact, **location, 'WhCode': fact['WHCode'],
                    '_a': fact, '_sku': sku, '_location': location, '_pair': pair_row})
            def weight(row):
                return (permission_multiplicity(self.products, row['SKUCode']) *
                        permission_multiplicity(self.allowed_locations, row['WhCode']) *
                        predicate(row))
            if kind == 'availability-trend':
                selected = [row for row in joined for _ in range(weight(row))]
                return insights.availability_trend(selected)
            return insights.availability_ageing(
                joined, self.snapshots, minimum_age, predicate=weight)
        sources = self.sources('excess')
        selected = []
        for occurrence in self.joined(self.excess, self.importer_skus,
                                      self.importer_locations,
                                      self.importer_pairs, excess=True):
            _, fact, _, sku, _, location, _, pair_row = occurrence
            if date.fromisoformat(fact['ReportDate']) <= cutoff:
                continue
            row = {**fact, 'LocationType': location['LocationType'],
                   '_a': fact, '_sku': sku, '_location': location, '_pair': pair_row}
            copies = (permission_multiplicity(self.products, fact['SKUCode']) *
                      permission_multiplicity(self.allowed_locations, fact['WhCode']) *
                      predicate(row))
            selected.extend(dict(row) for _ in range(copies))
        return excess_insights.project(selected, value=kind == 'excess-value')

    def predicate(self, payload, kind):
        locations = (self.importer_locations if kind.startswith('excess-')
                     else self.locations)
        return InsightPredicate(payload, locations, kind=kind)

    def test_default_four_reads_match_native_occurrences(self):
        cases = (
            ('availability-trend', timedelta(days=90), None),
            ('availability-ageing', timedelta(days=30), 1),
            ('excess-sku', timedelta(days=90), None),
            ('excess-value', timedelta(days=90), None),
        )
        for kind, horizon, minimum_age in cases:
            with self.subTest(kind=kind):
                payload = {'filters': {}}
                predicate = self.predicate(payload, kind)
                cutoff = self.run.business_date - horizon
                self.assertEqual(self.read(kind, cutoff, predicate, minimum_age),
                                 self.expected(kind, cutoff, predicate, minimum_age))

    def test_nondefault_cutoff_age_parent_weights_and_raw_owner_or_filters(self):
        filters = {
            'supplyChainFilter': group('forChildren', 'Parent'),
            'productFilter': {'filters': [
                dict(attributeName='p1', value='Family', operator='equalto')]},
            'customAttributeFilter': {'filters': [
                dict(attributeName='SKUAttr1', value='a', operator='equalto'),
                dict(attributeName='SKUAttr1', value='b', operator='equalto'),
                dict(attributeName='LocAttr1', value='x', operator='equalto'),
                dict(attributeName='SKULocAttr1', value='pair-a', operator='equalto'),
            ]},
        }
        cutoff = self.run.business_date - timedelta(days=2)
        for kind in ('availability-trend', 'excess-sku', 'excess-value'):
            with self.subTest(kind=kind):
                predicate = self.predicate({'filters': filters}, kind)
                self.assertEqual(self.read(kind, cutoff, predicate),
                                 self.expected(kind, cutoff, predicate))

        base = self.predicate({'filters': filters}, 'availability-ageing')
        class SnapshotOrPredicate:
            children = base.children
            sql_terms = base.sql_terms + [('or', [
                ('compare', ('_snapshot', 'AgePhysicalInv'), 'equalto', '4'),
                ('compare', ('_snapshot', 'AgePhysicalInv'), 'equalto', '5'),
            ])]
            def __call__(self, row):
                return base(row) if row['_snapshot']['AgePhysicalInv'] in (4, 5) else 0
        predicate = SnapshotOrPredicate()
        self.assertEqual(self.read('availability-ageing', cutoff, predicate, 5),
                         self.expected('availability-ageing', cutoff, predicate, 5))


if __name__ == '__main__':
    unittest.main()
