"""PostgreSQL cardinality/paging proof for positive GIT location serving."""
import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','postgres-test-only')

from django.db import connection
from django.test import TestCase

from mta.presentation import planning_git_preparation as preparation
from mta.presentation import planning_git_sql as reader


class PositiveGitPostgresTests(TestCase):

    def execute(self,*statements):
        with connection.cursor() as cursor:
            for statement in statements:cursor.execute(statement)

    def tearDown(self):
        self.execute(*['DROP TABLE IF EXISTS '+name for name in (
            'gitpos_master','gitpos_tm','gitpos_sd','gitpos_ld','gitpos_sa','gitpos_la','gitpos_pair',
            'gitpage_occ','gitpage_master','gitpage_sa','gitpage_transit')])
        super().tearDown()

    def test_prepared_location_occurrences_preserve_left_transporter_cardinality(self):
        self.execute(
            'CREATE TEMP TABLE gitpos_master(rationed_ordinal bigint,standard_ordinal bigint,"SKUCode" text,"WhCode" text,"ParentWhCode" text,"Git" int,"PhysicalInventoryColor" text)',
            "INSERT INTO gitpos_master VALUES (1,1,'A','L','P',1,'Red'),(2,2,'B','X','Q',1,'Black')",
            'CREATE TEMP TABLE gitpos_tm(vf_ordinal bigint,"SKUCode" text,"WhCode" text)',
            "INSERT INTO gitpos_tm VALUES (0,'A','L'),(1,'A','L')",
            'CREATE TEMP TABLE gitpos_sd(vf_ordinal bigint,"SKUCode" text,"SKUDescription" text)',
            "INSERT INTO gitpos_sd VALUES (10,'A','A desc'),(11,'B','B desc')",
            'CREATE TEMP TABLE gitpos_ld(vf_ordinal bigint,"WHCode" text,"WHDescription" text)',
            "INSERT INTO gitpos_ld VALUES (20,'L','L desc'),(21,'P','P desc'),(22,'X','X desc'),(23,'Q','Q desc')",
            'CREATE TEMP TABLE gitpos_sa(vf_ordinal bigint,"SKUCode" text,"SL1" text,"SL2" text,"SL3" text,"SL4" text,"SL5" text)',
            "INSERT INTO gitpos_sa VALUES (30,'A','S1',NULL,NULL,NULL,NULL),(31,'B','S1',NULL,NULL,NULL,NULL)",
            'CREATE TEMP TABLE gitpos_la(vf_ordinal bigint,"WHCode" text,"LL1" text,"LL2" text,"LL3" text,"LL4" text,"LL5" text)',
            "INSERT INTO gitpos_la VALUES (40,'L','L1',NULL,NULL,NULL,NULL),(41,'X','L1',NULL,NULL,NULL,NULL)",
            'CREATE TEMP TABLE gitpos_pair(vf_ordinal bigint,"SKUCode" text,"LocCode" text)',
            "INSERT INTO gitpos_pair VALUES (50,'A','L'),(51,'B','X')")
        bindings={
            'sources/planning/GoodsInTransitTransporterMaster':'SELECT * FROM gitpos_tm',
            'closing/importer/SKUDescriptionTbl':'SELECT * FROM gitpos_sd',
            'closing/importer/SiteDescriptionTbl':'SELECT * FROM gitpos_ld',
            'closing/importer/SkuAttributeData':'SELECT * FROM gitpos_sa',
            'closing/importer/LocationAttributeData':'SELECT * FROM gitpos_la',
            'closing/importer/SkuLocAttributeData':'SELECT * FROM gitpos_pair',
        }
        with patch.object(preparation,'admitted_sources',return_value={
                'git_master':('SELECT * FROM gitpos_master',[])}), \
                patch.object(preparation,'image_query',side_effect=lambda run,path:(bindings[path],[])):
            sql,params=preparation.production_git_occurrences(SimpleNamespace())
        with connection.cursor() as cursor:
            cursor.execute(sql,params);names=[column[0] for column in cursor.description]
            rows=[dict(zip(names,row)) for row in cursor.fetchall()]
        self.assertEqual(len(rows),3)
        self.assertEqual(sum(row['rationed_ordinal']==1 for row in rows),2)
        self.assertEqual(sum(row['rationed_ordinal']==2 for row in rows),1)
        duplicates=[row for row in rows if row['rationed_ordinal']==1]
        self.assertEqual(duplicates[0],duplicates[1])
        self.assertTrue(all(row['grid_eligible'] for row in rows))

    def test_parent_page_uses_ageing_before_penetration_and_keeps_nested_duplicates(self):
        self.execute(
            'CREATE TEMP TABLE gitpage_occ(ordinal bigint,rationed_ordinal bigint,standard_ordinal bigint,sku_ordinal bigint,pair_ordinal bigint,location_ordinal bigint,grid_eligible boolean,sku_description text,location_description text,parent_description text,sl1 text,sl2 text,sl3 text,sl4 text,sl5 text,ll1 text,ll2 text,ll3 text,ll4 text,ll5 text)',
            "INSERT INTO gitpage_occ VALUES (0,1,1,10,20,30,true,'A desc','L desc','P desc','S',NULL,NULL,NULL,NULL,'W',NULL,NULL,NULL,NULL),(1,2,2,11,21,31,true,'B desc','X desc','Q desc','S',NULL,NULL,NULL,NULL,'W',NULL,NULL,NULL,NULL)",
            'CREATE TEMP TABLE gitpage_master(rationed_ordinal bigint,standard_ordinal bigint,"Status" text,"SKUCode" text,"WhCode" text,"Tags" text,"ParentWhCode" text,"Norm" int,"VirtualNorm" int,"Stock" int,"Git" int,"PhysicalInventoryPen" numeric(10,2),"PhysicalInventoryColor" text,"PipelineInventoryPen" numeric(10,2),"PipelineInventoryColor" text,"Req" int,"Price" int)',
            "INSERT INTO gitpage_master VALUES (1,1,'','A','L',NULL,'P',1,1,1,1,1,'Red',1,'Red',1,NULL),(2,2,'','B','X',NULL,'Q',1,1,1,1,99,'Black',1,'Red',1,NULL)",
            'CREATE TEMP TABLE gitpage_sa(vf_ordinal bigint,"ElephantOrderCapping" int,"Volume" numeric,"Weight" numeric)',
            'INSERT INTO gitpage_sa VALUES (10,NULL,NULL,NULL),(11,NULL,NULL,NULL)',
            'CREATE TEMP TABLE gitpage_transit(vf_ordinal bigint,"SKUCode" text,"WhCode" text,"Ageing" int,"SLT" int)',
            "INSERT INTO gitpage_transit VALUES (0,'A','L',10,2),(1,'A','L',10,2),(2,'B','X',4,2)")
        transit=[
            dict(SKUCode='A',WhCode='L',OrderNo='OA',CreationDate=None,SLT=2,TLT=9,Ageing=10,
                 ETA=None,CurrentLocationCode=None,InTransitQty=4,Remark=None),
            dict(SKUCode='A',WhCode='L',OrderNo='OA',CreationDate=None,SLT=2,TLT=9,Ageing=10,
                 ETA=None,CurrentLocationCode=None,InTransitQty=4,Remark=None),
            dict(SKUCode='B',WhCode='X',OrderNo='OB',CreationDate=None,SLT=2,TLT=3,Ageing=4,
                 ETA=None,CurrentLocationCode=None,InTransitQty=7,Remark=None),
        ]
        class Codes(set):pass
        products=Codes(('A','B'));products.multiplicities={'A':1,'B':1}
        locations=Codes(('L','X'));locations.multiplicities={'L':1,'X':1}
        def images(run,path):
            if path=='sources/bpr/InTransitData':return 'SELECT * FROM gitpage_transit',[]
            if path=='closing/importer/SkuAttributeData':return 'SELECT * FROM gitpage_sa',[]
            raise AssertionError(path)
        with patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch.object(reader,'admitted_git',return_value={'row':('SELECT * FROM gitpage_occ',[])}), \
                patch.object(reader,'admitted_sources',return_value={'git_master':('SELECT * FROM gitpage_master',[])}), \
                patch.object(reader,'image_query',side_effect=images), \
                patch.object(reader,'image_rows',return_value=transit):
            result=reader.grid(SimpleNamespace(kind='DAILY_CHAIN'),
                dict(type='parent',filters={},paginationParameter=dict(pageNumber=1,recordsPerPage=1)),
                resolved_scope=({},None,products,locations))
        self.assertEqual(len(result['data']),1)
        self.assertEqual(result['data'][0]['sc'],'A')
        self.assertEqual(result['data'][0]['AgeingOrder'],8)
        self.assertEqual(len(result['data'][0]['transit']),2)
