"""Actual owned BPR Pick/Post-Pick and fixed remark-prefix source queries."""
from copy import copy
from dataclasses import replace
from datetime import datetime,timezone
import json
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_remarks_postgresql as remarks
from tests import test_scoped_pick_queries_postgresql as pick_fixture
from tests import test_scoped_expedite_queries_postgresql as expedite


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedExpeditePickQueriesTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr','parents'):
        locals()[_name]=getattr(remarks.ScopedRemarkTests,_name)
    row=staticmethod(remarks.ScopedRemarkTests.row)
    for _name in ('fetch','rows','match','facts','grid'):
        locals()[_name]=getattr(expedite.ScopedExpediteQueriesTests,_name)

    def owner(self,**options):
        pick_fixture.ScopedPickQueriesTests.owner(self,remark_inputs=self.snapshot,**options)

    def binding(self,**options):
        return remarks.ScopedRemarkTests.binding(self,**dict(dict(include_nms=True),**options))

    def context(self,**options):
        from mta.presentation import scoped_expedite_pick_queries as module,scoped_pick_storage
        self.bound=self.binding(**options)
        row=scoped_pick_storage.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.pick=scoped_pick_storage.bind(row.pk,expected_digest=row.digest,action_revision=0)
        return module.bind(self.run,read_binding=self.bound,pick_binding=self.pick)

    def independent(self,ctx):
        from mta.presentation import scoped_expedite_pick_queries as module,rrr,pick_post
        from mta.serialization import storage
        raw=rrr.pick_rows(self.bound.sources.rows('reports/bpr/vf_RationedReqReport'),
            self.bound.sources.rows('sources/calculation/PickBands'))
        parent_members=[]
        for i,s in enumerate(raw):
            multiplicity=sum(expedite.same(r['ParentWhCode'],s['WhCode']) for r in raw)
            for j,t in enumerate(raw):
                if (multiplicity and expedite.same(s['SKUCode'],t['SKUCode']) and expedite.same(s['WhCode'],t['WhCode'])
                        and t['WhCode'] is not None and t['ParentWhCode'] is not None
                        and not expedite.same(t['WhCode'],t['ParentWhCode'])):
                    parent_members.append(dict(scope_ordinal=i,fact_ordinal=j,multiplicity=multiplicity))
        self.assertEqual(sorted(self.fetch(ctx.prepost_members()),key=lambda r:(r['scope_ordinal'],r['fact_ordinal'])),parent_members)
        post=pick_post.produce(raw)
        expected=[dict(r,vf_source_ordinal=i,PostPipelineInventoryColor=post[i]['PostPipelineInventoryColor']) for i,r in enumerate(raw)]
        sql,params=ctx.chart_pick_query()
        self.assertEqual(storage(self.fetch((sql+' ORDER BY vf_source_ordinal',params))),storage(expected))
        nms=self.bound.sources.rows(module.NMS);history=self.fetch(self.bound.remarks.query())
        base=[]
        for i,n in enumerate(nms):
            matched=[r for r in history if expedite.same(n['SKUCode'],r['SKUCode']) and expedite.same(n['WhCode'],r['WhCode'])]
            for r in sorted(matched,key=lambda r:r['vf_ordinal']) or [None]:
                base.append(dict(ordinal=len(base),nms_ordinal=i,remark_ordinal=None if r is None else r['vf_ordinal'],
                    sku_code=n['SKUCode'],location_code=n['WhCode'],sku_key=expedite.k(n['SKUCode']),
                    location_key=expedite.k(n['WhCode']),rlt=n['RLT'],remark=None if r is None else r['Remark'],
                    remark_key=None if r is None else expedite.k(r['Remark'])))
        sql,params=ctx.parent_base_query()
        self.assertEqual(storage(self.fetch((sql+' ORDER BY ordinal',params))),storage(base))
        grids=[]
        for branch in ('dispatch','availability'):
            rows=sorted(self.grid('parent',branch),key=lambda r:tuple((r[f] is not None,r[f]) for f in module.GRID_ORDER))
            grids.extend(dict(direction='parent',branch=branch,ordinal=i,fact_ordinal=r['fact_ordinal']) for i,r in enumerate(rows))
        self.assertEqual(sorted(self.fetch(ctx.parent_grids_query()),key=lambda r:(r['branch'],r['ordinal'])),
            sorted(grids,key=lambda r:(r['branch'],r['ordinal'])))
        facts=dict(self.facts());expected=[];history={r['vf_ordinal']:r for r in history}
        for b in base:
            r=history.get(b['remark_ordinal'])
            if r is None:continue
            for g in grids:
                a=facts[g['fact_ordinal']]
                if not(expedite.same(a['SKUCode'],r['SKUCode']) and expedite.same(a['WhCode'],r['WhCode'])):continue
                picked=[(i,p) for i,p in enumerate(raw) if expedite.same(p['SKUCode'],a['SKUCode']) and expedite.same(p['WhCode'],a['WhCode'])]
                for i,p in picked or [(None,{})]:
                    expected.append(dict(base_ordinal=b['ordinal'],branch=g['branch'],grid_ordinal=g['ordinal'],
                        pick_ordinal=i,parent_stock=p.get('ParentStockForRationing')))
        expected.sort(key=lambda r:tuple((r[k] is not None,r[k]) for k in ('base_ordinal','branch','grid_ordinal','pick_ordinal')))
        expected=[dict(r,ordinal=i) for i,r in enumerate(expected)]
        sql,params=ctx.parent_match_query()
        self.assertEqual(storage(self.fetch((sql+' ORDER BY ordinal',params))),storage(expected))
        print(json.dumps(dict(boundary=getattr(self,'external_boundary','default'),raw=len(raw),prepost=len(parent_members),
            base=len(base),grids=len(grids),matches=len(expected))),flush=True)
        return parent_members,base,grids,expected

    def complete(self,boundary=None,virtual=False):
        from mta.runtime.scope_revisions import require_current
        self.external_boundary=boundary;self.virtual_case=virtual
        stamp=datetime(2037,4,9,tzinfo=timezone.utc)
        self.parents(rows=[self.row(None,stamp),self.row('same',stamp),self.row('same',stamp)],counter=True,consumer_cut=True)
        ctx=self.context();before=require_current(self.run)
        result=self.independent(ctx)
        self.assertEqual(require_current(self.run),before)
        self.assertIn('remarks',ctx.provenance(parent_transit=True))
        self.assertEqual(ctx.provenance(parent_transit=True)['source_projection_digest'],self.bound.projection.digest)
        self.assertNotIn('remarks',ctx.provenance())
        return result

    def test_default_complete_duplicate_null_remark_and_pick_cells(self):self.complete()

    def test_positive_dispatch_parent_grid_and_pick_matches(self):
        _members,_base,grids,matches=self.complete('dispatch')
        self.assertTrue(grids);self.assertTrue(matches)

    def test_positive_availability_grid_keeps_actual_topology_prepost_empty(self):
        members,_base,grids,matches=self.complete('availability')
        self.assertTrue(grids);self.assertTrue(matches)
        # This retained H3 topology produces no physical parent Pick band.
        # Positive native hierarchy coverage is a separate acceptance boundary.
        self.assertEqual(members,[])

    def test_retained_cross_sku_duplicate_sql_join_semantics_only(self):
        self.parents();ctx=self.context()
        # Exact relation from test_expedite_charts.py's existing join probe.
        # These are transient SQL operands, never accepted calculation facts.
        rows=[(0,'337','AG515802','LP001'),(1,'338','LP001','AG515802'),(2,'338','LP001','AG515802')]
        query='SELECT * FROM (VALUES '+','.join(['(%s::bigint,%s::text,%s::text,%s::text)']*len(rows))+') '
        query+='P(vf_source_ordinal,"SKUCode","WhCode","ParentWhCode")'
        with patch.object(type(ctx.pick),'pick_query',return_value=(query,[v for r in rows for v in r])):
            actual=self.fetch(ctx.prepost_members())
        self.assertEqual(sorted(actual,key=lambda r:(r['scope_ordinal'],r['fact_ordinal'])),[
            dict(scope_ordinal=0,fact_ordinal=0,multiplicity=2),
            *[dict(scope_ordinal=s,fact_ordinal=t,multiplicity=1) for s in (1,2) for t in (1,2)]])

    def test_empty_expedite_and_virtual_pick_are_distinct_populations(self):self.complete('empty',True)

    def test_original_full_sql_and_parameters_after_owned_relation_substitution(self):
        from mta.presentation import planning_expedite_chart_preparation as charts,planning_expedite_transit_preparation as original
        self.external_boundary='dispatch';self.parents();ctx=self.context()
        def image(run,path):
            return self.bound.remarks.query() if path=='sources/bpr/BPRReport_RemarkDetails' else self.bound.image_query(path)
        with patch.object(original,'production_pick_query',side_effect=lambda run:ctx.pick.pick_query()), \
                patch.object(original,'image_query',side_effect=image), \
                patch.object(original,'admitted_expedite_grids',return_value={'row':ctx.parent_grids_query()}):
            self.assertEqual(ctx.prepost_members(),charts.production_prepost_members(self.run))
            self.assertEqual(ctx.parent_base_query(),original.production_base_query(self.run))
            sql,params=original.production_match_query(self.run)
        base,bp=ctx.parent_base_query();facts,fp=self.bound.fact_query('ExpediteDispatches')
        sql=sql.replace('), candidates AS (SELECT ', '),B AS (SELECT %s::uuid AS run_id,base.* FROM ('+base+') base),A AS ('+facts+'), candidates AS (SELECT ',1)
        sql=sql.replace('FROM mta.fresh_mta_planningexpeditetransitbase B ','FROM B ')
        sql=sql.replace('JOIN mta.fresh_mta_expediterow A ON ','JOIN A ON ')
        self.assertEqual(ctx.parent_match_query(),(sql,[*params[:-1],self.run.pk,*bp,*fp,params[-1]]))

    def test_missing_sources_and_wrong_run_phase_config_action_deny(self):
        from mta.presentation import scoped_expedite_pick_queries as module
        from mta.presentation.context import PublicationUnavailable
        self.parents();ctx=self.context()
        for field,value in (('phase_id',self.pre_receipt.pk),('configuration_digest','f'*64),
                ('action_revision',1),('source_digest','f'*64)):
            generation=copy(self.pick.generation);setattr(generation,field,value)
            with self.assertRaisesRegex(PublicationUnavailable,'raw_pick_owner_differs'):
                module.bind(self.run,read_binding=self.bound,pick_binding=replace(self.pick,generation=generation))
        for read,pick in ((None,self.pick),(self.bound,None)):
            with self.assertRaises(PublicationUnavailable):module.bind(self.run,read_binding=read,pick_binding=pick)
        missing=module.bind(self.run,read_binding=self.binding(include_nms=False),pick_binding=self.pick)
        with self.assertRaises(PublicationUnavailable):missing.parent_base_query()
        no_remarks=module.bind(self.run,read_binding=self.binding(include_remarks=False),pick_binding=self.pick)
        self.assertIsNotNone(no_remarks.prepost_members())
        with self.assertRaises(PublicationUnavailable):no_remarks.parent_base_query()
        sources=copy(self.bound.sources.run);sources.pk=self.pre_receipt.pk
        with self.assertRaisesRegex(PublicationUnavailable,'raw_pick_owner_differs'):
            module.bind(self.run,read_binding=replace(self.bound,sources=replace(self.bound.sources,run=sources)),pick_binding=self.pick)
        old=self.pick;old_remarks=self.bound.remarks;self.parents();fresh=self.context()
        with self.assertRaises(PublicationUnavailable):module.bind(self.run,read_binding=self.bound,pick_binding=old)
        wrong_remarks=module.bind(self.run,read_binding=replace(self.bound,remarks=old_remarks),pick_binding=self.pick)
        with self.assertRaisesRegex(PublicationUnavailable,'remark_owner_differs'):wrong_remarks.parent_base_query()

    def test_later_remark_prefix_changes_only_fresh_parent_sources(self):
        from mta.presentation import ancillary_live as live,scoped_expedite_pick_queries as module
        from mta.runtime.scope_revisions import require_current
        self.external_boundary='dispatch';self.parents(counter=True,consumer_cut=True)
        ctx=self.context();before=ctx.provenance(parent_transit=True);old=self.fetch(ctx.parent_match_query())
        base=self.fetch(ctx.parent_base_query());revision=require_current(self.run)
        live.append(live.BPR,[{k:v for k,v in self.row('later',None).items() if k!='RemarkDate'}],
            actor_id='owned-expedite-parent',timestamp=datetime(2037,4,11,tzinfo=timezone.utc))
        fresh=module.bind(self.run,read_binding=self.binding(),pick_binding=self.pick)
        self.assertNotEqual(fresh.provenance(parent_transit=True),before)
        self.assertEqual(ctx.provenance(parent_transit=True),before)
        self.assertEqual(self.fetch(ctx.parent_base_query()),base)
        self.assertEqual(self.fetch(ctx.parent_match_query()),old)
        self.assertTrue(self.fetch(fresh.parent_match_query()))
        self.assertEqual(require_current(self.run),revision)
