"""Draft migration -> actual admission consumer checks, not PostgreSQL proof."""
from importlib import import_module
import re
import unittest
from unittest.mock import Mock, patch

from mta.runtime import ingestion_ownership as ownership


guards = import_module('mta.runtime.migrations.0234_report_definition_guards')


def watch_catalogue():
    rows = []
    for name, operation, table, transitions, domain in re.findall(
            r"CREATE TRIGGER (ingestion_watch_\w+) AFTER (\w+) ON mta\.(\w+)(.*?)"
            r"FOR EACH STATEMENT EXECUTE FUNCTION mta\.ingestion_watch\('(\w+)'\);", guards.SQL, re.S):
        old = 'old_rows' if 'OLD TABLE AS old_rows' in transitions else None
        new = 'new_rows' if 'NEW TABLE AS new_rows' in transitions else None
        kind = {'INSERT': 4, 'DELETE': 8, 'UPDATE': 16, 'TRUNCATE': 32}[operation]
        rows.append(('mta', table, name, 'O', 'mta', 'ingestion_watch', domain + '\\000',
                     kind, 1, None, '', old, new))
    return rows


def validate_catalogue(rows):
    cursor = Mock(); cursor.fetchall.return_value = rows
    with patch('mta.runtime.accepted_state_ownership.verify_guards'), \
            patch('mta.runtime.scoped_action_ownership.available'), \
            patch.object(ownership, 'migration_history_guard', return_value=False), \
            patch.object(ownership, 'tables', return_value=[
                ('mta', table, ownership.domain('mta', table)) for table in guards.TABLES]):
        ownership._verify_guard_coverage(cursor)


class RegistrationGuardConsumerTests(unittest.TestCase):
    def test_declared_watch_catalogue_meets_real_admission_roster(self):
        validate_catalogue(watch_catalogue())

    def test_missing_truncate_and_wrong_domain_are_rejected_by_actual_consumer(self):
        rows = watch_catalogue()
        without_truncate = [r for r in rows if not (r[1] == guards.TABLES[0] and r[2].endswith('truncate'))]
        with self.assertRaisesRegex(ValueError, 'Missing or incorrectly classified'):
            validate_catalogue(without_truncate)
        changed = list(rows); wrong = list(changed[-1]); wrong[6] = 'action\\000'; changed[-1] = tuple(wrong)
        with self.assertRaisesRegex(ValueError, 'Missing or incorrectly classified'):
            validate_catalogue(changed)

    def test_scoped_readers_select_installed_body_without_waiving_minimum(self):
        cursor = Mock()
        minimum = '0218_scope_read_reference_guards'
        cursor.fetchall.return_value = [(minimum,), ('0231_runtime_report_placement_guards',)]
        self.assertEqual(ownership.scoped_derived_body(cursor, minimum=minimum), guards.OLD)
        cursor.fetchall.return_value.append(('0234_report_definition_guards',))
        self.assertEqual(ownership.scoped_derived_body(cursor, minimum=minimum), guards.NEW)
        cursor.fetchall.return_value = [('0234_report_definition_guards',)]
        with self.assertRaisesRegex(ValueError, 'Required scoped derived'):
            ownership.scoped_derived_body(cursor, minimum=minimum)


if __name__ == '__main__':
    unittest.main()
