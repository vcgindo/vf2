"""Named-image boundary, own action lineage and permission ownership."""
import os
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.presentation.dbm_read import dbm_context, GRID_TABLES, HISTORY_TABLES, SCOPE_TABLES
from mta.serialization import digest


class DBMReadTest(unittest.TestCase):
    def run_value(self, commands=()):
        run = SimpleNamespace(business_date=date(2026, 6, 17), commands=Mock())
        run.commands.exists.return_value = bool(commands)
        run.commands.order_by.return_value = commands
        return run

    def test_grid_reads_only_nine_native_images(self):
        run = self.run_value()
        with patch('mta.presentation.dbm_read.selected_run', return_value=run), \
             patch('mta.presentation.dbm_read.image_rows', side_effect=lambda r, p: [p]) as read, \
             patch('mta.presentation.dbm_read.hierarchy.selected_manifest', return_value=None), \
             patch('mta.presentation.context.read_outputs', side_effect=AssertionError('whole run')):
            context = dbm_context()
        self.assertEqual(set(context.dbm), set(GRID_TABLES))
        self.assertEqual([c.args[1] for c in read.call_args_list], ['closing/dbm/' + n for n in GRID_TABLES])
        self.assertEqual(context.output, {})

    def test_history_uses_importer_scope_and_exact_projection_dependencies(self):
        run = self.run_value()
        with patch('mta.presentation.dbm_read.selected_run', return_value=run), \
             patch('mta.presentation.dbm_read.image_rows', side_effect=lambda r, p: [p]) as read, \
             patch('mta.presentation.dbm_read.hierarchy.selected_manifest', return_value={'approved': True}), \
             patch('mta.presentation.dbm_read.permission_catalogue', return_value={}), \
             patch('mta.presentation.dbm_read.hierarchy.project_attributes', side_effect=lambda s, c, m: s) as project:
            context = dbm_context(history=True)
        self.assertEqual(set(context.dbm), set(HISTORY_TABLES))
        self.assertEqual(set(c.args[1] for c in read.call_args_list),
                         {'closing/dbm/' + n for n in HISTORY_TABLES} |
                         {'closing/importer/' + n for n in SCOPE_TABLES})
        self.assertEqual(project.call_args.args[0], context.output['ClosingState'][0]['importer'])
        self.assertEqual(context.output['ClosingState'][0]['importer']['SkuAttributeData'],
                         ['closing/importer/SkuAttributeData'])

    def test_committed_actions_keep_full_dbm_digest_validation(self):
        opening = {n: [] for n in GRID_TABLES}
        opening['UnrelatedState'] = [{'value': 'must participate in action digest'}]
        opening['IntermediateTables'] = {'Scratch': [{'kept': 1}]}
        opening['Suggestions'] = [{'SKUCode': '337', 'WhCode': 'AG515802'}]
        closing = {**opening, 'Suggestions': []}
        payload = {'timestamp': '2026-06-17T00:00:00'}
        event = SimpleNamespace(pk=1, payload=payload, digest=digest(payload),
                                before_digest=digest(opening), after_digest=digest(closing),
                                state_manifest={'Suggestions': {'image': 'action/1/Suggestions'}})
        run = self.run_value([event])
        tables = {n: {'image': 'closing/dbm/' + n} for n in opening if n != 'IntermediateTables'}
        tables['IntermediateTables'] = {'scratch_kind': 'dict', 'items': [
            ['Scratch', {'image': 'closing/dbm/IntermediateTables/Scratch'}]]}
        run.production_manifest = {'closing': {'dbm': {'tables': tables}}}

        def read(r, path):
            return opening['IntermediateTables']['Scratch'] if path.endswith('/Scratch') else opening[path.rsplit('/', 1)[1]]

        with patch('mta.presentation.dbm_read.selected_run', return_value=run), \
             patch('mta.presentation.dbm_read.image_rows', side_effect=read), \
             patch('mta.presentation.dbm_read.hierarchy.selected_manifest', return_value=None), \
             patch('mta.runtime.relational_state.load_image', return_value=[]), \
             patch('mta.presentation.context.read_outputs', side_effect=AssertionError('whole run')):
            self.assertEqual(dbm_context().dbm, closing)
            event.before_digest = 'tampered'
            with self.assertRaisesRegex(ValueError, 'Command input/ordering drift'):
                dbm_context()
        self.assertEqual(len(opening['Suggestions']), 1)


if __name__ == '__main__':
    unittest.main()
