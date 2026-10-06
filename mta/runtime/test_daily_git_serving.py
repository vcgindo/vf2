"""PostgreSQL proof for production GIT chart aggregation and custom paging."""
import os
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'postgres-test-only')

from django.db import connection
from django.test import TestCase

from mta.presentation import daily_git_custom, daily_git_preparation, daily_git_read
from mta.presentation.context import PublicationUnavailable


class Codes(set):
    pass


class DailyGitServingPostgresTests(TestCase):
    def execute(self, *statements):
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

    def setUp(self):
        super().setUp()
        self.execute(
            'CREATE TEMP TABLE gs_tm("SKUCode" text,"WhCode" text,"ParentWhCode" text,"TransporterCode" text,"TransporterName" text,"OrderNo" text,"IsReceiving" boolean,"PhysicalInventoryColor" text,"LRCode" text,"SKUStatus" text,"TruckStatus" text,"Status" text,"InTransitQty" integer,"TransporterContact" text,"CreationDate" date,"SLT" integer,"Ageing" integer,"ETA" date,"CurrentLocation" text,"Remark" text)',
            "INSERT INTO gs_tm VALUES ('A','L','P','T','Carrier','O',true,'Red','LR1','SuperDelay','SuperDelay','Open',2,NULL,'2026-06-01',2,5,NULL,NULL,NULL),('A','L','P','T','Carrier','O',true,'Red','LR2','Delay','Delay','Open',2,NULL,'2026-06-01',2,5,NULL,NULL,NULL)",
            'CREATE TEMP TABLE gs_transit("SKUCode" text,"WhCode" text,"TLT" integer,"SLT" integer)',
            "INSERT INTO gs_transit VALUES ('A','L',5,2),('A','L',9,2),('A','L',99,NULL)",
            'CREATE TEMP TABLE gs_git("SKUCode" text,"WhCode" text,"ParentWhCode" text,"PhysicalInventoryColor" text,"Git" integer,"IsParent" boolean,"Req" integer)',
            "INSERT INTO gs_git VALUES ('A','L','P','Black',1,true,7)",
            'CREATE TEMP TABLE gs_desc("WHCode" text,"WHDescription" text)',
            "INSERT INTO gs_desc VALUES ('L','L''ocation'),('P','Parent')",
            'CREATE TEMP TABLE gs_loc("WHCode" text,"LogisticsLocation" text,"LL1" text,"LL2" text,"LL3" text,"LL4" text,"LL5" text)',
            "INSERT INTO gs_loc VALUES ('L','LOG','North',NULL,NULL,NULL,NULL)",
            'CREATE TEMP TABLE gs_nms("SKUCode" text,"WhCode" text,"SKUDescription" text,"WHDescription" text,"ParentWhCode" text,"Norm" integer,"MinNorm" integer,"RLT" integer,"RCP" integer,"GCP" integer,"OCP" integer,"MinOrderCount" integer,"PackSize" integer,"FGRMFlag" text,"DBMActive" boolean,"SL1" text,"SL2" text,"SL3" text,"SL4" text,"SL5" text,"LL1" text,"LL2" text,"LL3" text,"LL4" text,"LL5" text)',
            "INSERT INTO gs_nms VALUES ('A','L','A desc','Location','P',10,1,2,1,1,1,1,1,'FG',true,'S',NULL,NULL,NULL,NULL,'North',NULL,NULL,NULL,NULL)")
        self.products = Codes(('A',)); self.products.multiplicities = {'A': 2}
        self.locations = Codes(('L', 'P')); self.locations.multiplicities = {'L': 1, 'P': 1}
        self.relations = {
            daily_git_preparation.TRANSPORTER_PATH: ('SELECT * FROM gs_tm', []),
            daily_git_preparation.TRANSIT_PATH: ('SELECT * FROM gs_transit', []),
            'git_master': ('SELECT * FROM gs_git', []),
            daily_git_preparation.DESCRIPTION_PATH: ('SELECT * FROM gs_desc', []),
            daily_git_preparation.LOCATION_PATH: ('SELECT * FROM gs_loc', []),
            daily_git_preparation.NMS_PATH: ('SELECT * FROM gs_nms', []),
        }

    def tearDown(self):
        self.execute(*['DROP TABLE IF EXISTS ' + name for name in
                       ('gs_tm', 'gs_transit', 'gs_git', 'gs_desc', 'gs_loc', 'gs_nms')])
        super().tearDown()

    def test_nonempty_charts_and_custom_nms_empty_boundary(self):
        with patch.object(daily_git_read, 'sources',
                          return_value=(self.relations, [], [])):
            chart = daily_git_read.graph(SimpleNamespace(), self.products, self.locations)
        status = chart['data']['locationWise']['maxTechBlackRedColumn']['data'][0]
        self.assertEqual((status['superdelay'], status['delay']), ('2', '2'))
        delay = chart['data']['locationWise']['delayDaysStatisticalBox']['data'][0]
        self.assertEqual((delay['mean'], delay['median'], delay['Q1'], delay['Q3']),
                         ('5.00', '5.00', '3.00', '7.00'))
        with patch.object(daily_git_custom, 'sources',
                          return_value=(self.relations, [], [])), \
             self.assertRaisesRegex(PublicationUnavailable, 'UNORDERED-TIE'):
            daily_git_custom.custom(SimpleNamespace(), self.products,
                                    self.locations, None)
        self.execute('TRUNCATE gs_tm', 'TRUNCATE gs_transit',
            "INSERT INTO gs_tm VALUES ('A','L','P','T','Carrier','O',true,'Red','LR1','Delay','Delay','Open',2,NULL,'2026-06-01',2,5,NULL,NULL,NULL),('A','L','P','T','Carrier','O',true,'Red','LR1','Delay','Delay','Open',2,NULL,'2026-06-01',2,5,NULL,NULL,NULL)",
            "INSERT INTO gs_transit VALUES ('A','L',5,2)")
        with patch.object(daily_git_custom, 'sources',
                          return_value=(self.relations, [], [])):
            safe_all = daily_git_custom.custom(SimpleNamespace(), self.products,
                                               self.locations, None)
            safe_page = daily_git_custom.custom(SimpleNamespace(), self.products,
                                                self.locations, (1, 3))
        self.assertEqual(len(safe_all['data']), 4)
        expected = dict(sc='A', wc='L', sd='A desc', wd='Location', dd=3,
            ss='Delay', s='Open', pwc='P', pn='Parent', n=10, mn=1, rlt=2,
            rcp=1, gcp=1, ocp=1, moc=1, rq=7, ps=1, frf='FG', da=True,
            odn='O', ts='Delay', tn='Carrier', tc='T', fl='P', itq=2,
            cd=date(2026, 6, 1), slt=2, ag=5, lc='LR1', sl1='S', ll1='North')
        self.assertEqual(safe_all['data'], [dict(RN=index, **expected)
                                            for index in range(1, 5)])
        self.assertEqual(len(safe_page['data']), 3)
        self.assertEqual({key: value for key, value in safe_page['data'][0].items() if key != 'RN'},
                         {key: value for key, value in safe_page['data'][1].items() if key != 'RN'})
        self.execute('TRUNCATE gs_nms')
        with patch.object(daily_git_custom, 'sources',
                          return_value=(self.relations, [], [])):
            empty = daily_git_custom.custom(SimpleNamespace(), self.products,
                                            self.locations, (1, 3))
        self.assertEqual(empty['data'], [])
