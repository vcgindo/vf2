"""Full native capture recovery must retain its report request; scopes stay fenced."""
import os
os.environ.setdefault('VF_SECRET_KEY','unit-contract-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch
from mta.runtime import production_daily,runtime_report_request as contract
from tests.test_runtime_report_request import fixture


class ReachedOwnedSource(Exception):pass


class PlacementFullRetryTests(unittest.TestCase):
    def request(self,scope):
        return contract.request(scope,'retry-contract',runtime_reports=fixture())

    @patch('release.native_identity.require_current',return_value={'local-test':'same-release'})
    def test_only_qualified_full_retry_reaches_unchanged_owned_source_checks(self,_identity):
        with patch('mta.runtime.models.ProductionInitialization.objects.select_related') as query:
            query.return_value.get.side_effect=ReachedOwnedSource
            args=dict(initialization_id='10000000-0000-4000-8000-000000000001',source_digest='a'*64,
                configuration_digest='b'*64,pick_output_root='/owned',execution_revision='new-retry',retry_capture_id='old-failed')
            for scope in ('UptoBPR','UptoDBM'):
                with self.subTest(scope=scope),self.assertRaisesRegex(ValueError,'scope attempt'):
                    production_daily.inspect_execution(b'', 'c'*64,scope_request=self.request(scope),**args)
            query.assert_not_called()
            with self.assertRaises(ReachedOwnedSource):
                production_daily.inspect_execution(b'', 'c'*64,scope_request=self.request('Full'),**args)
            query.return_value.get.assert_called_once()
            with self.assertRaisesRegex(ValueError,'scope attempt'):
                production_daily.inspect_execution(b'', 'c'*64,scope_request=self.request('Full'),
                    report_disposition='unapproved-replacement',**args)

    @patch('release.native_identity.require_current',return_value={'local-test':'same-release'})
    def test_retry_reconstructs_exact_captured_report_request(self,_identity):
        request=self.request('Full')
        with patch.object(production_daily,'inspection_request',side_effect=ReachedOwnedSource) as reconstruct:
            with self.assertRaises(ReachedOwnedSource):
                production_daily.inspect_retry(b'raw','a'*64,None,None,None,None,None,'retry','/owned',
                    lambda *args:self.fail('unexpected diagnostic'),scope_request=request)
            self.assertEqual(reconstruct.call_args.kwargs,{'scope_request':request})

    def test_ordinary_retry_retains_original_reconstruction_call(self):
        with patch.object(production_daily,'inspection_request',side_effect=ReachedOwnedSource) as reconstruct:
            with self.assertRaises(ReachedOwnedSource):
                production_daily.inspect_retry(b'raw','a'*64,None,None,None,None,None,'retry','/owned',lambda *args:None)
            self.assertEqual(reconstruct.call_args.kwargs,{})

    @patch('release.native_identity.require_current',return_value={'local-test':'same-release'})
    def test_full_retry_passes_current_capture_cut_without_replacing_frozen_origin(self,_identity):
        source=SimpleNamespace(digest='a'*64)
        owner=SimpleNamespace(pk='10000000-0000-4000-8000-000000000001',source=source,configuration_digest='b'*64)
        parent=SimpleNamespace(pk='10000000-0000-4000-8000-000000000002',output_digest='c'*64)
        frame=dict(profile={'import_non_nms':False},opening={})
        cut=object();day=dict(business_date='2037-04-10',raw_non_nms=[])
        for request,retry,prepared in ((self.request('Full'),'frozen-failed',cut),
                                      (None,'frozen-ordinary',None),(None,None,cut)):
            with self.subTest(scope=request and request['scope'],retry=retry),ExitStack() as stack:
                for target,value in (
                    ('mta.runtime.daily_preparation.prepare',b'raw'),
                    ('mta.runtime.production_daily.inspect_execution',({},owner,parent,frame)),
                    ('mta.runtime.production_preflight.require',None),
                    ('mta.runtime.production_daily.decode',{'consumer_opening':None}),
                    ('mta.mdm.production_families.require_initialization',None),
                    ('mta.runtime.production_daily._daily_initialization',frame),
                    ('mta.runtime.production_daily.working_day',day),
                    ('mta.mdm.location_transition.admit',None)):
                    stack.enter_context(patch(target,return_value=value))
                owners=stack.enter_context(patch('mta.runtime.models.ProductionInitialization.objects.select_related'))
                owners.return_value.get.return_value=owner
                stack.enter_context(patch('mta.runtime.models.CalculationRun.objects.get',return_value=parent))
                readiness=stack.enter_context(patch('mta.runtime.ingestion_admission.preparation_source',return_value=cut))
                execute=stack.enter_context(patch('mta.runtime.temporal.execute_day',return_value='owned-result'))
                actual=production_daily.execute(b'raw','d'*64,initialization_id=owner.pk,
                    source_digest=source.digest,configuration_digest=owner.configuration_digest,
                    execution_revision='new-retry',pick_output_root='/owned',predecessor_id=parent.pk,
                    predecessor_output_digest=parent.output_digest,retry_capture_id=retry,scope_request=request)
                self.assertEqual(actual,'owned-result')
                self.assertIs(execute.call_args.kwargs['prepared_state'],prepared)
                self.assertEqual(execute.call_args.kwargs['mdm_retry'],retry)
                self.assertEqual(execute.call_args.kwargs['scope_request'],request)
                self.assertIs(execute.call_args.kwargs['mdm_source'],source if retry is None else None)
                if prepared is not None:readiness.assert_called_once_with(source.digest)
                else:readiness.assert_not_called()
