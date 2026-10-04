"""Differential proofs for occurrence-preserving insight lookup indexes."""
from itertools import product
import unittest

from mta.presentation import insights


def old_joined_rows(btr, dbm, kind, *, filter_owners=False):
    """Tiny frozen reconstruction of the pre-index nested lookup loops."""
    table = ('ChronicUnavalabilityData' if kind.startswith('chronic')
             else 'DBMNormSuggestionsData')
    result = []
    for row in btr[table]:
        sku, loc = insights._key(row)
        populations = [
            [r for r in btr['SkuAttributeData'] if r['SKUCode'] == sku],
            [r for r in btr['LocationAttributeData'] if r['WHCode'] == loc],
            [r for r in btr['SkuLocAttributeData']
             if insights._key(r) == (sku, loc)] or [{}],
        ]
        if kind.endswith('loc'):
            populations.append(
                [r for r in btr['SiteDescriptionTbl'] if r['WHCode'] == loc])
        elif kind.endswith('sku'):
            populations.append(
                [r for r in btr['SKUDescriptionTbl'] if r['SKUCode'] == sku])
        else:
            populations.append([{}])
        populations.append(
            [r for r in dbm['DBMMaster'] if insights._key(r) == (sku, loc)]
            if table == 'DBMNormSuggestionsData' else [{}])
        for sa, la, sla, description, master in product(*populations):
            value = {**row, 'WHCode': loc,
                     'ParentWhCode': master.get(
                         'ParentWhCode', row.get('ParentWhCode')),
                     '_sku': sa, '_loc': la, '_description': description}
            value.update({f'SKUAttribute{i}': sa.get(f'c{i}')
                          for i in range(1, 16)})
            value.update({f'LocAttribute{i}': la.get(f'c{i}')
                          for i in range(1, 16)})
            value.update({f'SkuLocAttribute{i}': sla.get(f'c{i}')
                          for i in range(1, 16)})
            value.update({k: v for k, v in sa.items()
                          if not k.startswith('c')})
            value.update({k: v for k, v in la.items()
                          if not k.startswith('c')})
            if filter_owners:
                value.update(_a=row, _location=la, _pair=sla,
                             _master=master)
            result.append(value)
    return result


def old_chronic_grid(btr, nms, *, filter_owners=False):
    """Tiny frozen reconstruction of the pre-index chronic grid loops."""
    result = []
    for row in btr['ChronicUnavalabilityData']:
        populations = (
            [r for r in nms if insights._key(r) == insights._key(row)] or [{}],
            [r for r in btr['LocationAttributeData']
             if r['WHCode'] == insights._key(row)[1]] or [{}],
            [r for r in btr['SkuAttributeData']
             if r['SKUCode'] == row['SKUCode']] or [{}],
            [r for r in btr['SkuLocAttributeData']
             if insights._key(r) == insights._key(row)] or [{}],
        )
        for n, la, sa, sla in product(*populations):
            result.append({
                'SKUCode': row['SKUCode'], 'WHCode': insights._key(row)[1],
                'skucode': row['SKUCode'],
                'skudesc': n.get('SKUDescription'),
                'location': insights._key(row)[1],
                'parentloc': row['ParentWhCode'], 'RLT': row['RLT'],
                'BlackRedAgeing': row['BRAge'],
                'PhysicalInventoryPen': row['PhysicalInventoryPen'],
                'Techcolor': row['PhysicalInventoryColor'],
                'PipelineInventoryPen': row['PipelineInventoryPen'],
                'ecocolor': row['PipelineInventoryColor'],
                'RationedStockatparent': row['RationedQty'],
            })
            if filter_owners:
                result[-1].update(_a=row, _sku=sa, _location=la,
                                  _pair=sla, _description=n)
    return result


def insight_row(sku, loc, marker):
    return {
        'SKUCode': sku, 'WhCode': loc, 'ParentWhCode': f'parent-{marker}',
        'RLT': 2, 'BRAge': 3, 'PhysicalInventoryPen': marker,
        'PhysicalInventoryColor': 'Red', 'PipelineInventoryPen': marker,
        'PipelineInventoryColor': 'Green', 'RationedQty': marker,
        'Suggestion': 'Increase', 'SuggestionGenerationAge': 2,
    }


class CountingList(list):
    def __init__(self, values):
        super().__init__(values)
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        return super().__iter__()


