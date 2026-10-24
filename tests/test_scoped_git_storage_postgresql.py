"""Owned rollback-only GIT persistence and normal consumer components."""
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_git_postgresql as fixtures
from tests import test_scoped_transit_storage_postgresql as full_fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedGitStorageTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr','positive','parents','scopes','target','occurrences'):
        locals()[_name]=getattr(fixtures.ScopedGitTests,_name)
    for _name in ('prepare_dbm','finish','publication_opening'):
        locals()[_name]=getattr(full_fixtures.ScopeTransitStorageTests,_name)

    def prepare(self):
        from mta.presentation.scoped_git import prepare
        return prepare(self.report.pk,expected_report_digest=self.report.digest,
            expected_source_digest=self.prepared.digest,transit_generation_id=self.transit.pk,
            expected_transit_digest=self.transit.digest,action_revision=0)

    def binding(self,row):
        from mta.presentation.scoped_git import bind
        return bind(row.pk,expected_digest=row.digest,action_revision=0)

    def read(self,bound,payload,*,count=False,products=None,locations=None):
        from mta.presentation import planning_git_sql as reader
        p,l=self.scopes()
        with patch.object(reader,'scope',return_value=(p if products is None else products,l if locations is None else locations)), \
                patch.object(reader,'_projected_attributes',side_effect=AssertionError('terminal attributes')), \
                patch.object(reader,'image_query',side_effect=AssertionError('terminal image')):
            return reader.grid(self.run,payload,count=count,read_binding=bound)

    def test_complete_occurrences_sql_readback_repeat_and_counter_neutrality(self):
        from django.db import connection
        from mta.presentation import scoped_git as module
        from mta.runtime.models import PlanningGitOccurrence,PlanningGitProjection
        from mta.runtime.scope_revisions import require_current
        self.parents(counter=True);before=require_current(self.run)
        expected=sorted(self.occurrences(),key=lambda r:tuple((r[k] is not None,r[k]) for k in module.ORDER))
        expected=[dict(r,ordinal=i) for i,r in enumerate(expected)]
        row=self.prepare();bound=self.binding(row)
        self.assertEqual(bound.rows(),expected)
        self.assertEqual(sorted(r['transporter_ordinal'] for r in self.target(bound.rows())),[0,1,2,3])
        sql,params=bound.query()
        with connection.cursor() as c:
            c.execute(sql+' ORDER BY R.ordinal',params);names=[col[0] for col in c.description]
            actual=[dict(zip(names,r)) for r in c.fetchall()]
        self.assertTrue(all(r.pop('run_id')==self.run.pk for r in actual))
        self.assertEqual(actual,expected)
        # Patch a dependency invoked only by the producer, leaving recipe source
        # identity unchanged; repeat must read existing sealed rows.
        with patch('mta.presentation.planning_git_preparation.admitted_sources',side_effect=AssertionError('rebuild')):
            self.assertEqual(self.prepare().pk,row.pk)
        self.assertEqual(require_current(self.run),before)
        self.assertFalse(PlanningGitOccurrence.objects.filter(run=self.run).exists())
        self.assertFalse(PlanningGitProjection.objects.filter(run=self.run).exists())

    def test_normal_parent_complete_wire_paging_and_directional_child_count(self):
        from mta.presentation import planning_git_sql as reader
        from mta.presentation.permissions import PermissionCodes
        from mta.presentation.context import PublicationUnavailable
        self.parents();bound=self.binding(self.prepare())
        actual=self.read(bound,dict(type='parent'))
        masters={(r['rationed_ordinal'],r['standard_ordinal']):r for r in self.bound.rows('git_master')}
        attrs=self.bound.sources.rows('closing/importer/SkuAttributeData')
        aliases=dict(st='Status',sc='SKUCode',wc='WhCode',t='Tags',pwc='ParentWhCode',n='Norm',vn='VirtualNorm',
            stk='Stock',g='Git',pip='PhysicalInventoryPen',pic='PhysicalInventoryColor',plp='PipelineInventoryPen',
            plc='PipelineInventoryColor',rq='Req',pr='Price')
        numeric={'n','vn','stk','g','pip','plp','rq','pr','eoc','v','wt'}
        nested=dict(lc='O-1',cd='2037-04-08',slt=None,tlt=1,ag=2,eta=None,cl=None,qty=4,remarks=None)
        expected=[]
        for h in self.target(bound.rows()):
            a=masters[h['rationed_ordinal'],h['standard_ordinal']];c=attrs[h['sku_ordinal']]
            record={alias:a[name] for alias,name in aliases.items()}
            record.update(skd=h['sku_description'],wcd=h['location_description'],prn=h['parent_description'],
                eoc=c['ElephantOrderCapping'],v=c['Volume'],wt=c['Weight'],AgeingOrder=None,
                **{p+str(i):h[p+str(i)] for p in ('sl','ll') for i in range(1,6)})
            for name in numeric:
                if record[name] is not None:record[name]=float(record[name])
            for _ in range(6):expected.append(dict(record,rn=len(expected)+1,transit=[dict(nested),dict(nested)]))
        self.assertEqual(len(expected),24)
        self.assertEqual(actual,dict(data=expected,uiConfig=actual['uiConfig']))
        # Run the unchanged default consumer SQL on the same exact typed
        # relations. This is a controlled SQL equivalence check, not a claim
        # that a partial generation has passed Full publication admission.
        p,l=self.scopes()
        with patch.object(reader,'admitted_git',return_value={'row':bound.query()}), \
                patch.object(reader,'admitted_sources',return_value={'git_master':self.bound.query('git_master')}), \
                patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch.object(reader,'image_rows',return_value=self.bound.transit.rows('InTransitData')), \
                patch.object(reader,'image_query',side_effect=lambda run,path:bound.image_query(path)):
            self.assertEqual(reader.grid(self.run,dict(type='parent'),resolved_scope=(bound.attributes(),None,p,l)),actual)
        page=self.read(bound,dict(type='parent',paginationParameter=dict(pageNumber=2,recordsPerPage=5)))
        self.assertEqual(page,dict(data=expected[5:10],uiConfig=actual['uiConfig']))
        self.assertEqual(self.read(bound,dict(type='parent'),count=True),[dict(locationwise=24)])
        positive=dict(type='parent',filters=dict(availabilityFilter=dict(filters=[
            dict(attributeName='git',operator='greaterthan',value='0')])))
        self.assertEqual(self.read(bound,positive),actual)
        self.assertEqual(self.read(bound,dict(type='child'),count=True),[dict(locationwise=24,transporterwise=1)])
        self.assertEqual(self.read(bound,dict(type='child'),count=True,locations=PermissionCodes({'OWN-WH8':3})),
            [dict(locationwise=0,transporterwise=0)])
        with self.assertRaisesRegex(PublicationUnavailable,'LEG-GIT-CHILD-TRANSPORTER-INVALID-SQL'):
            self.read(bound,dict(type='child'))
        payload=dict(type='child',filters=dict(productFilter=dict(filters=[dict(attributeName='p1',operator='equalto',value='C')])))
        with self.assertRaisesRegex(PublicationUnavailable,'LEG-GIT-FILTER-INVALID-SQL'):
            self.read(bound,payload,count=True)
        payload=dict(type='parent',filters=dict(productFilter=dict(filters=[dict(attributeName='sku',value='ABSENT')])))
        self.assertEqual(self.read(bound,payload)['data'],[])
        self.assertEqual(self.read(bound,dict(type='parent'),products=PermissionCodes({}))['data'],[])

    def test_empty_transit_keeps_location_occurrence_and_settles_child_wire(self):
        from mta.presentation.permissions import PermissionCodes
        self.parents(empty=True);bound=self.binding(self.prepare())
        rows=self.target(bound.rows());self.assertEqual(len(rows),1)
        self.assertIsNone(rows[0]['transporter_ordinal'])
        actual=self.read(bound,dict(type='child'))
        self.assertEqual(len(actual['locationWise']['data']),6)
        self.assertTrue(all(r['transit']==[] and r['AgeingOrder'] is None for r in actual['locationWise']['data']))
        self.assertEqual(actual['transporterWise']['data'],[])
        self.assertEqual(self.read(bound,dict(type='child'),count=True),[dict(locationwise=6,transporterwise=0)])
        self.assertEqual(self.read(bound,dict(type='child'),count=True,products=PermissionCodes({})),
            [dict(locationwise=0,transporterwise=0)])

    def test_sql_immutability_unsealed_commit_and_dependency_mismatch_denials(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation import scoped_git as module
        from mta.runtime.models import ScopeGitGeneration,ScopeGitOccurrence
        from mta.presentation.context import PublicationUnavailable
        self.parents();row=self.prepare();bound=self.binding(row)
        for statement in ('UPDATE mta.fresh_mta_scopegitgeneration SET digest=digest WHERE id=%s',
                'DELETE FROM mta.fresh_mta_scopegitgeneration WHERE id=%s',
                'UPDATE mta.fresh_mta_scopegitoccurrence SET ordinal=ordinal WHERE generation_id=%s',
                'DELETE FROM mta.fresh_mta_scopegitoccurrence WHERE generation_id=%s'):
            with self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as c:c.execute(statement,[row.pk])
        for table in ('fresh_mta_scopegitgeneration','fresh_mta_scopegitoccurrence'):
            with self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as c:c.execute('TRUNCATE mta.'+table)
        with self.assertRaisesRegex(DatabaseError,'requires its unsealed generation'),transaction.atomic():
            values=dict(bound.rows()[0]);values['ordinal']=len(bound.rows())
            ScopeGitOccurrence.objects.create(generation=row,**values)
        values={f.attname:getattr(row,f.attname) for f in ScopeGitGeneration._meta.local_fields
            if f.name not in ('id','metadata','digest','sealed','sealed_at','created_at')}
        for changes in (dict(source_projection_digest='f'*64),dict(transit_generation_digest='f'*64),dict(recipe_digest='f'*64)):
            with self.assertRaisesRegex(DatabaseError,'exact sealed|Unsealed scope'),transaction.atomic():
                candidate=ScopeGitGeneration(**dict(values,**changes))
                with module._owner(candidate.pk):
                    candidate.save(force_insert=True)
                    with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
        with self.assertRaises(PublicationUnavailable):module.bind(row.pk,expected_digest='f'*64,action_revision=0)
        with connection.cursor() as c:
            c.execute('SET CONSTRAINTS ALL IMMEDIATE')
            c.execute('SET CONSTRAINTS ALL DEFERRED')
        with transaction.atomic():
            with connection.cursor() as c:c.execute('ALTER TABLE mta.fresh_mta_scopegitoccurrence DISABLE TRIGGER scope_git_rows_insert')
            with self.assertRaisesRegex(PublicationUnavailable,'guard_coverage'):self.binding(row)
            transaction.set_rollback(True)
        self.assertEqual(self.binding(row).rows(),bound.rows())
        self.parents()
        with self.assertRaisesRegex(PublicationUnavailable,'phase_owner_differs'):
            self.read(bound,dict(type='parent'))

    def test_late_seal_failure_rolls_back_parent_rows_and_input_counters(self):
        from mta.presentation import scoped_git as module
        from mta.runtime.models import ScopeGitGeneration,ScopeGitOccurrence
        from mta.runtime.scope_revisions import require_current
        self.parents(counter=True);before=require_current(self.run)
        def failure(identifier):raise OSError('GIT readback interrupted')
        with patch.object(module,'_receipt',side_effect=failure),self.assertRaisesRegex(OSError,'interrupted'):
            self.prepare()
        self.assertEqual(ScopeGitGeneration.objects.count(),0);self.assertEqual(ScopeGitOccurrence.objects.count(),0)
        self.assertEqual(require_current(self.run),before)
        self.assertTrue(self.binding(self.prepare()).rows())

    def test_actual_sleep_invalidates_fresh_binding_but_keeps_inflight_rows(self):
        from mta.runtime.scoped_actions import record
        from mta.runtime.scope_execution import _close_attempt,_setting
        from tests.production_h3_fixture import SEASON,CHILD
        from mta.presentation.context import PublicationUnavailable
        self.action_case=True;self.parents();row=self.prepare();bound=self.binding(row);before=bound.rows()
        with _setting('fresh.scope_worker',self.attempt.worker_token):_close_attempt(self.attempt,self.run,'RELEASED',{})
        event=record(self.run.pk,phase_id=self.receipt.pk,phase_digest=self.receipt.digest,expected_revision=0,
            operation='SLEEP',selected=[[SEASON,CHILD]],timestamp='2037-04-10T10:00:00',
            actor='owned-git-component',idempotency_key='git-sleep')
        self.assertTrue(event.state_sealed)
        with self.assertRaises(PublicationUnavailable):self.binding(row)
        self.assertEqual(bound.rows(),before)

    def test_same_actual_run_full_finish_preserves_partial_occurrences(self):
        from mta.runtime.models import RunPhaseAcceptance,DailyTransitRow
        from mta.presentation import scoped_prepared,scoped_report_storage as facts,scoped_transit_storage
        self.full_factor=True;self.positive();self.owner(claim=False);self.prepare_dbm()
        self.receipt=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR')
        self.transit=scoped_transit_storage.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.report=facts.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.prepared=scoped_prepared.prepare(self.report.pk,expected_report_digest=self.report.digest,action_revision=0)
        row=self.prepare();bound=self.binding(row);before=bound.rows()
        self.assertTrue(before)
        finished=self.finish();self.assertEqual((finished.pk,finished.status),(row.run_id,'SUCCEEDED'))
        self.assertTrue(DailyTransitRow.objects.filter(run=finished).exists())
        self.assertEqual(self.binding(row).rows(),before)

    def test_scalar_contract_matches_full_occurrences(self):
        from mta.runtime.models import PlanningGitOccurrence,ScopeGitOccurrence
        for field in PlanningGitOccurrence._meta.local_fields:
            if field.name not in ('id','run'):
                self.assertEqual(ScopeGitOccurrence._meta.get_field(field.name).deconstruct()[1:],field.deconstruct()[1:])
