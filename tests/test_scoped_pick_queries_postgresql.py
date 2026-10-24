"""Separate complete raw Pick and RRR grains from actual accepted phase rows."""
from decimal import Decimal
from itertools import product
import json
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_expedite_queries_postgresql as fixtures


def key(*values):
    return None if any(v is None for v in values) else tuple(str(v).rstrip(' ').lower() for v in values)


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedPickQueriesTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr','parents','binding','fetch'):
        locals()[_name]=getattr(fixtures.ScopedExpediteQueriesTests,_name)

    def owner(self,**options):
        from tests import production_h3_fixture as h3
        original=h3.supplied_day
        def day(*args,**kwargs):
            value=original(*args,**kwargs)
            if getattr(self,'virtual_case',False):
                value['day']['order_feed'].append(dict(OrderID='SCOPED-PICK-PARENT-DIRECT',SKUCode='SUPPLIED-Z9',
                    WhCode=h3.PARENT,Qty=3,CustomerExpDate=None))
            if getattr(self,'pick_empty_case',False):
                for row in value['day']['raw_daily']:
                    if row['SKUCode']=='SUPPLIED-Z9' and row['WhCode'] in (h3.CHILD,h3.DIST,h3.DMS,h3.VENDOR):
                        row.update(Stock=1000,GIT=0,Consumption=0,Receipts=0)
            return value
        if getattr(self,'virtual_case',False) or getattr(self,'pick_empty_case',False):
            with patch.object(h3,'supplied_day',side_effect=day):fixtures.ScopedExpediteQueriesTests.owner(self,**options)
        else:fixtures.ScopedExpediteQueriesTests.owner(self,**options)

    def context(self):
        from mta.presentation.scoped_pick_queries import bind
        self.bound=self.binding()
        return bind(self.run,read_binding=self.bound)

    def manual_members(self):
        from mta.presentation import rrr_preparation,scoped_pick_queries
        bags={a:list(enumerate(self.bound.sources.rows(path))) for a,path in rrr_preparation.SOURCES}
        bands=self.bound.sources.rows(scoped_pick_queries.PATH);result=[]
        for b,band in enumerate(bands):
            for i,r in bags['R']:
                if key(r['SKUCode'],r['WhCode'])!=key(band['sku_code'],band['location_code']):continue
                matches=[]
                for alias,sku,loc in (('S','SKUCode','WhCode'),('B','SKUCode','LocCode'),('C','SKUCode',None),('D',None,'WHCode'),('B','SKUCode','LocCode')):
                    group=[(j,row) for j,row in bags[alias] if key(*(row[f] for f in (sku,loc) if f))==key(*(r['SKUCode'] if f==sku else r['WhCode'] for f in (sku,loc) if f))]
                    matches.append(group or ([(None,{})] if len(matches)==4 else []))
                for s,p,c,d,left in product(*matches):
                    result.append(dict(band_ordinal=b,rationed_ordinal=i,standard_ordinal=s[0],pair_ordinal=p[0],
                        sku_ordinal=c[0],location_ordinal=d[0],left_pair_ordinal=left[0],sku_key=key(r['SKUCode'])[0],
                        location_key=key(r['WhCode'])[0],parent_key=None if r['ParentWhCode'] is None else key(r['ParentWhCode'])[0],
                        virtual=key(band['location_code'])==key(band['parent_location_code']),
                        dispatch_color_sequence=r['DispatchColorSequence'],
                        dispatch_pen=None if r['DispatchPen'] is None else Decimal(str(r['DispatchPen']))))
        return result

    def complete(self,virtual):
        from mta.presentation import scoped_pick_queries as module,rrr
        from mta.runtime.scope_revisions import require_current
        self.virtual_case=virtual;self.parents(counter=True);ctx=self.context();before=require_current(self.run)
        bands=self.bound.sources.rows(module.PATH);rationed=self.bound.sources.rows(module.RATIONED)
        raw=self.fetch(ctx.raw_membership_query())
        self.assertEqual(sorted(r['ordinal'] for r in raw),list(range(len(bands))))
        self.assertEqual([r['band_ordinal'] for r in sorted(raw,key=lambda r:r['ordinal'])],list(range(len(bands))))
        if virtual:self.assertTrue(any(r['virtual'] for r in raw))
        self.assertTrue(any(not r['virtual'] for r in raw))
        pair=ctx.pick_query();actual=self.fetch((pair[0]+' ORDER BY vf_source_ordinal',pair[1]))
        self.assertEqual([r.pop('vf_source_ordinal') for r in actual],list(range(len(bands))))
        expected=rrr.pick_rows(rationed,bands)
        self.assertEqual(actual,expected)
        for got,want in zip(actual,expected):
            for field,value in want.items():
                if value is None:self.assertIsNone(got[field])
                elif isinstance(value,bool):self.assertIs(type(got[field]),bool)
        members=self.fetch(ctx.rrr_membership_query())
        from mta.serialization import digest
        self.assertEqual(sorted(members,key=digest),sorted(self.manual_members(),key=digest))
        self.assertEqual(require_current(self.run),before)
        self.assertEqual(set(ctx.provenance()['images']),{module.PATH,*[p for _a,p in module.rrr_preparation.SOURCES]})
        print(json.dumps(dict(virtual_case=virtual,bands=len(bands),raw=len(raw),virtual=sum(r['virtual'] for r in raw),rrr=len(members))),flush=True)

    def test_default_complete_raw_pick_and_separate_rrr_cells(self):self.complete(False)

    def test_external_parent_direct_order_produces_exact_virtual_aliases(self):self.complete(True)

    def test_original_rrr_membership_and_position_sql_parameters_unchanged(self):
        from mta.presentation import scoped_pick_queries as module,rrr_preparation as original
        from django.db import connection
        self.parents();captured=[]
        def observe(execute,sql,params,many,context):
            if 'selected AS (SELECT DISTINCT column2,column3,column4 FROM K)' in sql:captured.append((sql,params))
            return execute(sql,params,many,context)
        with connection.execute_wrapper(observe):ctx=self.context()
        query,params=ctx.band_columns
        class Cursor:
            def execute(self,sql,params):self.query=(sql,params)
            def fetchone(self):return None
        with patch.object(original,'image_query',side_effect=lambda run,path:self.bound.image_query(path)):
            self.assertEqual(ctx.rrr_membership_query(),original.membership_query(self.run,query,params))
            cursor=Cursor();original.validate_positions(cursor,self.run,query,params)
            self.assertEqual(captured,[cursor.query])
        from mta.presentation import planning_expedite_transit_preparation as full
        with patch.object(full,'image_query',side_effect=lambda run,path:self.bound.image_query(path)):
            full_sql,full_params=full.production_pick_query(self.run)
        raw,raw_params=ctx.raw_membership_query();bands,band_params=ctx.bands
        h='H AS (SELECT * FROM mta."fresh_mta_rrrpreparedmembership" WHERE run_id=%s)'
        k='K AS (SELECT * FROM mta."fresh_mta_pickband" WHERE run_id=%s)'
        self.assertEqual(full_sql.count(h),1);self.assertEqual(full_sql.count(k),1)
        self.assertEqual(full_params[len(ctx.rationed[1]):],[self.run.pk,self.run.pk])
        self.assertEqual(ctx.pick_query(),(full_sql.replace(h,'H AS ('+raw+')').replace(k,'K AS ('+bands+')'),
            [*ctx.rationed[1],*raw_params,*band_params]))

    def test_owned_empty_bands_do_not_manufacture_raw_or_rrr_rows(self):
        self.pick_empty_case=True;self.parents(counter=True);ctx=self.context()
        from mta.presentation.scoped_pick_queries import PATH
        self.assertEqual(self.bound.sources.rows(PATH),[])
        self.assertEqual(self.fetch(ctx.raw_membership_query()),[])
        self.assertEqual(self.fetch(ctx.rrr_membership_query()),[])
        self.assertEqual(self.fetch(ctx.pick_query()),[])

    def test_position_guard_rejects_bad_relations_without_persisted_state_changes(self):
        from mta.presentation import scoped_pick_queries as module
        from mta.presentation.context import PublicationUnavailable
        self.parents();ctx=self.context();band=self.bound.sources.rows(module.PATH)[0]
        columns='SELECT 0::bigint AS column1,%s::text AS column2,%s::text AS column3,%s::text AS column4'
        for sku,loc,parent in ((band['sku_code'],'ABSENT',band['parent_location_code']),
                (band['sku_code'],band['location_code'],'WRONG-PARENT')):
            with self.assertRaisesRegex(PublicationUnavailable,'rationed_position_or_parent'):
                module._validate_positions(ctx.rationed,(columns,[sku,loc,parent]))
        r,rp=ctx.rationed
        duplicate=('SELECT * FROM ('+r+') A UNION ALL SELECT * FROM ('+r+') B',[*rp,*rp])
        with self.assertRaisesRegex(PublicationUnavailable,'rationed_position_or_parent'):
            module._validate_positions(duplicate,ctx.band_columns)
        self.assertTrue(self.fetch(ctx.pick_query()))

    def test_wrong_run_and_missing_binding_deny_without_full_receipts(self):
        from mta.presentation import scoped_pick_queries as module
        from mta.presentation.context import PublicationUnavailable
        self.parents();ctx=self.context();old=self.bound;before=self.fetch(ctx.pick_query())
        with self.assertRaisesRegex(PublicationUnavailable,'binding_required'):module.bind(self.run,read_binding=None)
        self.parents()
        with self.assertRaisesRegex(PublicationUnavailable,'phase_owner_differs'):module.bind(self.run,read_binding=old)
        self.assertEqual(self.fetch(ctx.pick_query()),before)
