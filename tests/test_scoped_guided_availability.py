"""Current cutoff against independently owned inherited availability history."""
from datetime import timedelta
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import patch

from tests.test_scoped_btr import fixture, Codes
from mta.presentation import scoped_guided_availability as subject, insight_history_sql as reader
from mta.presentation.context import PublicationUnavailable


class ScopedAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.btr=fixture(); self.run=self.btr.run
        self.view=Obj(run=self.run,run_id=self.run.pk,
            reference=Obj(metadata={'runtime_reports':{'schema':'fresh-registered-placement-read-configuration-v1'}}))
        self.receipt=Obj(source_digest='a'*64,schema_digest='b'*64)
        self.bound=subject.AvailabilityBinding(self.view,self.btr,self.receipt)
        self.attrs={'SkuAttributeData':[],'LocationAttributeData':[]}

    def test_owner_reuse_requires_same_request_connection_role_and_stable_stamp(self):
        from mta.presentation.request_scope import read_request
        run=self.btr.predecessor;run._meta=Obj()
        physical=object();database=Obj(connection=physical)
        with patch.object(subject,'connection',database), \
                patch('mta.presentation.identity_reuse.stamp',return_value=('snapshot','role-a')) as stamp, \
                patch.object(subject,'_require_owner',return_value=self.receipt) as verify:
            with read_request('/api/mta/AvailabilityTrend'):
                self.assertIs(subject.require_owner(run),self.receipt)
                self.assertIs(subject.require_owner(run),self.receipt)
                self.assertEqual(verify.call_count,1)
                stamp.return_value=('snapshot','role-b')
                subject.require_owner(run)
                self.assertEqual(verify.call_count,2)
                database.connection=object()
                subject.require_owner(run)
                self.assertEqual(verify.call_count,3)
                stamp.return_value=None
                subject.require_owner(run);subject.require_owner(run)
                self.assertEqual(verify.call_count,5)
            stamp.return_value=('snapshot','role-b')
            with read_request('/api/mta/AvailabilityTrend'):
                subject.require_owner(run)
                self.assertEqual(verify.call_count,6)
            subject.require_owner(run);subject.require_owner(run)
            self.assertEqual(verify.call_count,8)
            with read_request('/api/mta/AvailabilityTrend'):
                stamp.side_effect=[('before',),('after',)]
                subject.require_owner(run)
                self.assertEqual(verify.call_count,10)

    def test_bind_and_read_reuse_owner_but_not_live_aggregate_permission_validation(self):
        from mta.presentation.request_scope import read_request
        self.btr.predecessor._meta=Obj()
        with patch.object(subject,'connection',Obj(connection=object())), \
                patch('mta.presentation.identity_reuse.stamp',return_value=('snapshot','runtime-role')), \
                patch.object(subject,'_require_owner',return_value=self.receipt) as verify, \
                patch.object(subject.scoped_btr,'bind',return_value=self.btr), \
                patch.object(subject.hierarchy,'selected_manifest',return_value=None), \
                patch('mta.runtime.models.ReportAggregateReceipt.objects') as aggregate_owner, \
                patch('mta.presentation.guided_aggregates.read_aggregate',return_value=[]) as aggregate, \
                patch.object(subject.guided_history_prepared,'_prepared_owner',side_effect=AssertionError('duplicate owner')):
            aggregate_owner.filter.return_value.first.return_value=None
            with read_request('/api/mta/AvailabilityTrend'):
                bound=subject.bind(self.view)
                for _ in range(2):
                    self.assertEqual(bound.read(self.run.business_date,None,Codes(['S']),Codes(['W']),
                        'availability-trend',minimum_age=None,payload={}),[])
                self.assertEqual(verify.call_count,1)
                self.assertEqual(aggregate.call_count,2)

    def test_missing_changed_history_and_guards_deny_before_empty_permissions(self):
        with patch.object(subject.scoped_btr,'bind',return_value=self.btr), \
                patch.object(subject.hierarchy,'selected_manifest',return_value=None), \
                patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch('mta.presentation.daily_preparation.source_digest',return_value='a'*64), \
                patch('mta.presentation.guided_history_fields.schema_digest',return_value='b'*64), \
                patch('mta.runtime.guided_history_schema.verify_guards') as guard, \
                patch('mta.runtime.models.ReportAggregateReceipt.objects') as aggregate_owner, \
                patch('mta.runtime.models.GuidedHistoryPreparedProjection.objects') as manager:
            aggregate_owner.filter.return_value.first.return_value=None
            manager.filter.return_value.first.return_value=self.receipt
            self.assertIs(subject.bind(self.view).receipt,self.receipt)
            manager.filter.assert_called_with(run=self.btr.predecessor,family='availability')
            manager.filter.return_value.first.return_value=None
            with self.assertRaisesRegex(PublicationUnavailable,'receipt_differs'): subject.bind(self.view)
            manager.filter.return_value.first.return_value=self.receipt
            self.receipt.source_digest='c'*64
            with self.assertRaisesRegex(PublicationUnavailable,'receipt_differs'): subject.bind(self.view)
            self.receipt.source_digest='a'*64; guard.side_effect=ValueError('changed')
            with self.assertRaisesRegex(PublicationUnavailable,'guards_differ'): subject.bind(self.view)

    def test_optional_aggregate_has_independent_live_receipt_and_guard_validation(self):
        row=Obj(source_digest='aggregate-source',recipe_digest='aggregate-recipe',rows_digest='rows',members_digest='members')
        with patch.object(subject.scoped_btr,'bind',return_value=self.btr), \
                patch.object(subject.hierarchy,'selected_manifest',return_value=None), \
                patch.object(subject,'require_owner',return_value=self.receipt), \
                patch('mta.runtime.models.ReportAggregateReceipt.objects') as manager, \
                patch('mta.presentation.guided_aggregates.source_binding',return_value=row.source_digest) as source, \
                patch('mta.presentation.guided_aggregates.recipe_digest',return_value=row.recipe_digest), \
                patch('mta.runtime.report_aggregate_schema.verify_guards') as guards:
            manager.filter.return_value.first.return_value=row
            for _ in range(2):
                self.assertEqual(subject.bind(self.view).aggregate,dict(source='aggregate-source',recipe='aggregate-recipe',rows='rows',members='members'))
            self.assertEqual(source.call_count,2);self.assertEqual(guards.call_count,2)
            row.source_digest='changed'
            with self.assertRaisesRegex(PublicationUnavailable,'aggregate_receipt_changed'):subject.bind(self.view)
            row.source_digest='aggregate-source';guards.side_effect=ValueError('guard changed')
            with self.assertRaisesRegex(ValueError,'guard changed'):subject.bind(self.view)
            manager.filter.return_value.first.return_value=None
            self.assertIsNone(subject.bind(self.view).aggregate)

    def test_delegation_keeps_parent_owner_current_cutoff_and_original_payload(self):
        with patch('mta.presentation.native_publication.enabled',return_value=False), \
                patch.object(subject.AvailabilityBinding,'attributes',return_value=self.attrs), \
                patch.object(reader,'scope',return_value=(Codes(['S']),Codes(['W']))), \
                patch.object(subject.guided_history_prepared,'read_prepared') as prepared:
            for kind,payload,days,age in (
                ('availability-trend',{},90,None),
                ('availability-trend',{'horison':7},7,None),
                ('availability-trend',{'horizon':3,'horison':8},3,None),
                ('availability-ageing',{},30,1),
                ('availability-ageing',{'horizon':4,'ageing':'3'},4,3)):
                prepared.return_value=[('2026-10-23',None,75)] if age is None else [('2026-10-23',2,3,4)]
                result=reader.read_history(self.run,payload,kind,read_binding=self.bound)
                args=prepared.call_args.args; kwargs=prepared.call_args.kwargs
                self.assertIs(args[0],self.btr.predecessor)
                self.assertEqual(args[1],self.run.business_date-timedelta(days=days))
                self.assertIs(kwargs['payload'],payload)
                self.assertEqual(kwargs['minimum_age'],age)
                self.assertEqual(result,([dict(week='2026-10-23',percentage=75)] if age is None else
                    [dict(date='2026-10-23',black=2,red=3,white=4)]))

    def test_empty_invalid_horizon_and_wrong_binding_do_not_fall_back(self):
        with patch('mta.presentation.native_publication.enabled',return_value=False), \
                patch.object(subject.AvailabilityBinding,'attributes',return_value=self.attrs), \
                patch.object(reader,'scope',return_value=(Codes(),Codes())), \
                patch.object(subject.guided_history_prepared,'read_prepared') as prepared, \
                patch.object(reader,'image_rows',side_effect=AssertionError('current Full source')):
            self.assertEqual(reader.read_history(self.run,{},'availability-trend',read_binding=self.bound),[])
            prepared.assert_not_called()
            for horizon in (0,91):
                with self.assertRaises(ValueError):
                    reader.read_history(self.run,{'horizon':horizon},'availability-trend',read_binding=self.bound)
            with self.assertRaisesRegex(PublicationUnavailable,'binding_differs'):
                reader.read_history(Obj(pk='foreign',business_date=self.run.business_date),{},
                    'availability-trend',read_binding=self.bound)
            prepared.return_value=None
            with self.assertRaisesRegex(PublicationUnavailable,'predecessor_not_prepared'):
                self.bound.read(self.run.business_date,None,Codes(['S']),Codes(['W']),
                    'availability-trend',minimum_age=None,payload={})
