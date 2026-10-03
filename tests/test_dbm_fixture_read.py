"""Fixture reduction preserves the native DBM pair relation and normal reader."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from mta.presentation import dbm_fixture_read as reader
from mta.presentation.dbm_read import dbm_context
from mta.presentation.context import PermissionCodes


class DbmFixtureReadTest(unittest.TestCase):
    def test_exact_pair_membership_is_parameterized_and_null_safe(self):
        sql, values = reader.pair_condition({('a ', 'X'), ('A', 'x'), (None, 'x'), ('a', None), (None, None)}, 'WhCode')
        self.assertNotIn('lower', sql)
        self.assertNotIn('rtrim', sql)
        self.assertIn('IN (VALUES', sql)
        self.assertIn('"SKUCode" IS NULL', sql)
        self.assertIn('"WhCode" IS NULL', sql)
        self.assertCountEqual(values, ['a ', 'X', 'A', 'x', 'x', 'a'])
        self.assertEqual(reader.pair_condition(set(), 'WhCode'), ('FALSE', []))

    def test_prunes_before_transfer_preserving_source_order_and_wire_values(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(2, 'a', 'x', 7), (8, 'a', 'x', None)]
        state = {'Suggestions': [{'SKUCode':'a','WhCode':'x'}, {'SKUCode':'b','WhCode':'y'}]}
        metadata = dict(table='DBM/DBMMaster', count=10,
                        fields=[('SKUCode','SKUCode','str'),('WhCode','WhCode','str'),('Norm','Norm','str')])
        with patch.object(reader.fixture, 'binding') as binding, \
             patch.object(reader, 'image_rows', side_effect=lambda r,p:state.get(p.split('/')[-1], [])), \
             patch.object(reader, 'scope', return_value=(PermissionCodes({'a':2}),PermissionCodes({'x':1}))), \
             patch.object(reader.fixture, 'image_metadata', return_value=metadata), \
             patch.object(reader.connection, 'cursor') as factory:
            factory.return_value.__enter__.return_value = cursor
            result = reader.grid_state(SimpleNamespace(pk='owned'), {})
        binding.assert_called_once()
        self.assertEqual(result['Suggestions'], state['Suggestions'][:1])
        self.assertEqual([r['Norm'] for r in result['DBMMaster']], ['7',None])
        for call in cursor.execute.call_args_list:
            self.assertIn('ORDER BY vf_ordinal', call.args[0])
            self.assertEqual(call.args[1][-2:], ['a','x'])

    def test_fixture_dispatch_does_not_change_normal_or_command_readers(self):
        run = SimpleNamespace(kind='LEGACY_UI_FIXTURE',business_date='fixed',commands=MagicMock())
        run.commands.exists.return_value=False
        with patch('mta.presentation.dbm_read.selected_run',return_value=run), \
             patch('mta.presentation.dbm_read.hierarchy.selected_manifest',return_value=None), \
             patch.object(reader,'grid_state',return_value={'fixed':[]}) as read:
            self.assertEqual(dbm_context(payload={'scope':'kept'}).dbm, {'fixed':[]})
            read.assert_called_once_with(run, {'scope':'kept'})
