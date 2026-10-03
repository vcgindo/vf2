"""Generated SQL contracts for the fixture-only BPR grid/count reader."""
import os
import unittest
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import bpr_sql
from mta.presentation.bpr import ReadModel, sort_rows
from mta.presentation.bpr_filters import BprPredicate
from mta.presentation.context import PermissionCodes, PublicationUnavailable
from mta.presentation.permissions import permission_multiplicity
from mta.runtime.relational_state import CATALOG, PG_TYPES


class BprFixtureSqlTests(unittest.TestCase):
    importer = {
        'SkuAttributeData': [dict(SKUCode='sku', **{f'SL{i}': None for i in range(1, 6)},
                                  **{f'c{i}': None for i in range(1, 16)})],
        'LocationAttributeData': [dict(WHCode='loc', LocationType='leaf', LogisticsLocation=None,
                                       **{f'LL{i}': None for i in range(1, 6)},
                                       **{f'c{i}': None for i in range(1, 16)})],
    }
    ancillary = {'InTransitData': [], 'BPRReport_RemarkDetails': [
        dict(SKUCode='sku', WhCode='loc', RemarkDate='2026-04-07T01:00:00', Remark='first'),
        dict(SKUCode='sku', WhCode='loc', RemarkDate='2026-04-07T01:00:00', Remark='tied'),
    ]}

    def build(self, *, count, payload=None, paging=(1, 50)):
        payload = payload or {}
        run = SimpleNamespace(pk='run', kind='LEGACY_UI_FIXTURE')
        with patch.object(bpr_sql, 'image_query', side_effect=lambda r, p: ('SELECT * FROM retained_' + p.replace('/', '_'), [p])), \
             patch.object(bpr_sql, 'scope', return_value=(PermissionCodes({'sku': 2}), PermissionCodes({'loc': 3}))):
            return bpr_sql._build(run, payload, self.importer, None, self.ancillary, paging, count)

    def test_count_keeps_inner_standard_latest_remark_ties_and_permission_bags(self):
        query, values = self.build(count=True)
        self.assertIn(' JOIN S ON ', query)
        self.assertNotIn(' LEFT JOIN S ON ', query)
        self.assertIn('LEFT JOIN latest_remarks RM', query)
        self.assertIn('max("RemarkDate")', query)
        self.assertIn('SELECT count(*)', query)
        # One copy comes from each tied remark; the remaining copies are the
        # authorization bags (2 products and 3 locations).
        self.assertEqual(values.count('sku'), 4)
        self.assertEqual(values.count('loc'), 5)
        self.assertNotIn('LIMIT %s', query)

    def test_grid_pages_candidate_keys_then_final_rejoins_duplicate_bag(self):
        query, values = self.build(count=False, paging=(3, 50))
        self.assertIn('selected AS (SELECT A."SKUCode",A."WhCode"', query)
        self.assertIn(' LEFT JOIN S ON ', query)
        self.assertIn('selected_counts AS', query)
        self.assertIn('CROSS JOIN LATERAL generate_series(1,K.copies)', query)
        self.assertIn('LEFT JOIN latest_remarks RM', query)
        self.assertIn('LEFT JOIN T ON', query)
        self.assertIn('CASE WHEN V."PhysicalInventoryPen"=-99999999.00 THEN NULL', query)
        self.assertIn('lower(rtrim(A."WhCode"::text,\' \')) DESC NULLS LAST', query)
        self.assertIn('lower(rtrim(A."SKUCode"::text,\' \')) NULLS FIRST', query)
        self.assertNotIn(',,', query)
        self.assertEqual(values[-3:], [50, 100, 'closing/btr/BufferTrendPhysicalInv'])
        # Final joins deliberately do not reapply candidate permission/filter
        # predicates; selected key multiplicity owns the final rejoin.
        self.assertEqual(query.count(' JOIN P ON '), 1)

    def test_compiler_retains_raw_filter_owners_and_child_multiplicity(self):
        payload = {'filters': {
            'availabilityFilter': {'filters': [
                dict(attributeName='norm', operator='greaterthan', value='4'),
                dict(attributeName='virtualnorm', operator='equalto', value='7'),
                dict(attributeName='pipo,seasonality', operator='equalto', value='Phase In'),
            ]},
            'customAttributeFilter': {'filters': [
                dict(attributeName='SKULocAttr1', operator='contains', value='x')
            ]},
            'supplyChainFilter': {'filters': [
                dict(attributeName='forChildren', operator='equalto', value='parent')
            ]},
        }}
        query, values = self.build(count=True, payload=payload)
        self.assertIn('A."Norm"::numeric>%s', query)
        self.assertIn('V."VirtualNorm"::numeric=%s', query)
        self.assertIn('S."Tags"', query)
        self.assertIn('B."c1"::text ~* %s', query)
        self.assertIn('JOIN D parent ON', query)
        self.assertIn('parent."LocationType"', query)
        self.assertIn('parent', values)

    def test_public_reader_is_fixture_only_validates_filters_and_returns_native_rows(self):
        with self.assertRaisesRegex(ValueError, 'fixture-only'):
            bpr_sql.read_bpr(SimpleNamespace(kind='DAILY_CHAIN'), {}, paging=(1, 5))
        run = SimpleNamespace(kind='LEGACY_UI_FIXTURE')
        cursor = MagicMock()
        cursor.description = [('SKUCode',), ('intransit',)]
        cursor.fetchall.return_value = [('sku', None)]
        with patch.object(bpr_sql, '_projected_attributes', return_value=(self.importer, None)), \
             patch.object(bpr_sql, 'BprPredicate') as predicate, \
             patch('mta.presentation.fixture.bpr_ancillary', return_value=self.ancillary), \
             patch.object(bpr_sql, '_build', return_value=('SELECT result', ['bound'])), \
             patch.object(bpr_sql.connection, 'cursor') as factory:
            factory.return_value.__enter__.return_value = cursor
            self.assertEqual(bpr_sql.read_bpr(run, {}, paging=(1, 5)),
                             [{'SKUCode': 'sku', 'intransit': None}])
            predicate.assert_called_once()
            cursor.execute.assert_called_once_with('SELECT result', ['bound'])

    def test_nonempty_transit_fails_closed(self):
        run = SimpleNamespace(kind='LEGACY_UI_FIXTURE')
        ancillary = {**self.ancillary, 'InTransitData': [dict(SKUCode='sku', WhCode='loc')]}
        with patch.object(bpr_sql, '_projected_attributes', return_value=(self.importer, None)), \
             patch.object(bpr_sql, 'BprPredicate'), \
             patch('mta.presentation.fixture.bpr_ancillary', return_value=ancillary):
            with self.assertRaisesRegex(PublicationUnavailable, 'nonempty_BPR_transit'):
                bpr_sql.read_bpr(run, {}, paging=(1, 5))

    def test_established_predicate_rejects_legacy_missing_alias_before_sql(self):
        run = SimpleNamespace(kind='LEGACY_UI_FIXTURE')
        payload = {'filters': {'availabilityFilter': {'filters': [
            dict(attributeName='category', operator='equalto', value='x')
        ]}}}
        with patch.object(bpr_sql, '_projected_attributes', return_value=(self.importer, None)), \
             patch('mta.presentation.fixture.bpr_ancillary', return_value=self.ancillary), \
             patch.object(bpr_sql, '_build') as build:
            with self.assertRaisesRegex(PublicationUnavailable, 'missing alias b for category'):
                bpr_sql.read_bpr(run, payload, paging=(1, 5))
            build.assert_not_called()

    @unittest.skipUnless(os.environ.get('VF_RUN_POSTGRESQL_DIFFERENTIALS') == '1' and
                         bpr_sql.connection.vendor == 'postgresql',
                         'PostgreSQL-only SELECT/VALUES differential')
    def test_postgresql_duplicate_bags_tied_remarks_filters_and_page_differential(self):
        """Exercise expansion/order semantics in PostgreSQL without table writes."""
        def row(table, **values):
            return {**{name: None for name, _ in CATALOG['tables'][table]}, **values}

        base = [row('BPR/BPR_Table', SKUCode='SKU', SKUName='Item', WhCode='LOC',
            WhName='Location', ParentWhCode='PARENT', Stock=Decimal('9'), Norm=Decimal('4'),
            GIT=Decimal('2'), TechColorSequence=1, EcoColorSequence=None, EcoColor='Red',
            Req=None, RationedQTY=None, LeftoverParentStock=None,
            ResidualSnP=Decimal('1'), NormReq=Decimal('2'), BlueReq=Decimal('3'),
            **{'PhaseIn-Out': 1, 'SKULocAttr1': 'base-x'})]
        ration = [
            row('BPR/vf_RationedReqReport', SKUCode='SKU', WhCode='LOC', VirtualNorm=Decimal('5'),
                PhysicalInventoryColorSequence=None, PhysicalInventoryPen=Decimal('-99999999.00'),
                DispatchPen=Decimal('-99999999.00'), PhysicalInventoryColor='Black',
                DispatchColor='Green'),
            row('BPR/vf_RationedReqReport', SKUCode='SKU', WhCode='LOC', VirtualNorm=Decimal('5'),
                PhysicalInventoryColorSequence=1, PhysicalInventoryPen=Decimal('7'),
                DispatchPen=Decimal('8'), PhysicalInventoryColor='Black', DispatchColor='Green'),
        ]
        standard = [row('Importer/SKULocStandardAttributes', SKUCode='SKU', WhCode='LOC',
                        Tags='Phase In') for _ in range(2)]
        pair = [row('Importer/SkuLocAttributeData', SKUCode='SKU', LocCode='LOC', c1='pair-x')
                for _ in range(2)]
        sku = [row('Importer/SkuAttributeData', SKUCode='SKU', SL1='FG', c1='sku-x')
               for _ in range(2)]
        location = [row('Importer/LocationAttributeData', WHCode='LOC', LocationType='Leaf',
                        LL1='Zone', c1='loc-x') for _ in range(2)]
        trend = [row('BTR/BufferTrendPhysicalInv', SKUCode='SKU', WhCode='LOC',
                     Availability_01_30=Decimal(str(i))) for i in (1, 2)]
        images = {
            'reports/bpr/BPR_Table': ('BPR/BPR_Table', base),
            'reports/bpr/vf_RationedReqReport': ('BPR/vf_RationedReqReport', ration),
            'closing/dbm/SKULocStandardAttributes': ('Importer/SKULocStandardAttributes', standard),
            'closing/importer/SkuLocAttributeData': ('Importer/SkuLocAttributeData', pair),
            'closing/importer/SkuAttributeData': ('Importer/SkuAttributeData', sku),
            'closing/importer/LocationAttributeData': ('Importer/LocationAttributeData', location),
            'closing/btr/BufferTrendPhysicalInv': ('BTR/BufferTrendPhysicalInv', trend),
        }

        def relation(_run, path):
            table, rows = images[path]
            columns = ('vf_ordinal',) + tuple(name for name, _ in CATALOG['tables'][table])
            casts = {'vf_ordinal': '::bigint', **{
                name: '::' + PG_TYPES[kind] for name, kind in CATALOG['tables'][table]}}
            supplied = [dict(vf_ordinal=ordinal, **record) for ordinal, record in enumerate(rows)]
            return bpr_sql._values_cte(supplied, columns, casts)

        tied = datetime(2026, 4, 7, 1)
        ancillary = {'InTransitData': [], 'BPRReport_RemarkDetails': [
            dict(SKUCode='SKU', WhCode='LOC', RemarkDate=tied, Remark='tie-' + str(i))
            for i in range(5)
        ]}
        payload = {'filters': {
            'supplyChainFilter': {'filters': [dict(attributeName='forLocation', value='Leaf')]},
            'productFilter': {'filters': [dict(attributeName='p1', operator='equalto', value='FG')]},
            'locationFilter': {'filters': [dict(attributeName='l1', operator='equalto', value='Zone')]},
            'availabilityFilter': {'filters': [
                dict(attributeName='norm', operator='greaterthan', value='3'),
                dict(attributeName='virtualnorm', operator='equalto', value='5'),
                dict(attributeName='pic', operator='equalto', value='Green'),
                dict(attributeName='ohic', operator='equalto', value='Black'),
                dict(attributeName='pipo,seasonality', operator='equalto', value='Phase In'),
            ]},
            'customAttributeFilter': {'filters': [
                dict(attributeName='SKULocAttr1', operator='equalto', value='pair-x'),
                dict(attributeName='SKUAttr1', operator='equalto', value='sku-x'),
                dict(attributeName='LocAttr1', operator='equalto', value='loc-x'),
            ]},
        }}
        products, locations = PermissionCodes({'SKU': 2}), PermissionCodes({'LOC': 3})
        run = SimpleNamespace(pk='synthetic', kind='LEGACY_UI_FIXTURE')
        with patch.object(bpr_sql, 'image_query', side_effect=relation), \
             patch.object(bpr_sql, 'scope', return_value=(products, locations)):
            count_query, count_values = bpr_sql._build(
                run, payload, {'SkuAttributeData': sku, 'LocationAttributeData': location},
                None, ancillary, None, True)
            page_query, page_values = bpr_sql._build(
                run, payload, {'SkuAttributeData': sku, 'LocationAttributeData': location},
                None, ancillary, (2, 3), False)

        output = {'ClosingState': [{'importer': {'SkuAttributeData': sku,
                   'LocationAttributeData': location, 'SkuLocAttributeData': pair},
                   'dbm': {'SKULocStandardAttributes': standard}}],
                  'BPRReports': [{'BPR_Table': base, 'vf_RationedReqReport': ration}],
                  'BTRFinal': [{'BufferTrendPhysicalInv': trend}]}
        model = ReadModel(output, ancillary, bounded_page=True)
        predicate = BprPredicate(payload, location)
        def weight(candidate):
            return (permission_multiplicity(products, candidate['SKUCode']) *
                    permission_multiplicity(locations, candidate['WHCode']) * predicate(candidate))
        expected_count = sum(weight(candidate) for candidate in model.joined(count=True))
        candidates = sort_rows([candidate for candidate in model.joined()
                                for _ in range(weight(candidate))])
        expected_page = model.page(candidates, 2, 3)

        with bpr_sql.connection.cursor() as cursor:
            cursor.execute(count_query, count_values)
            actual_count = cursor.fetchone()[0]
            cursor.execute(page_query, page_values)
            names = [column[0] for column in cursor.description]
            actual_page = [dict(zip(names, record)) for record in cursor.fetchall()]
        self.assertEqual(actual_count, expected_count)
        self.assertEqual(actual_page, expected_page)
        self.assertEqual(actual_count, 960)
        self.assertEqual(len(actual_page), 960)
        self.assertIn(None, {record['TechPen'] for record in actual_page})
        self.assertIn(Decimal('7'), {record['TechPen'] for record in actual_page})
        self.assertEqual({record['Remark'] for record in actual_page},
                         {'tie-' + str(i) for i in range(5)})


if __name__ == '__main__':
    unittest.main()
