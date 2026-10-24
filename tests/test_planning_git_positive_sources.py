"""Bounded positive GIT location-source tests; no transporter-grid repair."""
import os
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()

from mta.presentation import planning_git_preparation as preparation
from mta.presentation import planning_git_sql as subject
from mta.presentation.context import PublicationUnavailable


class PositiveGitLocationSourcesTests(unittest.TestCase):
    def test_full_recipe_retains_protected_serving_identity(self):
        # Read-only serving witness, run49efa557, before the scoped adapter:
        # g2/git-compatibility-protected-receipt-before.json. A recipe mismatch
        # must fail; production admission still calculates this strict digest.
        self.assertEqual(preparation.production_recipe_digest(),
            '558f12c3ee170daa517d695026e18da7fd8d035a169b659dec3615d67f82fd97')

    def test_explicit_scoped_builder_denies_missing_binding_before_full_sources(self):
        with patch.object(preparation,'admitted_sources',side_effect=AssertionError('Full fallback')), \
                self.assertRaisesRegex(PublicationUnavailable,'scoped_binding_required'):
            preparation.scoped_git_occurrences(SimpleNamespace(),read_binding=None)

    @staticmethod
    def scopes():
        class Codes(set):pass
        products=Codes(('A',));products.multiplicities={'A':1}
        locations=Codes(('L',));locations.multiplicities={'L':1}
        return products,locations

    def test_production_occurrences_preserve_transporter_left_join_multiplicity(self):
        dimensions={
            'closing/importer/SKUDescriptionTbl':'SELECT * FROM sd',
            'closing/importer/SiteDescriptionTbl':'SELECT * FROM ld',
            'closing/importer/SkuAttributeData':'SELECT * FROM sa',
            'closing/importer/LocationAttributeData':'SELECT * FROM la',
            'closing/importer/SkuLocAttributeData':'SELECT * FROM pair',
            'sources/planning/GoodsInTransitTransporterMaster':'SELECT * FROM tm',
        }
        with patch.object(preparation,'admitted_sources',return_value={'git_master':('SELECT * FROM master',['master'])}), \
                patch.object(preparation,'image_query',side_effect=lambda run,path:(dimensions[path],[path])):
            sql,params=preparation.production_git_occurrences(SimpleNamespace())
        self.assertIn('LEFT JOIN tm ON',sql)
        self.assertIn('lower(rtrim(a."SKUCode"::text',sql)
        self.assertIn('lower(rtrim(a."WhCode"::text',sql)
        self.assertNotIn('DISTINCT',sql.upper())
        self.assertEqual(params[0],'master')
        self.assertEqual(params.count('sources/planning/GoodsInTransitTransporterMaster'),1)

    def test_nested_transit_preserves_duplicates_nulls_and_pair_only_correlation(self):
        rows=[
            dict(SKUCode='A ',WhCode='L ',OrderNo='O1',CreationDate=date(2026,6,1),
                 SLT=2,TLT=5,Ageing=6,ETA=date(2026,6,3),CurrentLocationCode=None,
                 InTransitQty=3,Remark=None,ParentWhCode='P1'),
            dict(SKUCode='a',WhCode='l',OrderNo='O1',CreationDate=date(2026,6,1),
                 SLT=2,TLT=5,Ageing=6,ETA=date(2026,6,3),CurrentLocationCode=None,
                 InTransitQty=3,Remark=None,ParentWhCode='DIFFERENT'),
            dict(SKUCode='A',WhCode='L',OrderNo='O2',CreationDate=None,
                 SLT=None,TLT=None,Ageing=99,ETA=None,CurrentLocationCode='ROAD',
                 InTransitQty=-1,Remark='kept',ParentWhCode=None),
        ]
        indexed=subject.location_transit(rows)
        value=indexed[('a','l')]
        self.assertEqual(value['AgeingOrder'],4)
        self.assertEqual(len(value['transit']),3)
        self.assertEqual(value['transit'][0],value['transit'][1])
        self.assertEqual(value['transit'][2]['qty'],-1)
        self.assertIsNone(value['transit'][2]['slt'])
        self.assertNotIn('ParentWhCode',value['transit'][0])

    def test_positive_child_combined_route_keeps_native_invalid_branch_unavailable(self):
        run=SimpleNamespace(kind='DAILY_CHAIN')
        payload=dict(type='child',filters={},paginationParameter=None)
        products,locations=self.scopes()
        with patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch.object(subject,'admitted_git',return_value={'row':('SELECT 1',[])}), \
                patch.object(subject,'admitted_sources',return_value={'git_master':('SELECT 1',[])}), \
                patch.object(subject,'image_rows',return_value=[dict(SKUCode='A',WhCode='L')]):
            with self.assertRaisesRegex(PublicationUnavailable,'207/8120'):
                subject.grid(run,payload,resolved_scope=({},None,products,locations))

    def test_parent_orders_and_pages_on_typed_ageing_before_attaching_nested_bag(self):
        transit=[dict(SKUCode='A',WhCode='L',OrderNo='O1',CreationDate=None,SLT=2,
                      TLT=5,Ageing=6,ETA=None,CurrentLocationCode=None,InTransitQty=3,Remark=None)]*2
        products,locations=self.scopes()
        captured={}
        class Cursor:
            description=[('rn',),('sc',),('wc',),('AgeingOrder',)]
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,sql,params):captured.update(sql=sql,params=params)
            def fetchall(self):return [(1,'A','L',4)]
        def source_query(run,path):
            if path=='sources/bpr/InTransitData':return 'SELECT * FROM typed_transit',['transit']
            return 'SELECT * FROM sku_attributes',[path]
        with patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch.object(subject,'admitted_git',return_value={'row':('SELECT * FROM occurrences',['occ'])}), \
                patch.object(subject,'admitted_sources',return_value={'git_master':('SELECT * FROM master',['master'])}), \
                patch.object(subject,'image_rows',return_value=transit), \
                patch.object(subject,'image_query',side_effect=source_query), \
                patch.object(subject.connection,'cursor',return_value=Cursor()):
            result=subject.grid(SimpleNamespace(kind='DAILY_CHAIN'),
                dict(type='parent',filters={},paginationParameter=dict(pageNumber=1,recordsPerPage=10)),
                resolved_scope=({},None,products,locations))
        self.assertIn('SELECT max(t."Ageing"-t."SLT")',captured['sql'])
        self.assertIn('DESC NULLS LAST,trunc(A."PhysicalInventoryPen")',captured['sql'])
        self.assertIn('WHERE rn BETWEEN',captured['sql'])
        self.assertEqual(result['data'][0]['AgeingOrder'],4)
        self.assertEqual(len(result['data'][0]['transit']),2)


if __name__=='__main__':unittest.main()
