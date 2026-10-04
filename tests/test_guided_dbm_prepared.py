"""Focused daily Guided DBM prepared occurrence and SQL-reader differential."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import guided_dbm, insights
from mta.presentation.bpr_sql import _values_cte
from mta.presentation.guided_dbm_fields import FIELDS, field_name
from mta.presentation.insight_filters import InsightPredicate
from mta.presentation.permissions import PermissionCodes, permission_multiplicity
from mta.runtime.management.commands.prepare_guided_dbm_fixture import raw_equal
from mta.runtime.relational_state import quote


class GuidedDbmPreparedTests(unittest.TestCase):
    def test_reader_requires_fixture_and_explicit_trial_switch(self):
        with self.assertRaisesRegex(ValueError, 'fixture-only'):
            guided_dbm.read_guided_dbm(SimpleNamespace(kind='DAILY_CHAIN'), {}, 'pie', {})
        run = SimpleNamespace(kind='LEGACY_UI_FIXTURE')
        with patch.object(guided_dbm.settings, 'VF_GUIDED_PREPARED', False, create=True):
            with self.assertRaisesRegex(Exception, 'trial_disabled'):
                guided_dbm.read_guided_dbm(run, {}, 'pie', {})

    def test_raw_join_expression_distinguishes_null_from_empty(self):
        expression = raw_equal('left_value', 'right_value')
        self.assertIn('(left_value IS NULL)=(right_value IS NULL)', expression)
        self.assertIn("COALESCE(left_value,'')=COALESCE(right_value,'')", expression)

    @unittest.skipUnless(os.environ.get('VF_RUN_POSTGRESQL_DIFFERENTIALS') == '1' and
                         guided_dbm.connection.vendor == 'postgresql',
                         'PostgreSQL-only typed Guided DBM differential')
    def test_all_four_readers_match_native_python_bags(self):
        def complete(owner, **values):
            return {**{name: None for name in FIELDS[owner]}, **values}

        suggestions = [
            complete('A', SKUCode='S1', WhCode='L1', Suggestion='Increase', SuggestionGenerationAge=1),
            complete('A', SKUCode='S1', WhCode='L1', Suggestion='Decrease', SuggestionGenerationAge=3),
            complete('A', SKUCode=None, WhCode=None, Suggestion=None, SuggestionGenerationAge=5),
            complete('A', SKUCode='S2', WhCode='L2', Suggestion='No Suggestion', SuggestionGenerationAge=7),
        ]
        skus = [
            complete('S', SKUCode='S1', ElephantOrderCapping=1, Weight='9.00',
                     SL1='P', c1='z'),
            complete('S', SKUCode='S1', ElephantOrderCapping=2, Weight='10.00',
                     SL1='P', c1='a'),
            complete('S', SKUCode=None, SL1='NULL', c1='null-sku'),
            complete('S', SKUCode='S2', SL1='Q'),
        ]
        locations = [
            complete('L', WHCode='L1', LocationType='Leaf', LogisticsLocation='Z', LL1='X', c1='b'),
            complete('L', WHCode='L1', LocationType='Leaf', LogisticsLocation='A', LL1='X', c1='y'),
            complete('L', WHCode=None, LocationType='NullLeaf', LL1='N', c1='null-loc'),
            complete('L', WHCode='L2', LocationType='Leaf', LL1='Y'),
            complete('L', WHCode='PARENT', LocationType='Parent'),
            complete('L', WHCode='PARENT', LocationType='Parent'),
        ]
        pairs = [complete('P', SKUCode='S1', LocCode='L1', c1='pair-a'),
                 complete('P', SKUCode='S1', LocCode='L1', c1='pair-b')]
        masters = [complete('M', SKUCode='S1', WhCode='L1', Norm=10, ParentWhCode='PARENT'),
                   complete('M', SKUCode='S1', WhCode='L1', Norm=11, ParentWhCode='PARENT'),
                   complete('M', SKUCode=None, WhCode=None, Norm=3, ParentWhCode=None),
                   complete('M', SKUCode='S2', WhCode='L2', Norm=4, ParentWhCode='PARENT')]
        site_descriptions = [dict(WHCode='L1', WHDescription='Zulu'),
                             dict(WHCode='L1', WHDescription='Alpha'),
                             dict(WHCode=None, WHDescription='Null site')]
        sku_descriptions = [dict(SKUCode='S1', SKUDescription='Zulu SKU'),
                            dict(SKUCode='S1', SKUDescription='Alpha SKU'),
                            dict(SKUCode=None, SKUDescription='Null SKU')]
        state = dict(DBMNormSuggestionsData=suggestions, SkuAttributeData=skus,
                     LocationAttributeData=locations, SkuLocAttributeData=pairs,
                     SiteDescriptionTbl=site_descriptions, SKUDescriptionTbl=sku_descriptions)
        dbm = {'DBMMaster': masters}

        def values_relation(rows, fields, casts=None):
            return _values_cte([dict(vf_ordinal=i, **row) for i, row in enumerate(rows)],
                               ('vf_ordinal',) + tuple(fields),
                               {'vf_ordinal': '::bigint', **(casts or {})})

        relations = {}
        for owner, rows in (('A', suggestions), ('S', skus), ('L', locations),
                            ('P', pairs), ('M', masters)):
            casts = {name: '::' + {'text': 'text', 'bigint': 'bigint'}[kind]
                     for name, kind in FIELDS[owner].items()}
            relations[owner] = values_relation(rows, FIELDS[owner], casts)
        ctes, relation_params = [], []
        for owner in ('A', 'S', 'L', 'P', 'M'):
            query, values = relations[owner]
            ctes.append(owner + ' AS (' + query + ')')
            relation_params.extend(values)
        selected = ['row_number() OVER (ORDER BY A.vf_ordinal,S.vf_ordinal,L.vf_ordinal,'
                    'P.vf_ordinal NULLS FIRST,M.vf_ordinal)-1 AS ordinal']
        selected += [owner + '.vf_ordinal AS ' + owner.lower() + '_ordinal'
                     for owner in ('A', 'S', 'L', 'P', 'M')]
        selected += [owner + '.' + quote(name) + ' AS ' + quote(field_name(owner, name))
                     for owner in ('A', 'S', 'L', 'P', 'M') for name in FIELDS[owner]]
        joins = (' FROM A JOIN S ON ' + raw_equal('A."SKUCode"', 'S."SKUCode"') +
                 ' JOIN L ON ' + raw_equal('A."WhCode"', 'L."WHCode"') +
                 ' LEFT JOIN P ON ' + raw_equal('A."SKUCode"', 'P."SKUCode"') + ' AND ' +
                 raw_equal('A."WhCode"', 'P."LocCode"') +
                 ' JOIN M ON ' + raw_equal('A."SKUCode"', 'M."SKUCode"') + ' AND ' +
                 raw_equal('A."WhCode"', 'M."WhCode"'))
        prepared_relation = 'WITH ' + ','.join(ctes) + ' SELECT ' + ','.join(selected) + joins

        def image(_run, path):
            if path.endswith('SiteDescriptionTbl'):
                return values_relation(site_descriptions, ('WHCode', 'WHDescription'),
                    {'WHCode': '::text', 'WHDescription': '::text'})
            if path.endswith('SKUDescriptionTbl'):
                return values_relation(sku_descriptions, ('SKUCode', 'SKUDescription'),
                    {'SKUCode': '::text', 'SKUDescription': '::text'})
            if path.endswith('LocationAttributeData'):
                return relations['L']
            raise AssertionError(path)

        products = PermissionCodes({'S1': 2, None: 1, 'S2': 1})
        allowed_locations = PermissionCodes({'L1': 1, None: 2, 'L2': 1})
        run = SimpleNamespace(pk='00000000-0000-0000-0000-000000000001')
        cases = [
            ('all', {}),
            ('raw-custom-parent', {'supplyChainFilter': {'filters': [
                dict(attributeName='forChildren', value='Parent')]},
                'customAttributeFilter': {'filters': [
                    dict(attributeName='SKUAttr1', operator='equalto', value='z'),
                    dict(attributeName='LocAttr1', operator='equalto', value='b'),
                    dict(attributeName='SKULocAttr1', operator='equalto', value='pair-a')]}}),
            ('native-operators', {'productFilter': {'filters': [
                dict(attributeName='p1', operator='startswith', value='P')]},
                'availabilityFilter': {'filters': [
                    dict(attributeName='norm', operator='notequalto', value='10')]}}),
        ]
        with patch.object(guided_dbm, '_prepared_query', return_value=(prepared_relation, relation_params)), \
             patch.object(guided_dbm, 'image_query', side_effect=image), \
             patch.object(guided_dbm, 'scope', return_value=(products, allowed_locations)):
            for case, payload in cases:
                for kind in ('loc', 'sku', 'pie', 'ageing'):
                    with self.subTest(case=case, kind=kind):
                        native = insights.joined_rows(state, dbm, kind, filter_owners=True)
                        predicate = InsightPredicate(payload, locations, kind=kind)
                        selected_rows = []
                        for row in native:
                            weight = (permission_multiplicity(products, row['SKUCode']) *
                                      permission_multiplicity(allowed_locations, row['WHCode']) *
                                      predicate(row))
                            selected_rows.extend(dict(row) for _ in range(weight))
                        expected = insights.project(selected_rows, kind)
                        query, params = guided_dbm.build_query(run, payload, kind,
                            {'SkuAttributeData': skus, 'LocationAttributeData': locations})
                        with guided_dbm.connection.cursor() as cursor:
                            cursor.execute(query, params)
                            names = [entry[0] for entry in cursor.description]
                            actual = [{name: value for name, value in zip(names, record)
                                       if name != 'first_ordinal' and value is not None}
                                      for record in cursor.fetchall()]
                        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
