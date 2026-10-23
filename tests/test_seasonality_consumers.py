"""Focused consumer contracts; mocked publications are not actual-day proof."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.application.r1_seasonality import SEASON_FIELDS
from mta.mdm import season_current as current


class SeasonConsumerTests(unittest.TestCase):
    def setUp(self):
        self.season = dict.fromkeys(SEASON_FIELDS)
        self.season.update(SKUCode='6120', WhCode='DP010290', OrigNorm=186, Status=23)
        self.images = {
            'closing/dbm/DBMMaster': [dict(SKUCode='6120', WhCode='DP010290', RLT=6, Norm=201)],
            'closing/dbm/SKUDescriptionTbl': [dict(SKUCode='6120', SKUDescription='DBM product')],
            'closing/dbm/SiteDescriptionTbl': [dict(WHCode='DP010290', WHDescription='DBM site')],
        }

    def test_task_description_owner_and_duplicate_grain(self):
        importer = ([dict(SKUCode='6120', SKUDescription='Importer product')] * 2,
                    [dict(WHCode='DP010290', WHDescription='Importer site')] * 3)
        with patch.object(current, 'consumer_rows', side_effect=lambda source, run, path, **kw: self.images[path]) as read:
            task = current.projected(None, None, [self.season], descriptions=importer)
            self.assertEqual(len(task), 6)
            self.assertEqual({r['skd'] for r in task}, {'Importer product'})
            self.assertEqual({r['wd'] for r in task}, {'Importer site'})
            self.assertEqual([c.args[2] for c in read.call_args_list], ['closing/dbm/DBMMaster'])
            visible = current.projected(None, None, [self.season])
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0]['skd'], 'DBM product')
        self.assertEqual(visible[0]['nn'], 201)
        self.assertIsNone(visible[0]['tn'])

    def test_projection_checks_master_once_and_preserves_join_occurrences(self):
        seasons = [dict(self.season), dict(self.season, SKUCode='6120 ', WhCode='dp010290 '),
                   dict(self.season, SKUCode=None)]
        masters = self.images['closing/dbm/DBMMaster'] * 2 + [dict(SKUCode=None, WhCode='DP010290', RLT=99, Norm=99)]
        skus = self.images['closing/dbm/SKUDescriptionTbl'] * 2
        sites = self.images['closing/dbm/SiteDescriptionTbl'] * 3
        class CheckedOnce:
            count = 0
            def __iter__(self):
                self.count += 1
                if self.count != 1:
                    raise AssertionError('Repeated complete master read')
                return iter(masters)
        checked = CheckedOnce()
        with patch.object(current, 'consumer_rows', return_value=checked), \
             patch.object(current, 'scope_counts', return_value=[2, 1, 1]):
            rows = current.projected(None, None, seasons, payload={}, descriptions=(skus, sites))
        # SQL join retains 2 master x 2 description x 3 site occurrences,
        # then the permission multiplicity; NULL never joins another NULL.
        self.assertEqual(len(rows), 36)
        self.assertEqual([r['sc'] for r in rows], ['6120'] * 24 + ['6120 '] * 12)
        self.assertEqual(checked.count, 1)
        self.assertTrue(all(r['r'] == 6 and r['nn'] == 201 for r in rows))

    def test_no_seasons_or_visible_scope_never_opens_unrelated_images(self):
        with patch.object(current, 'consumer_rows') as read, \
             patch.object(current, 'scope_counts', return_value=[0]):
            self.assertEqual(current.projected(None, None, []), [])
            self.assertEqual(current.projected(None, None, [self.season], payload={}), [])
        read.assert_not_called()

    def test_batched_scope_matches_original_occurrence_join(self):
        from collections import Counter
        from mta.mdm import force_reads
        product = lambda code, h: SimpleNamespace(SKUCode=code, SL1=h, SL2=None, SL3='')
        location = lambda code, h: SimpleNamespace(WHCode=code, LL1=h, LL2=None, LL3='')
        products = [product('A ', 'x'), product('a', 'x'), product(None, 'x'), product('B', 'z')]
        locations = [location('W ', 'y'), location('w', 'y'), location(None, 'y')]
        permissions = {'products': Counter({('x', None, ''): 2}), 'locations': Counter({('y', None, ''): 3})}
        rows = [SimpleNamespace(SKUCode=s, WhCode=w) for s, w in [('a', 'w'), ('B', 'w'), (None, 'w'), ('a', None)]]
        with patch.object(force_reads, 'triples', side_effect=lambda kind, ids: permissions[kind]), \
             patch.object(force_reads, 'hierarchy_key', side_effect=lambda value: value), \
             patch.object(force_reads.MdmSkuAttributes.objects, 'filter', return_value=products), \
             patch.object(force_reads.MdmLocationAttributes.objects, 'filter', return_value=locations):
            expected = [force_reads._scope_count(None, row, {}) for row in rows]
            self.assertEqual(force_reads.scope_counts(None, rows, {}), expected)
        self.assertEqual(expected, [24, 0, 0, 0])

    def test_late_nonmatching_master_corruption_prevents_partial_result(self):
        def checked():
            yield self.images['closing/dbm/DBMMaster'][0]
            yield dict(SKUCode='unrelated', WhCode='other', RLT=1, Norm=2)
            raise ValueError('Operational state value/type/multiplicity drift')
        with patch.object(current, 'consumer_rows', return_value=checked()):
            with self.assertRaisesRegex(ValueError, 'multiplicity drift'):
                current.projected(None, None, [self.season])

    def test_filter_native_null_not_equal_and_numeric_empty(self):
        self.assertTrue(current._filter({'tn': None}, dict(attributeName='tn', op='<>', value=201)))
        self.assertFalse(current._filter({'tn': None}, dict(attributeName='tn', op='=', value=201)))
        self.assertTrue(current._filter({'tn': 0}, dict(attributeName='tn', op='hasNoValue')))
        self.assertFalse(current._filter({'skd': None}, dict(attributeName='skd', op='Notcontains', value='x')))

    def test_graph_empty_omits_daily_and_preserves_empty_norm(self):
        with patch.object(current, 'scopes', return_value=({'6120'}, {'dp010290'})), \
             patch.object(current, 'publication', return_value=SimpleNamespace(pk='owned')), \
             patch.object(current, 'live_rows', return_value=[]), \
             patch.object(current, 'image_rows', return_value=[]):
            self.assertEqual(current.graph(None, dict(sc='6120', wc='DP010290')), [{'norm': []}])


if __name__ == '__main__':
    unittest.main()
