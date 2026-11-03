"""Read-only upgrade qualification on the retained completed IR3 installation."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID


@unittest.skipUnless(os.environ.get('VF_IR3_UPGRADE_OWNER_PG') == '1', 'retained PostgreSQL proof')
class ScopedUpgradeOwnerTests(unittest.TestCase):
    def test_selected_owner_binding_and_complete_metadata_boundary(self):
        from django.db import connection, transaction
        from mta.runtime.models import ProductionInitialization
        from release import upgrade_database as upgrade
        from mta.runtime.input_reader import read_input
        self.assertEqual(connection.settings_dict['NAME'], 'vftest_fresh_ir3_category_20261103')
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            owner = ProductionInitialization.objects.select_related('source').get(
                pk='9ca65d4c-1f8a-4227-9d04-7aa8a59b58fa')
            upgrade.require_finished_work(cursor, owner)
            selected = upgrade.selected(owner)
            self.assertEqual(selected['run_id'], '098967f3-c17e-404c-8a34-e8cda63554b9')
            snapshot = upgrade.snapshot(owner)
            self.assertIn(selected['run_id'], [v['id'] for v in snapshot['mta.fresh_mta_calculationrun']])
            self.assertEqual(len(snapshot['mta.fresh_mta_calculationrun']), 8)
            self.assertTrue(snapshot['mta.fresh_mta_runscopeattempt'])
            self.assertTrue(snapshot['mta.fresh_mta_runphaseacceptance'])
            self.assertEqual(len(snapshot['mta.fresh_mta_dailyuipublication']), 8)
            foreign = SimpleNamespace(pk=UUID(int=1), source_id=owner.source_id, source=owner.source)
            with self.assertRaisesRegex(ValueError, 'initialization binding differs'):
                upgrade.selected(foreign)
            foreign.source_id = -1
            with self.assertRaisesRegex(ValueError, 'accepted installation'):
                upgrade.selected(foreign)
            def corrupt_binding(*args, **kwargs):
                value = read_input(*args, **kwargs)
                value['initialization_binding']['source_digest'] = '0' * 64
                return value
            with patch('mta.runtime.input_reader.read_input', side_effect=corrupt_binding):
                with self.assertRaisesRegex(ValueError, 'initialization binding differs'):
                    upgrade.selected(owner)
            self.assertEqual(upgrade.snapshot(owner), snapshot)
