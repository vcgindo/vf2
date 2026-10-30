"""Canonical role metadata and safe blank/install repair contracts.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from release import install_identity as installer

ROOT = Path(__file__).resolve().parents[1]


class CatalogueTests(unittest.TestCase):
    def test_effective_roles_and_links_match_retained_source_not_new_policy(self):
        value = installer.catalogue()
        source = ROOT / value['source']['path']
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), value['source']['sha256'])
        tree = ast.parse(source.read_text(encoding='utf-8'))

        class Expand(ast.NodeTransformer):
            def visit_Attribute(self, node):
                if isinstance(node.value, ast.Name) and node.value.id == 'self':
                    values = {'all_permission_urls': [r['url'] for r in value['permissions']],
                              'all_feature_name': [r['feature'] for r in value['features']]}
                    if node.attr in values:
                        return ast.parse(repr(values[node.attr]), mode='eval').body
                return self.generic_visit(node)

        def literal(method, name):
            function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == method)
            assignment = next(n for n in ast.walk(function) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
            return ast.literal_eval(Expand().visit(copy.deepcopy(assignment.value)))

        self.assertEqual(value['roles'], literal('seed_roles', 'roles'))
        for key, method, variable, valid in (
            ('role_permissions', 'seed_role_permissions', 'role_permission_map', {r['url'] for r in value['permissions']}),
            ('role_features', 'seed_role_features', 'role_feature_map', {r['feature'] for r in value['features']})):
            original = literal(method, variable)
            self.assertEqual(value[key], {role: [x for x in links if x in valid] for role, links in original.items()})
            self.assertEqual(value['unresolved_source_links'][key],
                {role: sorted(set(links) - valid) for role, links in original.items() if set(links) - valid})


@unittest.skipUnless(os.environ.get('VF_IDENTITY_INSTALL_TEST') == '1',
                     'Run database contracts inside the auth image with VF_IDENTITY_INSTALL_TEST=1')
class DatabaseTests(unittest.TestCase):
    def setUp(self):
        installer._setup()
        from django.db import connections
        from django.db.backends.sqlite3.base import DatabaseWrapper
        from api.models import User, Roles, Permission, FeatureMaster, ApplicationMaster, UserserviceConfig
        self.directory = tempfile.TemporaryDirectory()
        self.original = connections['default']
        settings = dict(self.original.settings_dict, ENGINE='django.db.backends.sqlite3',
                        NAME=str(Path(self.directory.name) / 'contract.sqlite3'), OPTIONS={})
        self.database = DatabaseWrapper(settings, alias='default')
        connections['default'] = self.database
        with self.database.schema_editor() as editor:
            for model in (User, Roles, Permission, FeatureMaster, ApplicationMaster, UserserviceConfig):
                editor.create_model(model)

    def tearDown(self):
        from django.db import connections
        self.database.close()
        connections['default'] = self.original
        self.directory.cleanup()

    def base(self):
        from api.models import ApplicationMaster, Permission, FeatureMaster, UserserviceConfig
        value = installer.catalogue()
        for model, key in ((ApplicationMaster, 'applications'), (Permission, 'permissions'),
                           (FeatureMaster, 'features'), (UserserviceConfig, 'configuration')):
            model.objects.bulk_create([model(**row) for row in value[key]])

    def test_fresh_install_has_complete_roles_but_no_user_or_grants(self):
        from api.models import User, Roles, Permission, FeatureMaster
        result = installer.install()
        self.assertEqual(result['roles_created'], 29)
        self.assertEqual(result['permission_links_created'], 333)
        self.assertEqual(result['feature_links_created'], 43)
        self.assertEqual(User.all_objects.count(), 0)
        self.assertEqual(Roles.user_id.through.objects.count(), 0)
        self.assertEqual(Permission.role_id.through.objects.count(), 333)
        self.assertEqual(FeatureMaster.role_id.through.objects.count(), 43)
        with self.assertRaisesRegex(ValueError, 'empty metadata'):
            installer.install()

    def test_repair_preserves_admin_credentials_and_assigns_no_roles(self):
        from api.models import User, Roles
        self.base()
        admin = User.all_objects.create_superuser(email='contract@example.invalid', name='contract', tc=True, password='Contract!952')
        before = list(User.all_objects.values())
        first = installer.repair_missing_roles()
        second = installer.repair_missing_roles()
        self.assertEqual(first['roles_created'], 29)
        self.assertEqual(second['roles_created'], 0)
        self.assertEqual(second['permission_links_created'], 0)
        self.assertEqual(second['feature_links_created'], 0)
        self.assertEqual(list(User.all_objects.values()), before)
        self.assertEqual(admin.role_id.count(), 0)
        self.assertEqual(Roles.user_id.through.objects.count(), 0)

    def test_fresh_installer_admin_has_full_dynamic_access_without_business_grant_seeding(self):
        from api.models import User
        from common.data_scopes import effective_data_scopes
        from unittest.mock import patch
        installer.install()
        # Same account factory used by compose_install, with no role/scope seed.
        admin = User.all_objects.create_superuser(email='admin@fixture.invalid', name='Admin',
                                                 tc=True, password='Contract!952')
        self.assertTrue(admin.is_admin)
        self.assertEqual(admin.role_id.count(), 0)
        with patch('common.data_scopes._administrator_scopes', return_value=([1, 2], [3])) as catalogue:
            self.assertEqual(effective_data_scopes(admin.id, 2, administrator=admin.is_admin), ([1, 2], [3]))
        catalogue.assert_called_once()

    def test_conflicting_existing_role_rolls_back_all_new_metadata(self):
        from api.models import Roles
        self.base()
        Roles.objects.create(name='Admin', code='CUSTOM', description='preserve', application_id=2)
        before = list(Roles.objects.values())
        with self.assertRaisesRegex(ValueError, 'no overwrite'):
            installer.repair_missing_roles()
        self.assertEqual(list(Roles.objects.values()), before)

    def test_unexpected_existing_grant_is_not_removed_or_extended(self):
        from api.models import Roles, Permission
        self.base()
        definition = next(row for row in installer.catalogue()['roles'] if row['name'] == 'Admin')
        role = Roles.objects.create(**definition)
        permission = Permission.objects.filter(url__startswith='/mto/').first()
        role.permission_id.add(permission)
        with self.assertRaisesRegex(ValueError, 'links differ'):
            installer.repair_missing_roles()
        self.assertEqual(Roles.objects.count(), 1)
        self.assertEqual(list(role.permission_id.all()), [permission])

    def test_order_report_navigation_adds_metadata_without_assigning_grants(self):
        from api.models import User, Roles, Permission, FeatureMaster
        self.base()
        before = dict(users=list(User.all_objects.values()), roles=list(Roles.objects.values()),
            user_roles=list(Roles.user_id.through.objects.values()),
            role_urls=list(Permission.role_id.through.objects.values()),
            role_features=list(FeatureMaster.role_id.through.objects.values()))
        first = installer.repair_order_report_navigation()
        self.assertTrue(first['permission_created'])
        self.assertFalse(installer.repair_order_report_navigation()['permission_created'])
        self.assertEqual(Permission.objects.filter(**installer.ORDER_REPORT_NAVIGATION).count(), 1)
        self.assertEqual(before, dict(users=list(User.all_objects.values()), roles=list(Roles.objects.values()),
            user_roles=list(Roles.user_id.through.objects.values()),
            role_urls=list(Permission.role_id.through.objects.values()),
            role_features=list(FeatureMaster.role_id.through.objects.values())))

    def test_order_report_navigation_conflicts_are_not_overwritten(self):
        from api.models import Permission
        self.base()
        definition = dict(installer.ORDER_REPORT_NAVIGATION, code='CUSTOM')
        Permission.objects.create(**definition)
        before = list(Permission.objects.values())
        with self.assertRaisesRegex(ValueError, 'no overwrite'):
            installer.repair_order_report_navigation()
        self.assertEqual(list(Permission.objects.values()), before)


if __name__ == '__main__':
    unittest.main()
