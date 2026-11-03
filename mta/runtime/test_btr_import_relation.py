"""PostgreSQL witnesses for ordered BPR history reconstruction."""
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.db import connection
from django.test import TestCase

from mta.runtime import btr_import_relation as history


class BtrImportRelationTests(TestCase):
    def test_expiry_replaced_date_future_rows_and_duplicates(self):
        today = date(2026, 7, 10)
        run = SimpleNamespace(pk=uuid4(), business_date=today)
        old, middle = uuid4(), uuid4()
        tables = {'BTR/BPR':'pg_temp.ir2_anchor', 'BPR/vf_RationedReqReport':'pg_temp.ir2_daily'}
        with connection.cursor() as cursor:
            for key, table in tables.items():
                cursor.execute('CREATE TEMP TABLE '+table+' (LIKE '+history.table_sql(key)+') ON COMMIT DROP')
            # The old physical order need not be date order. Original import
            # removes today, retains a future row, and includes the 89th day.
            for ordinal, (age, stock) in enumerate([(5,2),(90,3),(-1,4),(0,5),(89,6),(5,2),(1,7)]):
                cursor.execute('INSERT INTO pg_temp.ir2_anchor '
                               '(vf_run_id,vf_image,vf_ordinal,"ReportDate","Stock") VALUES (%s,%s,%s,%s,%s)',
                               [old,history.HISTORY,ordinal,today-timedelta(days=age),stock])
            for owner, values in ((middle,[9]),(run.pk,[1,1])):
                for ordinal, stock in enumerate(values):
                    cursor.execute('INSERT INTO pg_temp.ir2_daily '
                                   '(vf_run_id,vf_image,vf_ordinal,"Stock") VALUES (%s,%s,%s,%s)',
                                   [owner,history.DAILY,ordinal,stock])
            yesterday = today-timedelta(days=1)
            days = [history.ImportBlock(middle,yesterday,1),history.ImportBlock(run.pk,today,2)]
            anchor = history.ImportBlock(old,today-timedelta(days=4),4)
            with patch.object(history,'table_sql',side_effect=tables.__getitem__):
                sql, args = history.query(run,anchor=anchor,blocks=days)
            cursor.execute('SELECT vf_ordinal,"Stock","ReportDate" FROM ('+sql+') h ORDER BY vf_ordinal',args)
            pairs=[(2,5),(4,-1),(6,89),(2,5),(9,1),(1,0),(1,0)]
            self.assertEqual(cursor.fetchall(), [(i,stock,today-timedelta(days=age))
                                                 for i,(stock,age) in enumerate(pairs)])
            positions = [6,3,4,0,1,6,2,5,-1,7]
            wanted = 'SELECT pos FROM unnest(%s::bigint[]) WITH ORDINALITY k(pos,request_order)'
            with patch.object(history,'table_sql',side_effect=tables.__getitem__):
                sql,args = history.lookup(run,anchor,days,wanted,[positions],complete_anchor=False)
            cursor.execute('SELECT vf_ordinal,"Stock","ReportDate" FROM ('+sql+') f ORDER BY vf_ordinal',args)
            self.assertEqual(cursor.fetchall(),[(pos,pairs[pos][0],today-timedelta(days=pairs[pos][1]))
                             for pos in sorted(positions) if 0<=pos<len(pairs)])

    def test_foreign_terminal_duplicate_owner_and_gap_beyond_horizon(self):
        run = SimpleNamespace(pk=uuid4(),business_date=date(2026,7,10))
        day = run.business_date
        for blocks in ([history.ImportBlock(uuid4(),day,1)],
                       [history.ImportBlock(run.pk,day-timedelta(days=1),1),history.ImportBlock(run.pk,day,0)],
                       [history.ImportBlock(uuid4(),day-timedelta(days=90),1),history.ImportBlock(run.pk,day,0)]):
            with self.subTest(blocks=blocks), self.assertRaises(ValueError):
                history.query(run,anchor=None,blocks=blocks)

    def test_anchor_expires_by_its_surviving_facts_including_future_dates(self):
        first = date(2026,4,7)
        last = first+timedelta(days=93)
        def source(path, table, count):
            return dict(image=path,table=table,digest='a'*64,count=count)
        original = source(history.HISTORY,'BTR/BPR',5)
        parent = SimpleNamespace(pk=uuid4(),business_date=first,status='SUCCEEDED',
                                 production_manifest={'version':3,'images':{history.HISTORY:original}})
        owner_id = parent.pk
        with connection.cursor() as cursor:
            cursor.execute('CREATE TEMP TABLE ir2_anchor_dates (LIKE '+history.table_sql('BTR/BPR')+') ON COMMIT DROP')
            for i,stamp in enumerate((first-timedelta(days=89),first,first+timedelta(days=1),last,last)):
                cursor.execute('INSERT INTO ir2_anchor_dates (vf_run_id,vf_image,vf_ordinal,"ReportDate")'
                               ' VALUES (%s,%s,%s,%s)',[parent.pk,history.HISTORY,i,stamp])
        with patch.object(history,'table_sql',return_value='pg_temp.ir2_anchor_dates'):
            for age, surviving, nblocks in ((1,3,1),(2,3,2),(92,2,1),(93,0,2)):
                run = SimpleNamespace(pk=uuid4(),business_date=first+timedelta(days=age),
                                      status='SUCCEEDED',predecessor_id=parent.pk)
                directory = history.advance(run,parent,source(history.DAILY,'BPR/vf_RationedReqReport',0))
                anchor = directory['anchor']
                self.assertEqual(anchor['count'] if anchor else 0,surviving)
                if anchor:
                    self.assertEqual(anchor['owner'],str(owner_id))
                self.assertEqual(len(directory['daily']),nblocks)
                self.assertEqual(directory['daily'][-1]['owner'],str(run.pk))
                run.production_manifest={'version':3,'images':{history.HISTORY:
                    dict(original,count=surviving,storage_format=history.FORMAT,sources=directory)}}
                parent=run
