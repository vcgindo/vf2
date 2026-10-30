"""Complete occurrence bags against an independent literal parent join."""
import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class TransitJoinPostgresTests(unittest.TestCase):
    def setUp(self):
        from django.db import connection,transaction
        self.atomic=transaction.atomic();self.atomic.__enter__()
        self.addCleanup(self.rollback)
        self.run=SimpleNamespace(pk=uuid4())
        self.prefix='transit_case_'+uuid4().hex+'_'
        self.tables={name:'pg_temp."'+self.prefix+name+'"' for name in ('nms','remarks','facts','grids','pick','base')}
        definitions={
            'nms':'vf_ordinal bigint,"SKUCode" text,"WhCode" text,"RLT" bigint',
            'remarks':'vf_ordinal bigint,"SKUCode" text,"WhCode" text,"Remark" text',
            'facts':'run_id uuid,ordinal bigint,"SKUCode" text,"WhCode" text',
            'grids':'run_id uuid,direction text,branch text,ordinal bigint,fact_ordinal bigint',
            'pick':'vf_source_ordinal bigint,"SKUCode" text,"WhCode" text,"ParentStockForRationing" numeric',
        }
        self.nms=[(0,'p ','L',5),(1,'P','l ',5),(2,None,'L',1),(3,'q','Z',None),(4,' p','L',2)]
        self.remarks=[(0,'P','l','same'),(1,'p ','L ',None),(2,'P','l','same'),(3,None,'L','null key'),(4,'q','Z','no pick'),(5,'orphan','L','no base')]
        self.facts=[(self.run.pk,i,*key) for i,key in enumerate([('p','l'),('P ','L'),(None,'L'),('q','Z'),('orphan','L')])]
        self.grids=[(self.run.pk,*r) for r in [('parent','dispatch',0,0),('parent','availability',0,0),('parent','dispatch',1,1),('parent','availability',1,3),('child','dispatch',0,0),('parent','dispatch',2,2),('parent','dispatch',3,4)]]
        self.pick=[(0,'p','l',Decimal(8)),(1,'P ','L',None),(2,None,'L',Decimal(99))]
        with connection.cursor() as c:
            for name,definition in definitions.items():c.execute('CREATE TEMP TABLE '+self.tables[name]+' ('+definition+') ON COMMIT DROP')
            for name in definitions:
                for values in getattr(self,name):c.execute('INSERT INTO '+self.tables[name]+' VALUES ('+','.join(['%s']*len(values))+')',values)

    def rollback(self):
        from django.db import transaction
        transaction.set_rollback(True);self.atomic.__exit__(None,None,None)

    @staticmethod
    def same(left,right):
        return left is not None and right is not None and left.rstrip(' ').lower()==right.rstrip(' ').lower()

    def expected(self):
        base=[]
        for ni,sku,wh,rlt in self.nms:
            matched=[r for r in self.remarks if self.same(sku,r[1]) and self.same(wh,r[2])]
            for r in matched or [(None,None,None,None)]:base.append((len(base),ni,r[0],sku,wh,rlt,r[3]))
        matches=[]
        for bo,ni,ri,sku,wh,rlt,text in base:
            for ro,rs,rw,remark in self.remarks:
                if ri!=ro:continue
                for arun,ao,asku,awh in self.facts:
                    if not(self.same(asku,rs) and self.same(awh,rw)):continue
                    for grun,direction,branch,go,fo in self.grids:
                        if direction!='parent' or grun!=arun or fo!=ao:continue
                        picks=[p for p in self.pick if self.same(p[1],asku) and self.same(p[2],awh)]
                        for po,ps,pw,stock in picks or [(None,None,None,None)]:matches.append((bo,branch,go,po,stock))
        matches.sort(key=lambda r:tuple((v is not None,v) for v in r[:4]))
        return [(i,*row) for i,row in enumerate(matches)]

    def compare(self):
        from django.db import connection
        from mta.presentation import planning_expedite_transit_preparation as original,expedite_transit_join as optimized
        def image(run,path):return ('SELECT * FROM '+self.tables['nms' if path.endswith('NMSAllItems') else 'remarks'],[])
        grids=('SELECT * FROM '+self.tables['grids'],[]);pick=('SELECT * FROM '+self.tables['pick'],[])
        with patch.object(original,'image_query',side_effect=image),patch.object(original,'production_pick_query',return_value=pick),patch.object(original,'admitted_expedite_grids',return_value={'row':grids}):
            bsql,bp=original.production_base_query(self.run)
            with connection.cursor() as c:c.execute('CREATE TEMP TABLE '+self.tables['base']+' ON COMMIT DROP AS SELECT %s::uuid AS run_id,B.* FROM ('+bsql+') B',[self.run.pk,*bp])
            reference,rp=original.production_match_query(self.run)
        reference=reference.replace('mta.fresh_mta_planningexpeditetransitbase',self.tables['base']).replace('mta.fresh_mta_expediterow',self.tables['facts'])
        expected=self.expected()
        with connection.cursor() as c:
            c.execute(reference,rp);self.assertEqual(c.fetchall(),expected)
        with optimized.prepared_match(base=('SELECT * FROM '+self.tables['base'],[]),remarks=image(self.run,'remarks'),facts=('SELECT * FROM '+self.tables['facts'],[]),grids=grids,pick=pick) as (query,params):
            with connection.cursor() as c:
                c.execute(query,params);self.assertEqual(c.fetchall(),expected)
        with connection.cursor() as c:
            c.execute("SELECT count(*) FROM pg_class WHERE relnamespace=pg_my_temp_schema() AND relname LIKE 'vf_transit_%%'")
            self.assertEqual(c.fetchone()[0],0)
        return expected

    def test_raw_scoped_pick_duplicate_null_and_unmatched_bags(self):
        rows=self.compare();self.assertTrue(rows)
        self.assertTrue(any(row[-2:] == (None,None) for row in rows))
        self.assertTrue(any(row[-2:] == (1,None) for row in rows))

    def test_full_display_membership_keeps_additional_pick_occurrences(self):
        from django.db import connection
        extra=(3,'p','l',Decimal(8));self.pick.append(extra)
        with connection.cursor() as c:c.execute('INSERT INTO '+self.tables['pick']+' VALUES (%s,%s,%s,%s)',extra)
        rows=self.compare();self.assertTrue(any(row[-2]==3 for row in rows))

    def test_certified_empty_remark_bag_keeps_no_match(self):
        from django.db import connection
        self.remarks=[]
        with connection.cursor() as c:c.execute('DELETE FROM '+self.tables['remarks'])
        self.assertEqual(self.compare(),[])
        with connection.cursor() as c:
            c.execute('SELECT count(*),count(remark_ordinal) FROM '+self.tables['base'])
            self.assertEqual(c.fetchone(),(len(self.nms),0))
