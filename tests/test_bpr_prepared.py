"""Prepared BPR differential against the independent native Python join bag."""
import os
import unittest
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import bpr_prepared as prepared
from mta.presentation.bpr import ReadModel, sort_rows
from mta.presentation.bpr_filters import BprPredicate
from mta.presentation.bpr_prepared_fields import FIELDS, SOURCES, field_name
from mta.presentation.bpr_sql import _values_cte
from mta.presentation.context import PermissionCodes, PublicationUnavailable
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr_sql import equal, key
from mta.runtime.relational_state import CATALOG, PG_TYPES, quote


class BprPreparedTests(unittest.TestCase):
    def test_hierarchy_opt_in_fails_before_receipt_or_prepared_read(self):
        run = SimpleNamespace(pk='fixture', kind='LEGACY_UI_FIXTURE')
        importer = {'LocationAttributeData': []}
        with patch.object(prepared, '_projected_attributes', return_value=(importer, {'version': 'approved'})), \
             patch('mta.presentation.fixture.binding') as binding, \
             patch.object(prepared, '_build') as build:
            with self.assertRaisesRegex(PublicationUnavailable, 'hierarchy_supplement_not_bound'):
                prepared.read_bpr(run, {}, paging=(1, 3))
            binding.assert_not_called()
            build.assert_not_called()

    def test_invalid_legacy_filter_is_rejected_before_prepared_read(self):
        run = SimpleNamespace(pk='fixture', kind='LEGACY_UI_FIXTURE')
        payload = {'filters': {'availabilityFilter': {'filters': [
            dict(attributeName='category', operator='equalto', value='x')]}}}
        with patch.object(prepared, '_projected_attributes', return_value=({'LocationAttributeData': []}, None)), \
             patch('mta.presentation.fixture.binding') as binding:
            with self.assertRaisesRegex(PublicationUnavailable, 'missing alias b for category'):
                prepared.read_bpr(run, payload, paging=(1, 3))
            binding.assert_not_called()

    def test_reader_rejects_nonfixture_and_invalid_page(self):
        with self.assertRaisesRegex(ValueError, 'requires an admitted source run'):
            prepared.read_bpr(SimpleNamespace(kind='DAILY_CHAIN'), {}, paging=(1, 3))
        run = SimpleNamespace(kind='LEGACY_UI_FIXTURE')
        for paging in ((0, 3), (1, 0), (True, 3), [1, 3], None):
            with self.subTest(paging=paging), self.assertRaisesRegex(ValueError, 'pagination'):
                prepared.read_bpr(run, {}, paging=paging)

    @unittest.skipUnless(os.environ.get('VF_RUN_POSTGRESQL_DIFFERENTIALS') == '1' and
                         prepared.connection.vendor == 'postgresql',
                         'PostgreSQL-only typed native VALUES differential')
    def test_postgresql_prepared_grid_count_analytics_native_bags(self):
        def row(table, **values):
            return {**{name: None for name, _ in CATALOG['tables'][table]}, **values}

        base = [row('BPR/BPR_Table', SKUCode='SKU ', SKUName='Item-' + str(i),
            WhCode='Loc ', WhName='Location', ParentWhCode='Parent ', Stock=9, Norm=4,
            GIT=2, TechColorSequence=1, EcoColorSequence=None, EcoColor='Red',
            Req=None, RationedQTY=None, LeftoverParentStock=None, ResidualSnP=1,
            NormReq=2, BlueReq=3, **{'PhaseIn-Out': i + 1, 'SKULocAttr1': 'display-x'})
            for i in range(2)]
        base += [row('BPR/BPR_Table', SKUCode='NO-S', SKUName='Unmatched standard',
                     WhCode='ALT', ParentWhCode='Parent', Stock=3, Norm=1, GIT=0),
                 row('BPR/BPR_Table', SKUCode='LOST', SKUName='Unmatched dimensions',
                     WhCode='Z', Stock=0, Norm=0, GIT=0),
                 row('BPR/BPR_Table', SKUCode=None, SKUName='NULL key', WhCode='Z')]
        ration = [row('BPR/vf_RationedReqReport', SKUCode='sku', WhCode='LOC',
                     VirtualNorm=5, PhysicalInventoryColorSequence=sequence,
                     PhysicalInventoryPen=pen, DispatchPen=dispatch,
                     PhysicalInventoryColor=color, DispatchColor='Green')
                  for sequence, pen, dispatch, color in (
                      (None, Decimal('-99999999.00'), Decimal('-99999999.00'), 'Black'),
                      (None, Decimal('7.123456789012345678901'), Decimal('8.02'), 'Unknown'),
                      (1, None, None, 'Blue'))]
        standard = [row('Importer/SKULocStandardAttributes', SKUCode='SKU', WhCode='loc', Tags=tag)
                    for tag in (None, 'Phase In')]
        sku = [row('Importer/SkuAttributeData', SKUCode='sku ', SL1='FG', c1='sku-' + str(i))
               for i in range(2)]
        sku += [row('Importer/SkuAttributeData', SKUCode='NO-S', SL1='FG')]
        location = [row('Importer/LocationAttributeData', WHCode='LOC', LocationType='Leaf',
                        LL1='Zone', c1='loc-' + str(i)) for i in range(2)]
        location += [row('Importer/LocationAttributeData', WHCode='parent', LocationType='Parent')
                     for _ in range(2)]
        location += [row('Importer/LocationAttributeData', WHCode='ALT', LocationType='Leaf', LL1='Zone')]
        pair = [row('Importer/SkuLocAttributeData', SKUCode='SKU', LocCode='loc ', c1=value)
                for value in ('pair-x', 'pair-y')]
        trend = [row('BTR/BufferTrendPhysicalInv', SKUCode='sku', WhCode='LOC',
                     Availability_01_30=Decimal(str(i))) for i in (1, 2)]
        images = {
            SOURCES['A']: ('BPR/BPR_Table', base),
            SOURCES['V']: ('BPR/vf_RationedReqReport', ration),
            SOURCES['S']: ('Importer/SKULocStandardAttributes', standard),
            SOURCES['C']: ('Importer/SkuAttributeData', sku),
            SOURCES['D']: ('Importer/LocationAttributeData', location),
            SOURCES['B']: ('Importer/SkuLocAttributeData', pair),
            'closing/btr/BufferTrendPhysicalInv': ('BTR/BufferTrendPhysicalInv', trend),
        }

        def relation(_run, path):
            table, rows = images[path]
            columns = ('vf_ordinal',) + tuple(name for name, _ in CATALOG['tables'][table])
            casts = {'vf_ordinal': '::bigint', **{
                name: '::' + PG_TYPES[kind] for name, kind in CATALOG['tables'][table]}}
            return _values_cte([dict(vf_ordinal=i, **record) for i, record in enumerate(rows)], columns, casts)

        def prepared_relation(run):
            # Derive typed prepared occurrences with native SQL joins. Expected
            # results below come from ReadModel and never supply prepared rows.
            ctes, params = [], []
            for owner, path in SOURCES.items():
                sql, values = relation(run, path)
                ctes.append(owner + ' AS (' + sql + ')')
                params.extend(values)
            source_order = ','.join(owner + '.vf_ordinal' for owner in SOURCES)
            fields = ['row_number() OVER (ORDER BY ' + source_order + ')-1 AS ordinal',
                      key('A."SKUCode"') + ' AS sku_key', key('A."WhCode"') + ' AS location_key']
            fields += [owner + '.vf_ordinal AS ' + owner.lower() + '_ordinal' for owner in SOURCES]
            fields += [owner + '.' + quote(name) + ' AS ' + quote(field_name(owner, name))
                       for owner, mapping in FIELDS.items() for name in mapping]
            joins = ' FROM A'
            for owner, sku_column, location_column in (
                    ('V', 'SKUCode', 'WhCode'), ('S', 'SKUCode', 'WhCode'),
                    ('C', 'SKUCode', None), ('D', None, 'WHCode'), ('B', 'SKUCode', 'LocCode')):
                conditions = []
                if sku_column:
                    conditions.append(equal('A."SKUCode"', owner + '.' + quote(sku_column)))
                if location_column:
                    conditions.append(equal('A."WhCode"', owner + '.' + quote(location_column)))
                joins += ' LEFT JOIN ' + owner + ' ON ' + ' AND '.join(conditions)
            return 'WITH ' + ','.join(ctes) + ' SELECT ' + ','.join(fields) + joins, params

        tied = datetime(2026, 4, 7, 1)
        ancillary = {'InTransitData': [], 'BPRReport_RemarkDetails': [
            dict(SKUCode='SKU', WhCode='loc ', RemarkDate=tied, Remark='tie-' + str(i)) for i in range(2)] + [
            dict(SKUCode='sku ', WhCode='LOC', RemarkDate=datetime(2026, 4, 6), Remark='old'),
            dict(SKUCode='SKU', WhCode='LOC', RemarkDate=None, Remark='NULL date')]}
        importer = {'SkuAttributeData': sku, 'LocationAttributeData': location, 'SkuLocAttributeData': pair}
        output = {'ClosingState': [{'importer': importer, 'dbm': {'SKULocStandardAttributes': standard}}],
                  'BPRReports': [{'BPR_Table': base, 'vf_RationedReqReport': ration}],
                  'BTRFinal': [{'BufferTrendPhysicalInv': trend}]}
        model = ReadModel(output, ancillary, bounded_page=True)
        # Native scope lookup carries the base's original codes. Source joins
        # still exercise independently normalized mixed-case/padded identities.
        products = PermissionCodes({'SKU ': 2, 'NO-S': 1, 'LOST': 1})
        locations = PermissionCodes({'Loc ': 3, 'ALT': 1, 'Z': 1})
        filtered = {'filters': {
            'supplyChainFilter': {'filters': [dict(attributeName='forChildren', value='Parent')]},
            'productFilter': {'filters': [dict(attributeName='p1', operator='equalto', value='FG')]},
            'locationFilter': {'filters': [dict(attributeName='l1', operator='equalto', value='Zone')]},
            'availabilityFilter': {'filters': [
                dict(attributeName='norm', operator='greaterthan', value='3'),
                dict(attributeName='virtualnorm', operator='equalto', value='5'),
                dict(attributeName='pic', operator='equalto', value='Green')]},
            'customAttributeFilter': {'filters': [
                dict(attributeName='SKULocAttr1', operator='equalto', value='pair-x'),
                dict(attributeName='SKUAttr1', operator='equalto', value='sku-0'),
                dict(attributeName='LocAttr1', operator='equalto', value='loc-0')]},
        }}
        cases = [('first', {}, (1, 3)), ('second', {}, (2, 3)),
                 ('boundary', {}, (129, 3)), ('beyond', {}, (1000, 3)),
                 ('raw-owner-parent', filtered, (2, 3)),
                 ('unmatched-standard', {'filters': {'productFilter': {'filters': [
                     dict(attributeName='sku', value='NO-S')]}}}, (1, 3)),
                 ('tag-filter', {'filters': {'availabilityFilter': {'filters': [
                     dict(attributeName='pipo,seasonality', value='Phase In')]}}}, (1, 3))]
        run = SimpleNamespace(pk='synthetic', kind='LEGACY_UI_FIXTURE')
        with patch.object(prepared, '_prepared_query', side_effect=prepared_relation), \
             patch.object(prepared, 'image_query', side_effect=relation), \
             patch.object(prepared, 'scope', return_value=(products, locations)):
            for name, payload, paging in cases:
                with self.subTest(case=name):
                    predicate = BprPredicate(payload, location)
                    def weight(candidate):
                        return (permission_multiplicity(products, candidate['SKUCode']) *
                                permission_multiplicity(locations, candidate['WHCode']) * predicate(candidate))
                    candidates = sort_rows([candidate for candidate in model.joined()
                                            for _ in range(weight(candidate))])
                    expected_count = sum(weight(candidate) for candidate in model.joined(count=True))
                    expected_page = model.page(candidates, *paging)
                    expected_analytics = model.analytics(candidates)
                    actual = {}
                    for mode in ('grid', 'count', 'analytics'):
                        query, values = prepared._build(run, payload, importer, ancillary, paging,
                            count=mode == 'count', analytics=mode == 'analytics')
                        with prepared.connection.cursor() as cursor:
                            cursor.execute(query, values)
                            if mode == 'count':
                                actual[mode] = cursor.fetchone()[0]
                            else:
                                names = [entry[0] for entry in cursor.description]
                                actual[mode] = [dict(zip(names, record)) for record in cursor.fetchall()]
                    self.assertEqual(actual['grid'], expected_page)
                    self.assertEqual(actual['count'], expected_count)
                    self.assertEqual(actual['analytics'], expected_analytics)
                    if name == 'first':
                        self.assertGreater(actual['count'], 0)
                        self.assertIn(None, {record['tags'] for record in actual['grid']})
                        self.assertIn(None, {record['TechPen'] for record in actual['grid']})
                        self.assertIn(Decimal('7.123456789012345678901'),
                                      {record['TechPen'] for record in actual['grid']})
                        self.assertEqual({record['Remark'] for record in actual['grid']}, {'tie-0', 'tie-1'})
                    if name == 'raw-owner-parent':
                        self.assertTrue(actual['grid'])
                        self.assertEqual({record['SKULocAttr1'] for record in actual['grid']}, {'display-x'})
                    if name == 'unmatched-standard':
                        self.assertTrue(actual['grid'])
                        self.assertEqual(actual['count'], 0)
                    if name == 'beyond':
                        self.assertEqual(actual['grid'], [])


if __name__ == '__main__':
    unittest.main()
