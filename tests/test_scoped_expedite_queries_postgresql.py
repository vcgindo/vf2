"""Actual accepted Expedite source relations; rollback-only supplied components."""
from itertools import product
import json
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_planning_postgresql as fixtures


def k(value):return None if value is None else str(value).rstrip(' ').lower()


def same(a,b):return a is not None and b is not None and k(a)==k(b)


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedExpediteQueriesTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr','parents'):
        locals()[_name]=getattr(fixtures.ScopedPlanningTests,_name)

    def owner(self,**options):
        from tests import production_h3_fixture as h3
        original=h3.supplied_day
        def day(*args,**kwargs):
            value=original(*args,**kwargs)
            for row in value['day']['raw_daily']:
                if row['SKUCode']!='SUPPLIED-Z9':continue
                if row['WhCode']==h3.CHILD:
                    row.update(Stock=1000 if self.external_boundary=='empty' else 0,GIT=0,Consumption=0,Receipts=0)
                if row['WhCode']==h3.PARENT and self.external_boundary=='availability':
                    row.update(Stock=0,Consumption=40,Receipts=0)
            return value
        if getattr(self,'external_boundary',None):
            with patch.object(h3,'supplied_day',side_effect=day):fixtures.ScopedPlanningTests.owner(self,**options)
        else:fixtures.ScopedPlanningTests.owner(self,**options)

    def binding(self,*,nms=True):
        from mta.presentation.scoped_prepared import bind
        return bind(self.report.pk,expected_digest=self.source.digest,
            expected_report_digest=self.report.digest,action_revision=0,include_nms=nms)

    def fetch(self,pair):
        from django.db import connection
        with connection.cursor() as c:
            c.execute(*pair);names=[col[0] for col in c.description]
            return [dict(zip(names,r)) for r in c.fetchall()]

    def rows(self,path):return list(enumerate(self.bound.sources.rows(path)))

    def match(self,rows,field,value,*,left=False):
        found=[(i,r) for i,r in rows if same(r.get(field),value)]
        return found or ([(None,{})] if left else [])

    def facts(self):return list(enumerate(self.bound.reports.rows('ExpediteDispatches')))

    def grid(self,direction,branch):
        standards=self.rows('closing/dbm/SKULocStandardAttributes')
        dimensions={n:self.rows('closing/importer/'+n) for n in ('SKUDescriptionTbl','SiteDescriptionTbl',
            'SkuAttributeData','LocationAttributeData','SkuLocAttributeData')}
        result=[];left=not(direction=='child' and branch=='availability')
        for i,a in self.facts():
            if (a['RationedQty']<=0 if branch=='dispatch' else a['RationedQty']!=0):continue
            if (direction=='parent' or branch=='dispatch') and k(a['PipelineInventoryColor']) not in ('black','red'):continue
            pair=[(j,r) for j,r in dimensions['SkuLocAttributeData']
                if same(r['SKUCode'],a['SKUCode']) and same(r['LocCode'],a['WhCode'])]
            standard=[(j,r) for j,r in standards if same(r['SKUCode'],a['SKUCode']) and same(r['WhCode'],a['WhCode'])]
            master=[(r['source_ordinal'],r) for r in self.bound.rows('bpr_master')
                if same(r['SKUCode'],a['SKUCode']) and same(r['WHCode'],a['ParentWhCode'])]
            groups=[standard or ([(None,{})] if left else []),
                self.match(dimensions['SKUDescriptionTbl'],'SKUCode',a['SKUCode'],left=left),
                self.match(dimensions['SiteDescriptionTbl'],'WHCode',a['WhCode'],left=left),
                self.match(dimensions['SiteDescriptionTbl'],'WHCode',a['ParentWhCode'],left=True),
                self.match(dimensions['SkuAttributeData'],'SKUCode',a['SKUCode'],left=left),
                self.match(dimensions['LocationAttributeData'],'WHCode',a['WhCode'],left=left),
                pair or ([(None,{})] if left else []),master if direction=='parent' and branch=='availability' else [(None,{})]]
            for s,sd,ld,pd,sa,la,pair,m in product(*groups):
                result.append(dict(fact_ordinal=i,standard_ordinal=s[0],sku_description_ordinal=sd[0],
                    location_description_ordinal=ld[0],parent_description_ordinal=pd[0],sku_ordinal=sa[0],
                    location_ordinal=la[0],pair_ordinal=pair[0],master_ordinal=m[0],
                    sku_description=sd[1].get('SKUDescription'),location_description=ld[1].get('WHDescription'),
                    parent_description=pd[1].get('WHDescription'),
                    **{p.lower()+str(n):r.get(p+str(n)) for p,r in (('SL',sa[1]),('LL',la[1])) for n in range(1,6)}))
        return result

    def custom(self):
        from mta.presentation.daily_git_preparation import NMS_PATH
        nms=self.rows(NMS_PATH);bpr=self.rows('reports/bpr/BPR_Table');desc=self.rows('closing/importer/SiteDescriptionTbl')
        result=[]
        for i,b in self.facts():
            if not(b['RationedQty']>0 and b['IsReceiving'] and k(b['PipelineInventoryColor']) in ('black','red')):continue
            items=[(j,r) for j,r in nms if same(r['SKUCode'],b['SKUCode']) and same(r['WhCode'],b['WhCode'])] or [(None,{})]
            for j,a in items:
                reports=[(n,r) for n,r in bpr if same(r['SKUCode'],a.get('SKUCode')) and same(r['WhCode'],a.get('WhCode'))] or [(None,{})]
                for (n,d),(q,c) in product(reports,self.match(desc,'WHCode',a.get('ParentWhCode'),left=True)):
                    result.append(dict(fact_ordinal=i,nms_ordinal=j,bpr_ordinal=n,parent_description_ordinal=q,
                        sku_key=k(a.get('SKUCode')),location_key=k(a.get('WhCode')),parent_description=c.get('WHDescription')))
        return result

    def members(self,direction,family):
        descriptions=self.rows('closing/importer/SiteDescriptionTbl');attrs=self.rows('closing/importer/LocationAttributeData')
        result=[]
        for i,s in self.facts():
            targets=[(i,s)];masters=[(None,{})];attr=True
            if family=='critical':
                if not(s['RationedQty']>0 and k(s['PipelineInventoryColor']) in ('black','red')):continue
                code=s['ParentWhCode']
                if direction=='child':
                    if not s['IsParent']:continue
                    targets=[(j,a) for j,a in self.facts() if same(s['SKUCode'],a['SKUCode']) and same(s['ParentWhCode'],a['WhCode'])]
            elif family=='receiving':
                if direction=='child' and not s['IsReceiving']:continue
                code=s['WhCode']
            else:
                if (s['RationedQty']!=0 if family=='nil_stock' else s['BRAge'] is None or s['BRAge']<=0):continue
                masters=[(r['source_ordinal'],r) for r in self.bound.rows('bpr_master')
                    if same(s['SKUCode'],r['SKUCode']) and same(s['ParentWhCode'],r['WHCode'])]
                attr=False
            for (j,a),(m,master) in product(targets,masters):
                actual=master['ParentWhCode'] if not attr else a['WhCode'] if family=='critical' and direction=='child' else code
                for (q,d),(n,l) in product(self.match(descriptions,'WHCode',actual),
                        self.match(attrs,'WHCode',actual) if attr else [(None,{})]):
                    result.append(dict(scope_ordinal=i,fact_ordinal=j,master_ordinal=m,description_ordinal=q,
                        location_ordinal=n,code=actual,code_key=k(actual),description=d['WHDescription'],description_key=k(d['WHDescription']),
                        logisticslocation=l.get('LogisticsLocation'),**{'ll'+str(v):l.get('LL'+str(v)) for v in range(1,6)}))
        return result

    def assert_bag(self,actual,expected):
        from mta.serialization import digest
        self.assertEqual(sorted(actual,key=digest),sorted(expected,key=digest))

    def complete(self,positive,*,boundary=None):
        from mta.presentation import scoped_expedite_queries as module
        from mta.runtime.scope_revisions import require_current
        self.external_boundary=boundary
        self.parents(positive=positive,counter=True);self.bound=self.binding();before=require_current(self.run)
        facts=self.bound.reports.rows('ExpediteDispatches');self.assertTrue(facts)
        self.assertTrue(all(r[n] is None for r in facts for n in ('BRAge','BRAgeRedCount','BRAgeBlackCount')))
        counts={}
        for direction,branch in product(('parent','child'),('dispatch','availability')):
            actual=self.fetch(module.grid_occurrences(self.run,direction,branch,read_binding=self.bound))
            self.assert_bag(actual,self.grid(direction,branch));counts[direction+'_'+branch]=len(actual)
        actual=self.fetch(module.custom_occurrences(self.run,read_binding=self.bound))
        self.assert_bag(actual,self.custom());counts['custom']=len(actual)
        for direction in ('parent','child'):
            for family in (('critical','receiving','nil_stock','chronic') if direction=='parent' else ('critical','receiving')):
                actual=self.fetch(module.members(self.run,direction,family,read_binding=self.bound))
                self.assert_bag(actual,self.members(direction,family));counts[direction+'_'+family]=len(actual)
                if family=='chronic':self.assertEqual(actual,[])
        self.assertEqual(require_current(self.run),before)
        print(json.dumps(dict(positive_external_parent_stock=positive,boundary=boundary,expedite_facts=facts,grains=counts)),flush=True)
        return counts

    def test_actual_default_all_complete_join_bags_and_null_age_counter_neutrality(self):self.complete(False)

    def test_actual_declared_positive_parent_stock_all_complete_join_bags(self):self.complete(True)

    def test_actual_first_known_zero_child_stock_dispatch_is_positive(self):
        counts=self.complete(True,boundary='dispatch')
        self.assertGreater(counts['parent_dispatch'],0);self.assertGreater(counts['child_dispatch'],0)
        self.assertGreater(counts['custom'],0);self.assertGreater(counts['parent_critical'],0)

    def test_actual_parent_stock_consumption_availability_is_positive(self):
        counts=self.complete(False,boundary='availability')
        self.assertGreater(counts['parent_availability'],0);self.assertGreater(counts['child_availability'],0)
        self.assertGreater(counts['parent_nil_stock'],0)

    def test_owned_empty_expedite_facts_keep_all_declared_relations_empty(self):
        from mta.presentation import scoped_expedite_queries as module
        from mta.runtime.scope_revisions import require_current
        self.external_boundary='empty';self.parents(counter=True);self.bound=self.binding()
        self.assertEqual(self.bound.reports.rows('ExpediteDispatches'),[])
        before=require_current(self.run)
        for direction,branch in product(('parent','child'),('dispatch','availability')):
            self.assertEqual(self.fetch(module.grid_occurrences(self.run,direction,branch,read_binding=self.bound)),[])
        self.assertEqual(self.fetch(module.custom_occurrences(self.run,read_binding=self.bound)),[])
        for direction in ('parent','child'):
            for family in (('critical','receiving','nil_stock','chronic') if direction=='parent' else ('critical','receiving')):
                self.assertEqual(self.fetch(module.members(self.run,direction,family,read_binding=self.bound)),[])
        self.assertEqual(require_current(self.run),before)

    def test_only_fact_relation_substitution_changes_original_full_sql(self):
        from mta.presentation import scoped_expedite_queries as module,planning_expedite_preparation as grids
        from mta.presentation import planning_expedite_custom_preparation as custom,planning_expedite_chart_preparation as charts
        self.parents();self.bound=self.binding()
        from contextlib import ExitStack
        with ExitStack() as stack:
            for original in (grids,charts):stack.enter_context(patch.object(original,'admitted_sources',return_value={n:self.bound.query(n) for n in ('bpr_master','git_master')}))
            for original in (grids,charts,custom):stack.enter_context(patch.object(original,'image_query',side_effect=lambda run,path:self.bound.image_query(path)))
            stack.enter_context(patch('mta.presentation.daily_preparation.source_digest',return_value=self.bound.sources.source_digest))
            calls=[('A',module.grid_occurrences(self.run,d,b,read_binding=self.bound),grids.grid_occurrences(self.run,d,b)) for d,b in product(('parent','child'),('dispatch','availability'))]
            calls+=[('B',module.custom_occurrences(self.run,read_binding=self.bound),custom.production_custom_occurrences(self.run))]
            calls+=[('E',module.members(self.run,d,f,read_binding=self.bound),charts.members(self.run,d,f)) for d in ('parent','child') for f in (('critical','receiving','nil_stock','chronic') if d=='parent' else ('critical','receiving'))]
        fact,params=self.bound.fact_query('ExpediteDispatches')
        for alias,actual,original in calls:
            table='"fresh_mta_expediterow"' if alias=='A' else 'fresh_mta_expediterow'
            literal=alias+' AS (SELECT * FROM mta.'+table+' WHERE run_id=%s)'
            self.assertEqual(original[0].count(literal),1)
            self.assertEqual(original[1][0],self.run.pk)
            self.assertEqual(actual,(original[0].replace(literal,alias+' AS ('+fact+')'),[*params,*original[1][1:]]))

    def test_missing_nms_wrong_run_and_invalid_grain_deny_without_terminal_fallback(self):
        from mta.presentation import scoped_expedite_queries as module
        from mta.presentation.context import PublicationUnavailable
        self.parents();self.bound=self.binding();without=self.binding(nms=False)
        with self.assertRaises(PublicationUnavailable):module.custom_occurrences(self.run,read_binding=without)
        self.assertEqual(self.fetch(module.grid_occurrences(self.run,'child','dispatch',read_binding=without)),self.fetch(module.grid_occurrences(self.run,'child','dispatch',read_binding=self.bound)))
        for call in (lambda:module.grid_occurrences(self.run,'invalid','dispatch',read_binding=self.bound),
                lambda:module.members(self.run,'child','chronic',read_binding=self.bound)):
            with self.assertRaises(ValueError):call()
        for call in (lambda:module.grid_occurrences(self.run,'parent','dispatch',read_binding=None),
                lambda:module.custom_occurrences(self.run,read_binding=None),
                lambda:module.members(self.run,'parent','receiving',read_binding=None)):
            with self.assertRaisesRegex(PublicationUnavailable,'scoped_binding_required'):call()
        original=self.bound;self.parents()
        with self.assertRaisesRegex(PublicationUnavailable,'phase_owner_differs'):
            module.members(self.run,'parent','receiving',read_binding=original)
