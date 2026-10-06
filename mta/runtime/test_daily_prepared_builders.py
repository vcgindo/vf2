"""PostgreSQL wiring proof for explicit daily prepared builders.

The tiny rows exercise real typed-image SQL, installed production guards and
immutable receipts.  They are deliberately not a legacy/modern parity fixture.
"""
import io
from datetime import date

from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from unittest.mock import patch

from mta.presentation.daily_preparation import source_digest
from mta.runtime.models import (
    BprPreparedProjection, CalculationRun, DailySourceReceipt,
    DailyUiPublication, HistoryPreparedProjection, PlanningGridProjection,
    PlanningSourceProjection,
)
from mta.runtime.relational_state import CATALOG, save_image
from mta.serialization import digest


PATHS = (
    'reports/bpr/BPR_Table', 'reports/bpr/vf_RationedReqReport',
    'closing/dbm/SKULocStandardAttributes', 'closing/importer/MasterData',
    'closing/importer/SKUDescriptionTbl', 'closing/importer/SiteDescriptionTbl',
    'closing/importer/SkuAttributeData', 'closing/importer/LocationAttributeData',
    'closing/importer/SkuLocAttributeData', 'closing/btr/BufferTrendPhysicalInv',
    'closing/btr/BufferTrendDispatch', 'closing/btr/BufferTrendDates',
    'closing/btr/SkuAttributeData', 'closing/btr/LocationAttributeData',
    'closing/btr/SkuLocAttributeData',
)


def value(name, kind):
    lower = name.casefold()
    if lower == 'skucode': return 'SKU-1'
    if lower in ('whcode', 'loccode'): return 'WH-1'
    if lower == 'parentwhcode': return 'PARENT-1'
    if lower == 'skudescription': return 'SKU one'
    if lower == 'whdescription': return 'Warehouse one'
    if lower == 'reportdate': return '2026-01-02'
    if lower.endswith('color'): return 'Black'
    if kind in ('int', 'bigint'): return 1
    if kind == 'bit': return True
    if kind == 'date': return '2026-01-02'
    if kind == 'datetime': return '2026-01-02T03:04:05'
    if kind in ('decimal', 'numeric'): return '1.00'
    if kind in ('float', 'real'): return 1.0
    return name[:40] or 'x'


def complete_row(binding, *, nullable_probe=False):
    table = '/'.join(CATALOG['bindings'][binding])
    row = {name: value(name, kind) for name, kind in CATALOG['tables'][table]}
    if nullable_probe:
        probe = next((name for name, _ in CATALOG['tables'][table]
                      if name.casefold() in ('c5', 'sl5', 'll5')), None)
        if probe: row[probe] = None
    return row


def _mutated_recipe_query(*_args, **_kwargs):
    return 'SELECT 0', []


class DailyServingOptInTests(SimpleTestCase):
    def test_fixture_recipe_hashes_remain_dynamic_and_match_accepted_head(self):
        import importlib
        expected = {
            'planning_chart_preparation': ('chart_ingredients', '1c908b7f9ea848979e309dd5f15b2085b9cb18039bedc1e5fe155fb2bef7a2e2'),
            'planning_custom_preparation': ('custom_occurrences', '8ac8accc948cdd56ea6bb8c381a1fc02f3a0d0c038ca318546e9b76c17e228c2'),
            'planning_expedite_chart_preparation': ('prepost_members', '11ba61b1b3a8cc14688f066af8fe37c6b12b8f4b53f4b0377ebf73f668939792'),
            'planning_expedite_custom_preparation': ('custom_occurrences', 'bd82329f80c93aaf869268187eb3f389ab07aaf207767e30d12025b2beef41ad'),
            'planning_git_preparation': ('git_occurrences', '08b746bebb9a3bf8c30903fb39d9c5f5f020744719114d45bd8fef47a71877e7'),
            'planning_grid_preparation': ('grid_occurrences', 'a204854b32f7be52b3aac91bee31cbd099300f0e623f98fa65dee5b8a99c8d3a'),
        }
        for name, (function, accepted) in expected.items():
            module = importlib.import_module('mta.presentation.' + name)
            current = module.recipe_digest()
            self.assertEqual(current, accepted, name)
            with patch.object(module, function, _mutated_recipe_query):
                self.assertNotEqual(module.recipe_digest(), current, name)
    @override_settings(VF_MTA_DAILY_PUBLICATION=False)
    def test_explicit_build_owner_enables_only_its_daily_run(self):
        from types import SimpleNamespace
        from mta.presentation.daily_preparation import production_branch
        run = SimpleNamespace(kind='DAILY_CHAIN', pk='run-1')
        cursor = __import__('unittest.mock', fromlist=['MagicMock']).MagicMock()
        cursor.__enter__.return_value.fetchone.return_value = ('run-1',)
        db = __import__('unittest.mock', fromlist=['MagicMock']).MagicMock(
            vendor='postgresql', in_atomic_block=True)
        db.cursor.return_value = cursor
        with patch('mta.presentation.daily_preparation.connection', db):
            self.assertTrue(production_branch(run))
            run.pk = 'run-2'
            self.assertFalse(production_branch(run))

    @override_settings(VF_MTA_DAILY_PUBLICATION=False)
    @patch('mta.presentation.bpr_read.image_rows', return_value=[])
    @patch('mta.presentation.bpr_read.terminal_ancillary')
    @patch('mta.presentation.bpr_read.selected_run')
    def test_daily_run_keeps_terminal_ancillary_when_opt_in_is_off(
            self, selected, terminal, _rows):
        from types import SimpleNamespace
        from mta.presentation.bpr_read import bpr_context
        run = SimpleNamespace(kind='DAILY_CHAIN')
        selected.return_value = run
        ancillary = {'InTransitData': [], 'BPRReport_RemarkDetails': []}
        terminal.return_value = ancillary
        with patch('mta.presentation.daily_preparation.ancillary_rows') as daily, \
                patch('mta.presentation.bpr_read.hierarchy.selected_manifest', return_value=None):
            self.assertIs(bpr_context().ancillary, ancillary)
        terminal.assert_called_once_with(run)
        daily.assert_not_called()

    @override_settings(VF_MTA_DAILY_PUBLICATION=True)
    @patch('mta.presentation.bpr_read.image_rows', return_value=[])
    @patch('mta.presentation.bpr_read.terminal_ancillary')
    @patch('mta.presentation.bpr_read.selected_run')
    def test_daily_run_uses_daily_ancillary_when_opted_in(
            self, selected, terminal, _rows):
        from types import SimpleNamespace
        from mta.presentation.bpr_read import bpr_context
        run = SimpleNamespace(kind='DAILY_CHAIN')
        selected.return_value = run
        ancillary = {'InTransitData': [], 'BPRReport_RemarkDetails': []}
        with patch('mta.presentation.daily_preparation.ancillary_rows', return_value=ancillary) as daily, \
                patch('mta.presentation.bpr_read.hierarchy.selected_manifest', return_value=None):
            self.assertIs(bpr_context().ancillary, ancillary)
        daily.assert_called_once_with(run)
        terminal.assert_not_called()


