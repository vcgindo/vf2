"""DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization."""
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from release.export import export, included


class ReleaseExportTests(unittest.TestCase):
    def test_runtime_schema_sql_and_required_input_integrity_library_remain(self):
        for name in ['mta/runtime/migrations/0141_logistics_guards.py', 'mta/presentation/logistics_read.py',
                     'mta/runtime/migrations/0094_nms_force_display_fixture.py',
                     'mta/runtime/migrations/0104_mdm_target_fixture.py',
                     'mta/config/logistics/ui_columns_v1.json', 'vectorflow/settings.py',
                     'mta/mdm/target_fixture.py', 'mta/runtime/input_reader.py',
                     'mta/runtime/management/commands/run_production_upto_dbm.py',
                     'baseline/complete-daily-state-schema-v3.json',
                     'frontend/src/reportWebVitals.ts', 'frontend/src/i18n/config.js', 'frontend/.eslintrc.json',
                     'frontend/public/assets/logo.svg', 'frontend/tsconfig.paths.json',
                     'frontend/src/mock-data/MCGrid.ts', 'frontend/src/mock-data/RRR-Color-Bandwise.ts',
                     'release/compose.yaml', 'release/frontend.Dockerfile', 'release/frontend-build.cjs', 'release/.env.example']:
            with self.subTest(name=name):
                self.assertTrue(included(name))

    def test_fixtures_runners_workstation_helpers_secrets_and_databases_are_excluded(self):
        for name in ['tests/test_any.py', 'mta/runtime/test_logistics.py', 'mta/runtime/dbm_filter_probe.py',
                     'mta/fixtures/r1_raw_current_day.json', 'mta/fixtures/r1_importer_master_base.json',
                     'mta/runtime/management/commands/prove_btr_gateway.py',
                     'mta/runtime/management/commands/record_parity.py', 'parity/replay_temporal.py', 'parity/output_archive.py', 'parity/temporal_policy.py',
                     'development/validation_storage.py', 'development/preacceptance_actions.py',
                     'mta/runtime/management/commands/publish_pick_projection.py',
                     'mta/runtime/management/commands/verify_application_reads.py',
                     'mta/runtime/management/commands/verify_offline_terminal.py',
                     'baseline/synthetic-temporal-business-v1.json', 'legacy/data.dll', 'legacy/run.bat',
                     'user-service/api/management/commands/bootstrap_stage7b.py', 'mto/build_exe.py',
                     'frontend/src/Example.test.tsx', 'frontend/node_modules/x.js',
                     'frontend/src/mock-data/BPR.ts', 'frontend/src/mock-data/MDM.ts',
                     'release/secrets/password', 'release/.env', 'release/private.pem',
                     '../outside.py', '/absolute.py']:
            with self.subTest(name=name):
                self.assertFalse(included(name))

    def test_export_uses_only_committed_regular_files_and_refuses_existing_destination(self):
        schema_name = 'baseline/planning-april-empty-requests-v1.json'
        root_source = Path(__file__).resolve().parents[1]
        schema = (root_source/schema_name).read_bytes()
        schema_sha = '0cec4bea850da03b9e57d59fe114a15d68fb60254637988451b609995757a33c'
        self.assertEqual(hashlib.sha256(schema).hexdigest(), schema_sha)
        self.assertEqual(tuple(c['name'] for c in json.loads(schema)['columns']),
            ('SKUCode', 'WhCode', 'ParentWhCode', 'Request', 'RequestDate',
             'Action', 'ActionDate', 'UserId', 'ETA'))
        for filename, constant in [('daily_requests.py', 'SCHEMA_SHA'),
                                   ('planning_expedite_requests.py', 'SOURCE_SHA')]:
            reader = (root_source/'mta/presentation'/filename).read_text()
            values = {node.targets[0].id: ast.literal_eval(node.value)
                for node in ast.parse(reader).body
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == constant}
            self.assertEqual(values[constant], schema_sha)
            self.assertIn(schema_name, reader)
        data=io.BytesIO()
        delivery_commands = {
            'mta/runtime/management/commands/'+name+'.py':
                (root_source/'mta/runtime/management/commands'/ (name+'.py')).read_bytes()
            for name in ('register_runtime_report_configuration', 'publish_diagnostic_download')}
        with tarfile.open(fileobj=data, mode='w') as tar:
            for name, raw in [('manage.py', b'print("entry")'), ('release/.dockerignore', b'**/secrets\n'),
                              ('requirements.txt', b'Django==5.2.17\n'),
                              ('frontend/tsconfig.json', b'{"extends":"./tsconfig.paths.json"}\n'),
                              ('frontend/tsconfig.paths.json', b'{"compilerOptions":{"baseUrl":"."}}\n'),
                              ('mta/mdm/initialization.py', b"IMPLEMENTATION_FILES = ('mdm/initialization.py',)\n"),
                              ('mta/runtime/migrations/0142_native_evidence_default.py', b'# migration\n'),
                              ('vectorflow/settings.py', b'# settings\r\n'),
                              ('baseline/production-state-schema.json', b'{}\n'),
                              (schema_name, schema),
                              ('baseline/manifest.json', b'not-exported'),
                              ('baseline/unrelated-schema.json', b'not-exported'),
                              ('mta/fixtures/current-day.json', b'not-exported'),
                              ('evidence/receipt.json', b'not-exported'),
                              ('release/secrets/password', b'not-exported'), ('tests/test_any.py', b'not-exported'),
                              *delivery_commands.items()]:
                entry=tarfile.TarInfo(name);entry.size=len(raw)
                tar.addfile(entry,io.BytesIO(raw))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            destination=root/'export'
            with patch('release.export.subprocess.check_output',side_effect=[b'a'*40+b'\n',data.getvalue()]):
                receipt=export(root/'repository','HEAD',destination)
            self.assertEqual(set(receipt['files']),{'manage.py','requirements.txt','release/.dockerignore','.dockerignore',
                'frontend/tsconfig.json', 'frontend/tsconfig.paths.json',
                'mta/mdm/initialization.py', 'mta/runtime/migrations/0142_native_evidence_default.py',
                'vectorflow/settings.py', 'baseline/production-state-schema.json', schema_name, *delivery_commands})
            self.assertEqual((destination/schema_name).read_bytes(), schema)
            self.assertEqual((destination/'vectorflow/settings.py').read_bytes(), b'# settings\r\n')
            self.assertEqual(receipt['files']['vectorflow/settings.py'],
                             hashlib.sha256(b'# settings\r\n').hexdigest())
            self.assertEqual(receipt['files'][schema_name], schema_sha)
            self.assertEqual((destination/'.dockerignore').read_bytes(),b'**/secrets\n')
            self.assertFalse((destination/'release/secrets/password').exists())
            self.assertEqual(json.loads((destination/'release-source.json').read_text())['source_commit'],'a'*40)
            self.assertEqual((destination/'release-source.json').read_bytes(),
                             (json.dumps(receipt, indent=2) + '\n').encode('utf-8'))
            from release.native_identity import MANIFEST
            native = json.loads((destination/MANIFEST).read_text())
            self.assertEqual((destination/MANIFEST).read_bytes(),
                             (json.dumps(native, sort_keys=True, indent=2) + '\n').encode('utf-8'))
            self.assertEqual(native['source_commit'], 'a'*40)
            self.assertEqual(native['files'], {name: receipt['files'][name] for name in native['files']})
            self.assertEqual(native['files'][schema_name], schema_sha)
            for name, raw in delivery_commands.items():
                self.assertEqual((destination/name).read_bytes(), raw)
                self.assertEqual(native['files'][name], hashlib.sha256(raw).hexdigest())
                self.assertEqual(receipt['files'][name], native['files'][name])
            self.assertNotIn('release/.dockerignore', native['files'])
            with self.assertRaisesRegex(ValueError,'existing targets'):
                export(root/'repository','HEAD',destination)

    def test_build_identity_has_canonical_bytes_and_authenticates_export_descriptors(self):
        from release.compose_build import build

        commit = 'a' * 40
        source_raw = b'{\n  "source_commit": "' + commit.encode('ascii') + b'"\n}\n'
        native_raw = b'{\n  "files": {}\n}\n'

        def export_files(repository, revision, destination):
            self.assertEqual(revision, commit)
            frontend = destination / 'frontend'
            frontend.mkdir(parents=True)
            (frontend / 'tsconfig.json').write_bytes(b'{"extends":"./tsconfig.paths.json"}\n')
            (frontend / 'tsconfig.paths.json').write_bytes(b'{}\n')
            (destination / 'release-source.json').write_bytes(source_raw)
            (destination / 'release-native-source.json').write_bytes(native_raw)
            return {'source_commit': commit}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / 'repository'
            (repository / '.git').mkdir(parents=True)
            output = root / 'build'
            with patch('release.compose_build.require_clean'), \
                    patch('release.compose_build.subprocess.check_output', return_value=commit.encode('ascii')), \
                    patch('release.compose_build.export', side_effect=export_files), \
                    patch('release.compose_build.wheels') as wheels, \
                    patch('release.compose_build.prepare', return_value={'packaging_tool_sha256': 'b' * 64}) as prepare, \
                    patch('builtins.print'):
                build(repository, output)
            expected = dict(source_commit=commit, source_sha256=hashlib.sha256(source_raw).hexdigest(),
                            native_sha256=hashlib.sha256(native_raw).hexdigest(), packaging_tool_sha256='b' * 64)
            self.assertEqual((output / 'identity.json').read_bytes(),
                             (json.dumps(expected, sort_keys=True, indent=2) + '\n').encode('utf-8'))
            self.assertEqual(json.loads((output / 'identity.json').read_bytes()), expected)
            wheels.assert_called_once_with(output / 'export', output / 'wheels')
            prepare.assert_called_once_with(output / 'export', output / 'mta-context', output / 'wheels',
                                           commit=commit, source_sha256=expected['source_sha256'],
                                           native_sha256=expected['native_sha256'])
