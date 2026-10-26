"""Full native capture recovery must retain its report request; scopes stay fenced."""
import os
os.environ.setdefault('VF_SECRET_KEY','unit-contract-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
import unittest
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
