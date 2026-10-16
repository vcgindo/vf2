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
                     'mta/mdm/target_fixture.py', 'parity/temporal_policy.py',
                     'baseline/complete-daily-state-schema-v3.json', 'parity/output_archive.py',
                     'frontend/src/reportWebVitals.ts', 'frontend/src/i18n/config.js', 'frontend/.eslintrc.json',
                     'frontend/public/assets/logo.svg',
                     'frontend/src/mock-data/MCGrid.ts', 'frontend/src/mock-data/RRR-Color-Bandwise.ts',
                     'release/compose.yaml', 'release/frontend.Dockerfile', 'release/.env.example']:
            with self.subTest(name=name):
                self.assertTrue(included(name))

    def test_fixtures_runners_workstation_helpers_secrets_and_databases_are_excluded(self):
        for name in ['tests/test_any.py', 'mta/runtime/test_logistics.py', 'mta/runtime/dbm_filter_probe.py',
                     'mta/runtime/management/commands/prove_btr_gateway.py',
                     'mta/runtime/management/commands/record_parity.py', 'parity/replay_temporal.py',
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
        data=io.BytesIO()
        with tarfile.open(fileobj=data, mode='w') as tar:
            for name, raw in [('manage.py', b'print("entry")'), ('release/.dockerignore', b'**/secrets\n'),
                              ('release/secrets/password', b'not-exported'), ('tests/test_any.py', b'not-exported')]:
                entry=tarfile.TarInfo(name);entry.size=len(raw)
                tar.addfile(entry,io.BytesIO(raw))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            destination=root/'export'
            with patch('release.export.subprocess.check_output',side_effect=[b'a'*40+b'\n',data.getvalue()]):
                receipt=export(root/'repository','HEAD',destination)
            self.assertEqual(set(receipt['files']),{'manage.py','release/.dockerignore','.dockerignore'})
            self.assertEqual((destination/'.dockerignore').read_bytes(),b'**/secrets\n')
            self.assertFalse((destination/'release/secrets/password').exists())
            self.assertEqual(json.loads((destination/'release-source.json').read_text())['source_commit'],'a'*40)
            with self.assertRaisesRegex(ValueError,'existing targets'):
                export(root/'repository','HEAD',destination)
