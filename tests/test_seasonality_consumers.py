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
        with patch.object(current, 'image_rows', side_effect=lambda run, path: self.images[path]) as read:
            task = current.projected(None, None, [self.season], descriptions=importer)
            self.assertEqual(len(task), 6)
            self.assertEqual({r['skd'] for r in task}, {'Importer product'})
            self.assertEqual({r['wd'] for r in task}, {'Importer site'})
            self.assertEqual([c.args[1] for c in read.call_args_list], ['closing/dbm/DBMMaster'])
            visible = current.projected(None, None, [self.season])
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0]['skd'], 'DBM product')
        self.assertEqual(visible[0]['nn'], 201)
        self.assertIsNone(visible[0]['tn'])

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
