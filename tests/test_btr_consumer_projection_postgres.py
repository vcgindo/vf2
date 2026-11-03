"""TEMP-only comparison of narrow reads with the complete dated relation."""
import os
import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from django.db import connection, transaction
from mta.presentation import btr_calendar_sources as sources, btr_calendar_images as images
from mta.runtime import relational_state as typed


@unittest.skipUnless(os.environ.get('VF_IR2_PROJECTION_POSTGRES')=='1','Owned isolated PostgreSQL only')
class BtrConsumerProjectionPostgresTests(unittest.TestCase):
    def test_full_relation_projection_preserves_anchor_successor_nulls_and_duplicates(self):
        with transaction.atomic(),connection.cursor() as cur:
            cur.execute('SELECT current_database(),current_user')
            self.assertEqual(cur.fetchone(),('vftest_fresh_ir2_dated1_20261103','vectorflow_mta_owner'))
            cur.execute("SET LOCAL statement_timeout='60s'")
            tables={name:'pg_temp.ir2_proj_'+str(i) for i,name in enumerate(
                ['BTR/BPR','BPR/vf_RationedReqReport',*('BTR/'+name for name in sources.TRENDS)])}
            for name,table in tables.items():
                cur.execute('CREATE TEMP TABLE '+table+' (LIKE '+typed.table_sql(name)+' INCLUDING ALL) ON COMMIT DROP')
            today=date(2026,10,23)
            def run(day):
                def item(path,table):
                    return dict(image=path,table=table,digest='a'*64,count=1,
                                fields=[(f,f,'str') for f in sources.OPERANDS])
                return SimpleNamespace(pk=uuid4(),business_date=day,status='SUCCEEDED',kind='DAILY_CHAIN',
                    evidence_mode='production',production_digest='b'*64,production_manifest={'version':3,'images':{
                    sources.HISTORY:item(sources.HISTORY,'BTR/BPR'),sources.DAILY:item(sources.DAILY,'BPR/vf_RationedReqReport')}})
            first=run(today);second=run(today+timedelta(days=1));second.predecessor_id=first.pk
            directory=sources.advance(first)
            after=sources.advance(second,predecessor=first,directory=directory)
            pairs=[('A','W'),('A','W'),(None,'W'),('','W'),('A',None),('A',''),(None,None),('a ','w')]
            ordinal=0
            for age in (91,90,89,60,30,1,0):
                for i,(sku,loc) in enumerate(pairs):
                    # All eight cells retain raw numeric text MAX, NULL and duplicate bags.
                    values=[None if i==2 else ('9.00' if i%2 else '100.00') if n.endswith('Pen')
                            else ('Red' if i%2 else 'Yellow') for n in sources.OPERANDS]
                    cols=['vf_run_id','vf_image','vf_ordinal','SKUCode','WHCode','ReportDate',*sources.OPERANDS]
                    cur.execute('INSERT INTO '+tables['BTR/BPR']+' ('+','.join(map(typed.quote,cols))+') VALUES ('+
                        ','.join(['%s']*len(cols))+')',[first.pk,sources.HISTORY,ordinal,sku,loc,today-timedelta(days=age),*values])
                    ordinal+=1
            for i,(sku,loc) in enumerate(pairs):
                vals=[None if i==2 else '11.00' if n.endswith('Pen') else 'Black' for n in sources.OPERANDS]
                cols=['vf_run_id','vf_image','vf_ordinal','SKUCode','WhCode',*sources.OPERANDS]
                cur.execute('INSERT INTO '+tables['BPR/vf_RationedReqReport']+' ('+','.join(map(typed.quote,cols))+') VALUES ('+
                    ','.join(['%s']*len(cols))+')',[second.pk,sources.DAILY,i,sku,loc,*vals])
            checked=0
            for current,selected in ((first,directory),(second,after)):
                for name in sources.TRENDS:
                    path='closing/btr/'+name;table='BTR/'+name
                    for i,(sku,loc) in enumerate(pairs):
                        cur.execute('INSERT INTO '+tables[table]+' (vf_run_id,vf_image,vf_ordinal,"SKUCode","WhCode") VALUES (%s,%s,%s,%s,%s)',
                                    [current.pk,path,i,sku,loc])
                    item={'table':table,'image':path}
                    with patch.object(sources,'table_sql',side_effect=tables.__getitem__), \
                            patch.object(typed,'table_sql',side_effect=tables.__getitem__), \
                            patch.object(images,'published_directory',return_value=selected):
                        full,args=sources._trend_query(current,selected,name)
                        for wanted in (['SKUCode','WhCode'],['SKUCode','WhCode','D90'],['D1','D90']):
                            sql,values=images.published_query(current,item,required_fields=wanted)
                            columns='vf_ordinal,'+','.join(map(typed.quote,wanted))
                            cur.execute('SELECT '+columns+' FROM ('+full+') q ORDER BY vf_ordinal',args)
                            expected=cur.fetchall()
                            cur.execute('SELECT '+columns+' FROM ('+sql+') q ORDER BY vf_ordinal',values)
                            self.assertEqual(cur.fetchall(),expected,(current.business_date,name,wanted))
                            checked+=len(expected)
            self.assertEqual(checked,384)
            transaction.set_rollback(True)
