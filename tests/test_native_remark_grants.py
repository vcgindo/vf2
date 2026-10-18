"""Native remark write coverage and exact least-privilege catalogue admission.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'source-only-remark-grants-test')
import django
with patch('django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection',
           side_effect=AssertionError('Database forbidden')):
    django.setup()
from mta.mdm import owned_namespace as owned
from mta.runtime import test_application_capability as fixtures
from mta.runtime.daily_input_schema import LIVE


class NativeRemarkGrantTests(unittest.TestCase):
    def setUp(self):
        blocker = patch('django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection',
                        side_effect=AssertionError('Database forbidden'))
        blocker.start()
        self.addCleanup(blocker.stop)
        fixture = fixtures.ApplicationCapabilityTests(methodName='runTest')
        fixture.setUp()
        self.catalogue, self.registration = fixture.catalogue, fixture.reg
        self.tables = ['mta.' + table for table, _ in LIVE]

    def test_every_native_live_remark_writer_has_append_only_access(self):
        self.assertEqual(len(self.tables), 3)
        for name in self.tables:
            self.assertEqual(owned.APPLICATION_GRANTS[name],
                             {'columns': [], 'table': ['INSERT']})
        owned._check_application_grants(self.catalogue, self.registration)

    def test_missing_remark_insert_or_sequence_usage_is_rejected(self):
        for table in self.tables:
            for name, privilege in ((table, 'INSERT'), (table + '_id_seq', 'USAGE')):
                catalogue = deepcopy(self.catalogue)
                catalogue['grants'] = [g for g in catalogue['grants']
                    if not (g['name'] == name and g['privilege'] == privilege)]
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'incomplete'):
                    owned._check_application_grants(catalogue, self.registration)

    def test_mutation_delegation_and_public_access_remain_denied(self):
        for table in self.tables:
            original = next(g for g in self.catalogue['grants']
                            if g['name'] == table and g['privilege'] == 'INSERT')
            changes = [{'privilege': p} for p in ('UPDATE', 'DELETE', 'TRUNCATE')]
            changes += [{'grantable': True}, {'grantee': 0}, {'grantee': 99}]
            for change in changes:
                catalogue = deepcopy(self.catalogue)
                catalogue['grants'].append(dict(original, **change))
                with self.subTest(table=table, change=change), self.assertRaises(ValueError):
                    owned._check_application_grants(catalogue, self.registration)

    def test_captured_remark_rows_do_not_gain_write_access(self):
        for family in ('bpr', 'bor', 'boroa'):
            self.assertNotIn('mta.fresh_mta_' + family + 'capturedremark',
                             owned.APPLICATION_GRANTS)
