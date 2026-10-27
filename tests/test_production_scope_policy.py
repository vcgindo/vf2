"""Production policy never infers customer behavior or authorizes a database."""
from copy import deepcopy
import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from mta.runtime import production_scope_policy as policy
from tests.test_runtime_report_request import fixture


def disposition(site='GulfOil'):
    return dict(schema=policy.SCHEMA, purpose=policy.PURPOSE, site_code=site,
        hooks={name: policy.MODE for name in policy.HOOKS},
        input_download='enabled-five-file-four-table-archive', authority='Operator generic policy')


def profile(site='GulfOil'):
    return dict(delivery=dict(site_code=site), daily_publication=True,
        complete_daily=dict(policy=policy.GENERIC_POLICY, consumption_days=90, remark_days=90))


def reference():
    value = fixture()
    value['purpose'] = 'production-generic-placement'
    hook = json.loads(value['hook_json'])
    hook.update(schema=policy.HOOK_SCHEMA, site_code='GulfOil', mode=policy.MODE)
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'),
                                        ensure_ascii=True, allow_nan=False)
    value.update(hook_json=canonical(hook), disposition_json=canonical(disposition()))
    return value


class ProductionScopePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'generic-scope-source-tests')
        import django
        django.setup()

    def test_packaged_profile_needs_explicit_choice_and_uses_initialized_site(self):
        from types import SimpleNamespace
        from mta.runtime.csv_scope_operator import profile_reference, selected_profile
        args = SimpleNamespace(policy='generic', profile='/missing-fixture-scope-profile.json')
        packaged = selected_profile(args)
        self.assertEqual(packaged['schema'], 'vectorflow-production-scope-profile-v1')
        identity = '10000000-0000-4000-8000-000000000001'
        value = profile_reference(packaged, identity, 'b' * 64,
            policy_mode='generic', site_code='GulfOil')
        self.assertEqual(json.loads(value['disposition_json'])['site_code'], 'GulfOil')
        with self.assertRaises(ValueError): profile_reference(packaged, identity, 'b' * 64)
        changed = deepcopy(packaged); changed['client_processing'] = True
        with self.assertRaises(ValueError):
            profile_reference(changed, identity, 'b' * 64, policy_mode='generic', site_code='GulfOil')

    def test_orphan_input_snapshot_cannot_be_treated_as_a_fresh_operation(self):
        from mta.runtime.csv_scope_operator import operation_record
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / 'day'
            self.assertIsNone(operation_record(root))
            root.mkdir()
            (root / 'frozen-input.json').write_text('{"preserve":true}')
            with self.assertRaisesRegex(ValueError, 'before stop'): operation_record(root)
            self.assertTrue((root / 'frozen-input.json').exists())
            (root / 'operation.json').write_text('{"status":"EXECUTING"}')
            self.assertEqual(operation_record(root), {'status': 'EXECUTING'})

    def test_operator_requires_explicit_generic_choice_and_does_not_erase_enabled_input_hook(self):
        from mta.runtime.csv_scope_operator import profile_reference
        old = fixture()
        template = dict(schema='vectorflow-scope-validation-profile-v1',
            configuration=json.loads(old['configuration_json']), hook=json.loads(old['hook_json']),
            disposition=json.loads(old['disposition_json']), authority='Explicit installation selection')
        identity = '10000000-0000-4000-8000-000000000001'
        result = profile_reference(template, identity, 'b' * 64, policy_mode='generic', site_code='GulfOil')
        self.assertEqual(json.loads(result['disposition_json']), policy.configuration(profile(),
            json.loads(result['disposition_json'])))
        self.assertEqual(result['purpose'], 'production-generic-placement')
        retained = profile_reference(template, identity, 'b' * 64)
        self.assertEqual(json.loads(retained['disposition_json'])['site_code'], 'SUPPLIED-INSTANCE')
        changed = deepcopy(template); changed['hook']['mode'] = 'enabled-client'
        with self.assertRaises(ValueError):
            profile_reference(changed, identity, 'b' * 64, policy_mode='generic', site_code='GulfOil')

    def test_retained_recipes_keep_original_identities_and_refuse_source_drift(self):
        from mta.runtime import retained_registered_execution_compatibility as compatible
        from mta.presentation import scoped_artifacts, scoped_batch_files
        compatible._recipe_sources.cache_clear()
        self.addCleanup(compatible._recipe_sources.cache_clear)
        self.assertEqual(scoped_artifacts._recipe(), 'b7047ad865d00062f29575c07e70ce95834a3cc9871ab9dfd0f4a03f546e2f46')
        self.assertEqual(scoped_batch_files.recipe_digest(), '1a244a5376c43b7791ba88b3923e461adc6d9e48d9c3ca6e5deaa32bff46abee')
        original = Path.read_text
        def changed(path, *args, **kwargs):
            return 'unapproved policy source' if path.name == 'production_scope_policy.py' else original(path, *args, **kwargs)
        compatible._recipe_sources.cache_clear()
        with patch.object(Path, 'read_text', changed), self.assertRaisesRegex(ValueError, 'producer source differs'):
            compatible._recipe_sources()

    def test_production_delivery_declaration_keeps_real_label_and_cannot_enter_old_version(self):
        from mta.presentation import scoped_artifacts as artifacts
        value = dict(schema=artifacts.PRODUCTION_SCHEMA, purpose=policy.PURPOSE,
            run_id='10000000-0000-4000-8000-000000000001',
            phase_id='20000000-0000-4000-8000-000000000002', phase_digest='a' * 64,
            input_digest='b' * 64, input_manifest_digest='c' * 64, site_code='GulfOil',
            post_bpr_hook=policy.MODE, input_download=True, importer_database='vectorflow_mta',
            physical_files=list(artifacts.PHYSICAL), input_tables=list(artifacts.TABLES),
            archive_clock='business-midnight-Asia-Kolkata', authority='Explicit generic choice')
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / 'declaration.json'
            def decode(declared):
                raw = json.dumps(declared).encode(); target.write_bytes(raw)
                return artifacts.declaration(target, hashlib.sha256(raw).hexdigest())
            self.assertEqual(decode(value), value)
            with self.assertRaises(ValueError): decode(dict(value, schema=artifacts.SCHEMA))
            with self.assertRaises(ValueError): decode(dict(value, importer_database='../foreign'))

    def test_registered_codec_reconstructs_new_policy_without_adopting_test_contract(self):
        from mta.runtime import report_definition_registration as registration
        value = reference()
        encoded = registration.encode(value,
            initialization_id='10000000-0000-4000-8000-000000000001',
            source_digest='b' * 64, certificate_id='20000000-0000-4000-8000-000000000002',
            certificate_digest='c' * 64)
        self.assertEqual(registration.decode(encoded), value)
        changed = deepcopy(encoded)
        changed['policy']['disposition_json'] = fixture()['disposition_json']
        with self.assertRaises(ValueError): registration.decode(changed)

    def test_new_policy_request_pins_its_actual_release_and_refuses_mixed_test_reference(self):
        from mta.runtime import runtime_report_request as request
        with patch('release.native_identity.require_current', return_value={'release': 'new'}):
            value = request.request('UptoBPR', 'generic-first', runtime_reports=reference())
            self.assertEqual(request.validate_request(value), value)
            with patch('release.native_identity.require_current', return_value={'release': 'different'}):
                with self.assertRaises(ValueError): request.validate_request(value)
                self.assertEqual(request.validate_read_request(value), value)
            changed = reference(); changed['purpose'] = 'owned-placement-publication-test'
            with self.assertRaises(ValueError): request.validate_reference(changed)

    def test_actual_site_is_bound_without_selecting_client_processing(self):
        value = disposition()
        self.assertEqual(policy.configuration(profile(), value), value)
        result = policy.configuration(profile(), value)
        result['hooks']['PostBPR'] = 'changed'
        self.assertEqual(value, disposition())
        with self.assertRaisesRegex(ValueError, 'initialized site'):
            policy.configuration(profile('AnotherSite'), value)

    def test_enabled_unknown_missing_or_extra_effect_cannot_be_ignored(self):
        for name in policy.HOOKS:
            for mode in ('enabled', 'explicit-test-no-op', 'declared-no-op', None):
                changed = disposition(); changed['hooks'][name] = mode
                with self.subTest(name=name, mode=mode), self.assertRaises(ValueError):
                    policy.disposition(changed)
        for change in ('missing', 'extra'):
            changed = disposition()
            if change == 'missing': del changed['hooks']['SiteFinal']
            else: changed['hooks']['GulfOilCustomBTR'] = policy.MODE
            with self.assertRaises(ValueError): policy.disposition(changed)

    def test_site_label_does_not_supply_business_policy(self):
        for generic in (None, {}, dict(policy='GulfOil-client', consumption_days=90, remark_days=90)):
            changed = profile(); changed['complete_daily'] = generic
            with self.assertRaises(ValueError): policy.configuration(changed, disposition())
        changed = profile(); changed['daily_publication'] = 1
        with self.assertRaises(ValueError): policy.configuration(changed, disposition())

    def test_hook_version_is_explicit_and_does_not_adopt_test_noop(self):
        value = dict(schema=policy.HOOK_SCHEMA, placement='PostBPR', mode=policy.MODE,
            site_code='GulfOil', authority='Explicit generic choice', source_sha256='a' * 64)
        self.assertEqual(policy.hook(value), value)
        for key, item in (('schema', 'fresh-runtime-report-hook-configuration-v1'),
                          ('mode', 'declared-no-op'), ('source_sha256', 'wrong')):
            changed = dict(value, **{key: item})
            with self.assertRaises(ValueError): policy.hook(changed)

    def test_existing_roster_is_supported_and_modified_sql_is_denied(self):
        config = json.loads(fixture()['configuration_json'])
        self.assertEqual(policy.report_configuration(config), config)
        for field, value in (('Query', 'SELECT 1'), ('Active', 1), ('Placement', 'Final')):
            changed = deepcopy(config); changed['RuntimeReports'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                policy.report_configuration(changed)
        config['DownloadableUIReportSettings'][0]['Active'] = True
        with self.assertRaises(ValueError): policy.report_configuration(config)

    def test_archive_label_preserves_actual_normal_name_and_rejects_path_or_sql(self):
        for name in ('vectorflow_mta', 'VectorFLOW_MTA', 'vftest_fresh_retained'):
            self.assertEqual(policy.archive_label(name), name)
        for name in ('../vectorflow_mta', 'a/b', 'a\\b', '', 'a;drop', 'x' * 64, None):
            with self.subTest(name=name), self.assertRaises(ValueError): policy.archive_label(name)