class InsightLookupIndexTests(unittest.TestCase):
    def setUp(self):
        keys = [('SKU', 'LOC'), ('sku', 'loc'), (None, None)]
        self.btr = {
            'ChronicUnavalabilityData': [
                insight_row('SKU', 'LOC', 'chronic-a'),
                insight_row(None, None, 'chronic-null'),
            ],
            'DBMNormSuggestionsData': [
                insight_row('SKU', 'LOC', 'dbm-a'),
                insight_row('sku', 'loc', 'dbm-case'),
                insight_row(None, None, 'dbm-null'),
            ],
            'SkuAttributeData': [
                {'SKUCode': sku, 'c1': f'sku-{index}', 'ordinal': index}
                for index, (sku, _) in enumerate(keys + [('SKU', 'LOC')])
            ],
            'LocationAttributeData': [
                {'WHCode': loc, 'c1': f'loc-{index}', 'ordinal': index}
                for index, (_, loc) in enumerate(keys + [('SKU', 'LOC')])
            ],
            'SkuLocAttributeData': [
                {'SKUCode': sku, 'LocCode': loc, 'c1': f'pair-{index}'}
                for index, (sku, loc) in enumerate(keys + [('SKU', 'LOC')])
            ],
            'SiteDescriptionTbl': [
                {'WHCode': loc, 'WHDescription': f'location-{index}'}
                for index, (_, loc) in enumerate(keys + [('SKU', 'LOC')])
            ],
            'SKUDescriptionTbl': [
                {'SKUCode': sku, 'SKUDescription': f'product-{index}'}
                for index, (sku, _) in enumerate(keys + [('SKU', 'LOC')])
            ],
        }
        self.dbm = {'DBMMaster': [
            {'SKUCode': sku, 'LocCode': loc, 'ParentWhCode': f'master-{index}'}
            for index, (sku, loc) in enumerate(keys + [('SKU', 'LOC')])
        ]}
        self.nms = [
            {'SKUCode': sku, 'LocCode': loc,
             'SKUDescription': f'nms-{index}'}
            for index, (sku, loc) in enumerate(keys + [('SKU', 'LOC')])
        ]

    def test_joined_rows_matches_nested_loops_for_all_projection_shapes(self):
        for filter_owners in (False, True):
            for kind in ('chronic-loc', 'chronic-sku', 'loc', 'sku',
                         'pie', 'ageing'):
                with self.subTest(kind=kind, filter_owners=filter_owners):
                    self.assertEqual(
                        insights.joined_rows(
                            self.btr, self.dbm, kind,
                            filter_owners=filter_owners),
                        old_joined_rows(
                            self.btr, self.dbm, kind,
                            filter_owners=filter_owners))

    def test_chronic_grid_matches_nested_loops_with_fallbacks_and_duplicates(self):
        missing = insight_row('MISSING', 'missing', 'missing')
        self.btr['ChronicUnavalabilityData'].append(missing)
        for filter_owners in (False, True):
            with self.subTest(filter_owners=filter_owners):
                self.assertEqual(
                    insights.chronic_grid(
                        self.btr, self.nms, filter_owners=filter_owners),
                    old_chronic_grid(
                        self.btr, self.nms, filter_owners=filter_owners))

    def test_lookup_sources_are_each_traversed_once_per_projection(self):
        joined_sources = ('SkuAttributeData', 'LocationAttributeData',
                          'SkuLocAttributeData', 'SiteDescriptionTbl')
        for name in joined_sources:
            self.btr[name] = CountingList(self.btr[name])
        self.dbm['DBMMaster'] = CountingList(self.dbm['DBMMaster'])
        insights.joined_rows(self.btr, self.dbm, 'loc')
        self.assertEqual(
            [self.btr[name].iterations for name in joined_sources],
            [1, 1, 1, 1])
        self.assertEqual(self.dbm['DBMMaster'].iterations, 1)

        grid_sources = ('SkuAttributeData', 'LocationAttributeData',
                        'SkuLocAttributeData')
        for name in grid_sources:
            self.btr[name].iterations = 0
        counted_nms = CountingList(self.nms)
        insights.chronic_grid(self.btr, counted_nms)
        self.assertEqual(
            [self.btr[name].iterations for name in grid_sources],
            [1, 1, 1])
        self.assertEqual(counted_nms.iterations, 1)


if __name__ == '__main__':
    unittest.main()
