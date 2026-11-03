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

    def test_foreign_terminal_duplicate_owner_and_gap_beyond_horizon(self):
        run = SimpleNamespace(pk=uuid4(),business_date=date(2026,7,10))
        day = run.business_date
        for blocks in ([history.ImportBlock(uuid4(),day,1)],
                       [history.ImportBlock(run.pk,day-timedelta(days=1),1),history.ImportBlock(run.pk,day,0)],
                       [history.ImportBlock(uuid4(),day-timedelta(days=90),1),history.ImportBlock(run.pk,day,0)]):
            with self.subTest(blocks=blocks), self.assertRaises(ValueError):
                history.query(run,anchor=None,blocks=blocks)
