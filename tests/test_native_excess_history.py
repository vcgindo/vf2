"""Focused ownership and coverage contracts for native Guided Excess history."""
import os
import unittest
from datetime import date
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import daily_native_prepared, native_excess_history
from mta.presentation.context import PublicationUnavailable
from mta.presentation.excess import PRODUCER_SHA


def run(day, predecessor=None):
    return NS(pk=uuid4(), business_date=day, predecessor=predecessor,
              predecessor_id=(predecessor.pk if predecessor else None))


class NativeExcessHistoryTests(unittest.TestCase):
    def receipt(self):
        return NS(producer_sha256=PRODUCER_SHA, source_digest='source',
                  rows_digest='rows', row_count=1)

    def test_identity_keeps_all_known_own_days_without_inventing_pre_root_history(self):
        root=run(date(2037,4,10));middle=run(date(2037,4,11),root);current=run(date(2037,4,12),middle)
        with patch('mta.presentation.native_publication.identity',
                side_effect=lambda item,verify_rows=False:dict(run=str(item.pk),initialization={'id':'own'})), \
                patch('mta.runtime.models.ExcessProjection.objects.get',return_value=self.receipt()) as projection:
            value=native_excess_history.identity(current)
        self.assertEqual([x['run_id'] for x in value['lineage']],list(map(lambda x:str(x.pk),(current,middle,root))))
        self.assertEqual(value['coverage_cutoff'],'2037-04-09')
        self.assertEqual(value['root_date'],'2037-04-10')
        self.assertEqual(value['coverage_days'],3)
        self.assertEqual(projection.call_count,3)
        native_excess_history.require_cutoff(value,date(2037,4,9))
        with self.assertRaisesRegex(PublicationUnavailable,'coverage_unavailable'):
            native_excess_history.require_cutoff(value,date(2037,4,8))

    def test_gap_wrong_initialization_and_missing_projection_fail(self):
        from mta.runtime.models import ExcessProjection
        root=run(date(2037,4,10));current=run(date(2037,4,12),root)
        with patch('mta.presentation.native_publication.identity',return_value={'initialization':{'id':'own'}}), \
                patch('mta.runtime.models.ExcessProjection.objects.get',return_value=self.receipt()):
            with self.assertRaisesRegex(PublicationUnavailable,'history_gap'):
                native_excess_history.identity(current)
        current.business_date=date(2037,4,11)
        with patch('mta.presentation.native_publication.identity',
                side_effect=lambda item,verify_rows=False:dict(initialization={'id':str(item.pk)})), \
                patch('mta.runtime.models.ExcessProjection.objects.get',return_value=self.receipt()):
            with self.assertRaisesRegex(PublicationUnavailable,'initialization_changed'):
                native_excess_history.identity(current)
        with patch('mta.presentation.native_publication.identity',return_value={'initialization':{'id':'own'}}), \
                patch('mta.runtime.models.ExcessProjection.objects.get',side_effect=ExcessProjection.DoesNotExist):
            with self.assertRaisesRegex(PublicationUnavailable,'projection_required'):
                native_excess_history.identity(current)

    def test_duplicate_run_identity_is_denied(self):
        root=run(date(2037,4,10));current=run(date(2037,4,11),root)
        root.pk=current.pk
        with patch('mta.presentation.native_publication.identity',return_value={'initialization':{'id':'own'}}), \
                patch('mta.runtime.models.ExcessProjection.objects.get',return_value=self.receipt()):
            with self.assertRaisesRegex(PublicationUnavailable,'duplicate_day'):
                native_excess_history.identity(current)

    def test_same_count_changed_projection_values_fail_full_readback(self):
        current=run(date(2037,4,12))
        with patch('mta.runtime.models.ExcessProjection.objects.get',return_value=self.receipt()), \
                patch('mta.presentation.selective.image_rows',return_value=[]), \
                patch('mta.presentation.excess_storage.read_excess',side_effect=ValueError('same-count digest differs')):
            with self.assertRaisesRegex(PublicationUnavailable,'readback_changed'):
                native_excess_history._projection(current,verify_rows=True)

    def test_locked_layer_checks_predecessor_projection_without_full_predecessor_audit(self):
        root = run(date(2037, 4, 10))
        current = run(date(2037, 4, 11), root)
        for locked in (False, True):
            with patch('mta.presentation.report_verification.check_active_owner', return_value=locked) as owner, \
                    patch('mta.presentation.native_publication.identity',
                          return_value={'initialization': {'id': 'own'}}) as identity, \
                    patch.object(native_excess_history, '_projection', return_value={}) as projection:
                native_excess_history.identity(current, verify_rows=True)
            owner.assert_called_once_with(root)
            self.assertEqual([call.kwargs['verify_rows'] for call in identity.call_args_list], [True, not locked])
            self.assertEqual([call.kwargs['verify_rows'] for call in projection.call_args_list], [True, True])

    def test_native_insert_carries_fact_owner_and_strict_cutoff(self):
        current = run(date(2037, 4, 12))
        history = {'storage_cutoff': '2037-04-10', 'lineage': [
            {'run_id': str(current.pk), 'ordinal': 0},
            {'run_id': str(uuid4()), 'ordinal': 1},
        ]}
        cursor = MagicMock()
        with patch.object(daily_native_prepared, 'image_query',
                          side_effect=lambda _run, path: ('SELECT '+path, [path])):
            daily_native_prepared._history_excess(cursor, current, history)
        query, params = cursor.execute.call_args.args
        self.assertIn('a.run_id fact_run_id', query)
        self.assertIn('a."ReportDate">%s', query)
        self.assertIn('(run_id,ordinal,fact_run_id,fact_ordinal', query)
        self.assertEqual(params[-2:], ['2037-04-10', current.pk])

    def test_projection_verifies_against_typed_output_images(self):
        current = run(date(2037, 4, 12))
        with patch('mta.runtime.models.ExcessProjection.objects.get',
                   return_value=self.receipt()), \
             patch('mta.presentation.selective.image_rows',
                   side_effect=[['rationed'], ['standards']]) as images, \
             patch('mta.presentation.excess_storage.read_excess',
                   return_value=[{'ReportDate': '2037-04-12'}]) as read:
            native_excess_history._projection(current, verify_rows=True)
        self.assertEqual([call.args[1] for call in images.call_args_list], [
            'reports/bpr/vf_RationedReqReport', 'closing/dbm/SKULocStandardAttributes'])
        self.assertEqual(read.call_args.kwargs['output'], {
            'BPRReports': [{'vf_RationedReqReport': ['rationed']}],
            'ClosingState': [{'dbm': {'SKULocStandardAttributes': ['standards']}}]})


if __name__ == '__main__':
    unittest.main()
