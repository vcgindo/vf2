import os
from pathlib import Path
import unittest
from unittest.mock import patch

from release.provision import identifier, plan
from release.register_mta import render_sql
from release.configuration import database_options


class ProvisionConfigurationTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {}, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def test_default_two_databases_and_per_service_roles_have_no_development_names(self):
        value = plan()
        self.assertEqual(value['databases'], {'MTA': 'vectorflow_mta', 'MTO': 'vectorflow_mto'})
        names = [name for roles in value['roles'].values() for name in roles.values()]
        self.assertEqual(len(set(names)), 9)
        self.assertFalse(any('handoff' in n or 'test' in n for n in names))

    def test_database_aliases_and_owner_role_collisions_fail_before_connecting(self):
        os.environ['MTO_DB_NAME'] = 'vectorflow_mta'
        with self.assertRaises(ValueError):
            plan()
        os.environ.pop('MTO_DB_NAME')
        os.environ['AUTH_OWNER_ROLE'] = 'vectorflow_mta_owner'
        with self.assertRaises(ValueError):
            plan()
        os.environ['AUTH_OWNER_ROLE'] = 'fresh_namespace_registrar'
        with self.assertRaises(ValueError):
            plan()

    def test_identifiers_and_migration_role_options_cannot_contain_sql_or_new_settings(self):
        for name in ['x;DROP DATABASE x', 'role name', 'a' * 64, 'owner -c superuser=on']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                identifier(name)
        os.environ['DB_SESSION_ROLE'] = 'vectorflow_mta_owner'
        self.assertEqual(database_options({'options': '-c search_path=mta,public'})['options'],
            '-c search_path=mta,public -c role=vectorflow_mta_owner')
        os.environ['DB_SESSION_ROLE'] = 'owner -c superuser=on'
        with self.assertRaises(ValueError):
            database_options()

    def test_namespace_template_uses_quoted_identifiers_and_literals_not_raw_operator_sql(self):
        rendered = render_sql('''\\set ON_ERROR_STOP on
SELECT :"owner_role", :'registration_id';''',
            {'owner_role': 'owner"quoted', 'registration_id': "value'; DROP TABLE anything; --"})
        self.assertNotIn('\\set', rendered)
        self.assertIn('"owner""quoted"', rendered)
        self.assertIn("'value''; DROP TABLE anything; --'", rendered)
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            render_sql('SELECT :"unknown";', {})
