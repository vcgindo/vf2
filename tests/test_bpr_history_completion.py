"""Bounded history semantics and terminal dispatch; actual guards use PostgreSQL."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from mta.runtime import bpr_history_completion as history
from mta.serialization import storage
from tests.test_operational_bor import bor_row, rrr_row


class BprHistorySemanticsTests(unittest.TestCase):
    def test_retention_boundary_nulls_duplicates_order_and_no_input_mutation(self):
        current = {'BORWithOrderAllocation': [bor_row(), bor_row()],
                   'RRR_OrderAllocation': [rrr_row(), rrr_row()]}
        opening = {history.NAMES[0]: [dict(bor_row(), ReportDate='2026-07-26'),
                                      dict(bor_row(), ReportDate='2026-07-27')],
                   history.NAMES[1]: [dict(rrr_row(), ReportDate='2026-07-26'),
                                      dict(rrr_row(), ReportDate='2026-07-27')]}
        before = deepcopy((opening, current))
        result = history.project(opening, current, '2026-10-24', history.AUTHORITY['policy'])
        self.assertEqual((opening, current), before)
        for name, rows in result.items():
            self.assertEqual([str(row['ReportDate']) for row in rows], ['2026-07-27', '2026-10-24', '2026-10-24'])
            self.assertEqual(rows[-1], rows[-2])
        self.assertIsNone(result[history.NAMES[1]][-1]['AllocationFor'])
        self.assertIsNone(result[history.NAMES[1]][-1]['VirtualNorm'])
        self.assertEqual(storage(result[history.NAMES[0]])[-1]['DispatchPen'], '50.00')

    def test_missing_history_is_not_empty(self):
        with self.assertRaises(KeyError):
            history.project({}, {'BORWithOrderAllocation': [], 'RRR_OrderAllocation': []},
                            '2026-10-24', history.AUTHORITY['policy'])

    def test_publication_binds_completion_without_mutating_receipt(self):
        receipt = SimpleNamespace(run_id=history.AUTHORITY['run'], digest='a' * 64,
            images={'sources/production/BOR_OrderAllocationHistory': {'count': 8}})
        before = deepcopy(receipt.images)
        published = history.published_images(receipt)
        self.assertEqual(receipt.images, before)
        self.assertEqual(published[next(iter(published))]['completion'],
                         {'run': receipt.run_id, 'digest': receipt.digest})

    def test_private_tables_do_not_change_accepted_phase_registry(self):
        from mta.runtime.phase_state import REGISTRY
        self.assertTrue(set(history.REGISTRY).isdisjoint(REGISTRY))


class BprHistoryDjangoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'local-unit-check-only')
        import django
        django.setup()

    def test_required_completion_cannot_fall_back_to_terminal_append(self):
        run = SimpleNamespace(pk=history.AUTHORITY['run'])
        with patch.object(history, 'verified', side_effect=ValueError('completion missing')):
            with self.assertRaisesRegex(ValueError, 'completion missing'):
                history.terminal_completion(run)

    def test_reader_uses_private_registry_and_denies_rebound_metadata(self):
        from mta.presentation import daily_sources
        path = 'sources/production/BOR_OrderAllocationHistory'
        item = {'table': history.TABLES[history.NAMES[0]], 'image': path, 'count': 8}
        receipt = SimpleNamespace(run_id=history.AUTHORITY['run'], digest='a' * 64, images={path: item})
        published = history.published_images(receipt)[path]
        run = SimpleNamespace(pk=receipt.run_id)
        with patch.object(daily_sources, 'image_metadata', return_value=published), \
                patch.object(history, 'verified', return_value=receipt), \
                patch.object(history.typed, 'load_image', return_value=[{'example': None}]) as load:
            self.assertEqual(daily_sources.image_rows(run, path), [{'example': None}])
            load.assert_called_once_with(run, published, table_registry=history.REGISTRY)
            with self.assertRaisesRegex(ValueError, 'differs from its completion'):
                history.read_published(run, path, dict(published, count=9))

    def test_retained_v5_is_exact_and_new_recipe_is_distinct(self):
        from mta.presentation.daily_sources import RETAINED_V5_RECIPE, recipe_digest
        self.assertEqual(RETAINED_V5_RECIPE, '4e110600f15a7dcf36beb191261961cbdef641c0514b5a1d89ecc4164ec71cab')
        self.assertNotEqual(recipe_digest(), RETAINED_V5_RECIPE)

    def test_terminal_writer_reuses_history_without_running_append_again(self):
        from mta.serialization import digest
        from mta.presentation.production_reports import recipe_digest
        report_recipe = recipe_digest()
        names = ('BORWithOrderAllocation', 'RRR_OrderAllocation', 'AllocatedOrders', 'BOROARequirement')
        values = {name: [{'kept': index}] for index, name in enumerate(names)}
        manifest = {'images': {name: dict(count=len(rows), digest=digest(rows)) for name, rows in values.items()},
                    'consumers': {'production_reports': {name: {'image': name} for name in names}}}
        run = SimpleNamespace(pk=history.AUTHORITY['run'], input_digest=history.AUTHORITY['input_digest'],
            business_date=__import__('datetime').date(2026, 10, 24),
            predecessor_id=history.AUTHORITY['predecessor'],
            predecessor=SimpleNamespace(output_digest=history.AUTHORITY['predecessor_digest']))
        receipt = SimpleNamespace(pk=run.pk, run_id=run.pk, digest='a'*64,
            images={history.reports.PATHS[name]: dict(history.AUTHORITY['expected'][name]) for name in history.NAMES},
            phase=SimpleNamespace(snapshot=SimpleNamespace(manifest=manifest)))
        opening = dict(production_report_policy=history.AUTHORITY['policy'], production_report_opening=None,
                       production_report_schema='fresh-production-source-inputs-v1', supplier={})
        with patch('mta.runtime.scoped_final.require_pending_final'), \
                patch.object(history, 'verified', return_value=receipt), \
                patch.object(history, 'project', side_effect=AssertionError('history replay')), \
                patch('mta.presentation.production_reports.recipe_digest', return_value=report_recipe), \
                patch('mta.presentation.production_reports._write_sources', side_effect=AssertionError('ordinary writer')), \
                patch.object(history.reports, 'save', side_effect=lambda *a, **kw: {}) as save:
            result = history.publish(run, values, opening, receipt)
            self.assertEqual(save.call_count, 4)
            self.assertEqual([call.args[1] for call in save.call_args_list], list(names))
            for path, item in history.published_images(receipt).items():
                self.assertEqual(result[path], item)
            with self.assertRaisesRegex(ValueError, 'differ from accepted BPR'):
                history.publish(run, dict(values, BORWithOrderAllocation=[]), opening, receipt)