class DailyPreparedBuilderPostgresTests(TestCase):
    databases = {'default'}

    def setUp(self):
        if connection.vendor != 'postgresql':
            self.skipTest('daily prepared builders require PostgreSQL')
        self.run = CalculationRun.objects.create(
            input_digest='1' * 64, execution_revision='daily-builder-postgres-001',
            kind='DAILY_CHAIN', business_date=date(2026, 1, 2), input_payload={},
            status='RUNNING', output_digest='2' * 64, production_digest='3' * 64)
        images = {}
        for path in PATHS:
            row = complete_row(path, nullable_probe=path.endswith('SkuAttributeData'))
            # BPR's driving bag deliberately retains a duplicate occurrence.
            rows = [row, dict(row)] if path == 'reports/bpr/BPR_Table' else [row]
            images[path] = save_image(self.run, path, path, rows)
        self.run.production_manifest = {'version': 1, 'images': images}
        self.run.save(update_fields=['production_manifest'])
        DailySourceReceipt.objects.create(
            run=self.run, input_digest=self.run.input_digest,
            recipe_digest='4' * 64, images={}, images_digest=digest({}))
        DailyUiPublication.objects.create(
            run=self.run, output_digest=self.run.output_digest,
            source_digest='5' * 64, configuration_digest='6' * 64,
            recipe_digest='7' * 64, status='INCOMPLETE')
        self.run.status = 'SUCCEEDED'
        self.run.save(update_fields=['status'])
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.daily_publication_build',%s,true)",
                           [str(self.run.pk)])

    def command(self, name):
        output = io.StringIO()
        call_command(name, run_id=str(self.run.pk), stdout=output, verbosity=0)
        self.assertIn('"status": "PASS"', output.getvalue())

    def test_real_daily_guards_and_representative_builder_sql(self):
        """Nonempty BPR/history plus empty fact-grid prove wiring, not parity."""
        from mta.runtime.management.commands.prepare_bpr_fixture import prepare
        bpr = prepare(run=self.run)
        self.assertGreater(bpr['row_count'], 0)
        self.assertEqual(BprPreparedProjection.objects.get(run=self.run).source_digest,
                         source_digest(self.run))

        self.command('prepare_planning_sources')
        sources = PlanningSourceProjection.objects.get(run=self.run)
        self.assertGreater(sources.bpr_count, 0)
        self.assertGreater(sources.git_count, 0)

        # No synthetic Excess/Fulfillment facts are invented. The command still
        # compiles and executes both real occurrence queries and seals zero rows.
        self.command('prepare_planning_grids')
        grids = PlanningGridProjection.objects.get(run=self.run)
        self.assertEqual((grids.excess_count, grids.fulfillment_count), (0, 0))

        self.command('prepare_history_reports')
        history = HistoryPreparedProjection.objects.get(run=self.run)
        self.assertGreater(history.research_master_count, 0)
        self.assertGreater(history.research_history_count, 0)
        self.assertGreater(history.availability_count, 0)
        self.assertGreater(history.graph_count, 0)
