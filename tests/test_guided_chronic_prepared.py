"""Focused prepared Chronic grid reader differential."""
import os
import unittest
from collections import defaultdict
from itertools import product
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import guided_chronic, insights
from mta.presentation.bpr_sql import _values_cte
from mta.presentation.guided_chronic_fields import OUTPUTS
from mta.presentation.insight_filters import InsightPredicate
from mta.presentation.permissions import PermissionCodes, permission_multiplicity
from mta.runtime.relational_state import CATALOG


class GuidedChronicPreparedTests(unittest.TestCase):
    def test_broad_query_does_not_rejoin_source_bags(self):
        attributes = {'SkuAttributeData': [], 'LocationAttributeData': []}
        with patch.object(guided_chronic, 'scope', return_value=(PermissionCodes({'S': 1}),
                                                                 PermissionCodes({'L': 1}))), \
             patch.object(guided_chronic, '_prepared_query', return_value=('SELECT 1 WHERE FALSE', [])), \
             patch.object(guided_chronic, 'image_query') as image:
            query, _, _ = guided_chronic.build_query(SimpleNamespace(pk='x'), {}, attributes)
        image.assert_not_called()
        self.assertNotIn(' LEFT JOIN A ', query)
        self.assertNotIn(' LEFT JOIN N ', query)
        self.assertNotIn(' LEFT JOIN S ', query)
        self.assertNotIn(' LEFT JOIN L ', query)
        self.assertNotIn(' LEFT JOIN P ', query)

    @unittest.skipUnless(os.environ.get('VF_RUN_POSTGRESQL_DIFFERENTIALS') == '1' and
                         guided_chronic.connection.vendor == 'postgresql',
                         'PostgreSQL-only typed Chronic grid differential')
    def test_broad_and_filtered_occurrences_match_native_grid(self):
        def row(table, **values):
            return {**{name: None for name, _ in CATALOG['tables'][table]}, **values}
        chronic = [row('BTR/ChronicUnavalabilityData', SKUCode='S1', WhCode='L1',
            ParentWhCode='PARENT', RLT=3, BRAge=4, PhysicalInventoryPen='1.25',
            PhysicalInventoryColor='Black', PipelineInventoryPen='2.50',
            PipelineInventoryColor='Red', RationedQty=7),
            row('BTR/ChronicUnavalabilityData', SKUCode=None, WhCode=None,
                ParentWhCode=None, RLT=None, BRAge=None)]
        nms = [row('Importer/NMSAllItems', SKUCode='S1', WhCode='L1', SKUDescription=value)
               for value in ('Desc A', 'Desc B')]
        locations = [row('BTR/LocationAttributeData', WHCode='L1', LocationType='Leaf', c1=value)
                     for value in ('loc-a', 'loc-b')]
        locations += [row('BTR/LocationAttributeData', WHCode='PARENT', LocationType='Parent')
                      for _ in range(2)]
        locations += [row('BTR/LocationAttributeData', WHCode=None, LocationType='Null', c1='null-loc')]
        skus = [row('BTR/SkuAttributeData', SKUCode='S1', c1=value) for value in ('sku-a', 'sku-b')]
        skus += [row('BTR/SkuAttributeData', SKUCode=None, c1='null-sku')]
        pairs = [row('BTR/SkuLocAttributeData', SKUCode='S1', LocCode='L1', c1=value)
                 for value in ('pair-a', 'pair-b')]

        def index(rows, key):
            result = defaultdict(list)
            for ordinal, value in enumerate(rows): result[key(value)].append((ordinal, value))
            return result
        by_n = index(nms, lambda value: (value['SKUCode'], value['WhCode']))
        by_l = index(locations, lambda value: value['WHCode'])
        by_s = index(skus, lambda value: value['SKUCode'])
        by_p = index(pairs, lambda value: (value['SKUCode'], value['LocCode']))
        prepared = []
        for a_ordinal, a in enumerate(chronic):
            key = (a['SKUCode'], a['WhCode'])
            populations = (by_n.get(key, [(None, {})]), by_l.get(a['WhCode'], [(None, {})]),
                           by_s.get(a['SKUCode'], [(None, {})]), by_p.get(key, [(None, {})]))
            for (n_ordinal, n), (l_ordinal, _), (s_ordinal, _), (p_ordinal, _) in product(*populations):
                prepared.append(dict(ordinal=len(prepared), a_ordinal=a_ordinal, n_ordinal=n_ordinal,
                    l_ordinal=l_ordinal, s_ordinal=s_ordinal, p_ordinal=p_ordinal,
                    skucode=a['SKUCode'], skudesc=n.get('SKUDescription'), location=a['WhCode'],
                    parentloc=a['ParentWhCode'], RLT=a['RLT'], BlackRedAgeing=a['BRAge'],
                    PhysicalInventoryPen=a['PhysicalInventoryPen'], Techcolor=a['PhysicalInventoryColor'],
                    PipelineInventoryPen=a['PipelineInventoryPen'], ecocolor=a['PipelineInventoryColor'],
                    RationedStockatparent=a['RationedQty']))
        prepared_fields = ('ordinal','a_ordinal','n_ordinal','l_ordinal','s_ordinal','p_ordinal',*OUTPUTS)
        prepared_query = _values_cte(prepared, prepared_fields, {
            **{name: '::bigint' for name in ('ordinal','a_ordinal','n_ordinal','l_ordinal','s_ordinal','p_ordinal')},
            **{name: '::' + ('bigint' if kind == 'bigint' else 'text') for name, kind in OUTPUTS.items()}})
        sources = {'_a': ('BTR/ChronicUnavalabilityData', chronic),
                   '_description': ('Importer/NMSAllItems', nms),
                   '_location': ('BTR/LocationAttributeData', locations),
                   '_sku': ('BTR/SkuAttributeData', skus), '_pair': ('BTR/SkuLocAttributeData', pairs)}
        def source_for_path(path):
            owner = next(owner for owner, configured in {
                '_a':'closing/btr/ChronicUnavalabilityData','_description':'closing/consumer_context/NMSAllItems',
                '_location':'closing/btr/LocationAttributeData','_sku':'closing/btr/SkuAttributeData',
                '_pair':'closing/btr/SkuLocAttributeData'}.items() if configured == path)
            table, rows = sources[owner]; fields = CATALOG['tables'][table]
            values = [dict(vf_ordinal=index, **record) for index, record in enumerate(rows)]
            casts = {'vf_ordinal':'::bigint', **{name:'::' + {'int':'bigint','bigint':'bigint','bit':'boolean',
                'date':'date','datetime':'timestamp','decimal':'numeric','numeric':'numeric','float':'double precision',
                'real':'double precision','nchar':'text','nvarchar':'text','varchar':'text','xml':'text'}[kind]
                for name, kind in fields}}
            return _values_cte(values, ('vf_ordinal', *[name for name, _ in fields]), casts), \
                   [(name, name, 'int' if kind in ('int','bigint') else 'bool' if kind == 'bit' else 'str')
                    for name, kind in fields]
        def metadata(_run, path):
            (_, fields) = source_for_path(path)
            return {'fields': fields}
        def image(_run, path): return source_for_path(path)[0]

        products = PermissionCodes({'S1': 2, None: 1}); allowed_locations = PermissionCodes({'L1': 1, None: 1})
        state = dict(ChronicUnavalabilityData=chronic, SkuAttributeData=skus,
                     LocationAttributeData=locations, SkuLocAttributeData=pairs)
        payloads = [{}, {'filters': {
            'supplyChainFilter': {'filters': [dict(attributeName='forChildren', value='Parent')]},
            'customAttributeFilter': {'filters': [
                dict(attributeName='SKUAttr1', operator='equalto', value='sku-a'),
                dict(attributeName='LocAttr1', operator='equalto', value='loc-a'),
                dict(attributeName='SKULocAttr1', operator='equalto', value='pair-a')]}}},
            {'filters': {'productFilter': {'filters': [
                dict(attributeName='SKU', value='S1')]}}}]
        run = SimpleNamespace(pk='00000000-0000-0000-0000-000000000001')
        with patch.object(guided_chronic, '_prepared_query', return_value=prepared_query), \
             patch.object(guided_chronic, 'image_metadata', side_effect=metadata), \
             patch.object(guided_chronic, 'image_query', side_effect=image), \
             patch.object(guided_chronic, 'scope', return_value=(products, allowed_locations)):
            for payload in payloads:
                with self.subTest(payload=bool(payload)):
                    native = insights.chronic_grid(state, nms, filter_owners=True)
                    predicate = InsightPredicate(payload, locations, kind='chronic-grid')
                    expected = []
                    for item in native:
                        copies = (permission_multiplicity(products, item['SKUCode']) *
                                  permission_multiplicity(allowed_locations, item['WHCode']) * predicate(item))
                        value = {key: value for key, value in item.items()
                                 if key not in ('SKUCode','WHCode') and not key.startswith('_')
                                 and value is not None}
                        for field in ('PhysicalInventoryPen','PipelineInventoryPen'):
                            if field in value: value[field] = float(value[field])
                        expected.extend(dict(value) for _ in range(copies))
                    query, params, outputs = guided_chronic.build_query(run, payload,
                        {'SkuAttributeData': skus, 'LocationAttributeData': locations})
                    with guided_chronic.connection.cursor() as cursor:
                        cursor.execute(query, params); records = cursor.fetchall()
                    actual = []
                    for record in records:
                        item = {name: value for (name, _), value in zip(outputs, record) if value is not None}
                        for field in ('PhysicalInventoryPen','PipelineInventoryPen'):
                            if field in item: item[field] = float(item[field])
                        copies = item.pop('_copies', 1); actual.extend(dict(item) for _ in range(copies))
                    self.assertEqual(actual, expected)


if __name__ == '__main__': unittest.main()
