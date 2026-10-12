"""Command preflight and package contract; calculation is explicitly forbidden."""
import ast
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.application import daily_finalization as final
from mta.runtime.management.commands import run_temporal as runner


class DailyMdmBaselineRegressionTests(unittest.TestCase):
    def test_null_permission_roots_deny_leaf_submission_without_writes(self):
        from mta.mdm import tasks, location_tasks
        for module, family, kind, key, prefix, attribute_model, requested_model in (
                (tasks, 1, 'products', 'sc', 'SL', 'MdmSkuAttributes', 'MdmSkuRequested'),
                (location_tasks, 2, 'locations', 'wc', 'LL', 'MdmLocationAttributes', 'MdmLocationRequested')):
            row = {key: 'LEAF', prefix + '1': 'Root', prefix + '2': 'Group', prefix + '3': 'Leaf'}
            catalogue = {kind: {'records': [dict(id=1, level_1='Root', level_2=None, level_3=None)]}}
            payload = dict(id=family, taskId='', data=[row], all_users=[],
                           **{'product_permissions' if family == 1 else 'location_permissions': [1]})
            with self.subTest(family=family), \
                    patch.object(module, 'permission_catalogue', return_value=catalogue), \
                    patch.object(getattr(module, attribute_model).objects, 'filter') as query, \
                    patch.object(getattr(module, requested_model).objects, 'bulk_create') as write, \
                    patch.object(module.MdmTask.objects, 'create') as task:
                query.return_value.values_list.return_value = []
                result = module.submit(object(), payload, {'id': 2, 'name': 'unit-only'}, 1)
                self.assertEqual(result['errorCount'], '1')
                self.assertEqual(result['error'][0]['errorData'], [row])
                write.assert_not_called()
                task.assert_not_called()

    def test_temporal_preflight_forwards_active_and_inactive_policy(self):
        for policy, active in ((final.ACTIVE_POLICY, '1'), (final.POLICY, '0')):
            with self.subTest(policy=policy), TemporaryDirectory() as directory:
                root = Path(directory)
                opening = {'importer_settings': [
                    dict(Parameter='NMSActive', Value=active),
                    dict(Parameter='IsBatchFileExecuted', Value='0'),
                    dict(Parameter='IsBPRBatchFileExecuted', Value='0'),
                    dict(Parameter='BatchFileExecutionDate', Value='2026-06-05')]}
                artifact = {'schema': 'unit-preflight-only', 'case': dict(
                    case='unit-preflight-only', opening=opening, opening_date='2026-06-05',
                    profile={}, static_day={}, commands=[],
                    days=[dict(business_date='2026-06-06')])}
                source = root / 'input.json'
                raw = json.dumps(artifact).encode()
                source.write_bytes(raw)
                checksum = hashlib.sha256(raw).hexdigest()
                complete = {name: [] for name in final.REQUIRED}
                complete['ScriptExecutedFlag'] = deepcopy(final.FLAG_SEED)
                config = root / 'finalization.json'
                content = json.dumps(dict(schema='generic-finalization-input-v1',
                    artifact_sha256=checksum, opening_complete=complete,
                    configuration=dict(policy=policy, consumption_days=90, remark_days=90))).encode()
                config.write_bytes(content)
                command = runner.Command(stdout=io.StringIO())
                options = vars(command.create_parser('manage.py', 'run_temporal').parse_args([
                    str(source), '--sha256', checksum, '--revision', 'unit-preflight-only',
                    '--evidence', str(root / 'evidence'), '--through', '0',
                    '--finalization-config', str(config), '--finalization-config-sha256',
                    hashlib.sha256(content).hexdigest()]))
                with patch.object(runner, 'execute_day',
                                  side_effect=RuntimeError('unit stop before calculation')) as execute:
                    with self.assertRaisesRegex(RuntimeError, 'unit stop before calculation'):
                        command.handle(**options)
                execute.assert_called_once()
                call = execute.call_args.kwargs
                self.assertEqual(call['profile']['complete_daily']['policy'], policy)
                self.assertEqual(call['opening']['state']['importer_settings'], opening['importer_settings'])
                self.assertEqual(call['finalization_config'], content)
                self.assertEqual(source.read_bytes(), raw)

    def test_package_requires_complete_reporting_coordinator_and_summary(self):
        path = Path(__file__).resolve().parents[1] / 'packaging/mdm_approval_day/execute-day.sh'
        script = path.read_text()
        section = script.split('# 4. Prepare all required native layers', 1)[1].split("\nPY\n", 1)[0]
        python = section.split("<<'PY'", 1)[1].split('\n', 1)[1]
        tree = ast.parse(python)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        coordinators = [node for node in calls if isinstance(node.func, ast.Name)
                        and node.func.id == 'prepare_reporting_generation']
        self.assertEqual(len(coordinators), 1)
        self.assertEqual([kw.arg for kw in coordinators[0].keywords], ['expected_output_digest'])
        self.assertFalse(any(isinstance(node.func, ast.Name) and node.func.id == 'prepare' for node in calls))
        guards = [node.test for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        self.assertTrue(any(any(isinstance(node, ast.Attribute) and node.attr == 'status'
                               and isinstance(node.value, ast.Name) and node.value.id == 'summary'
                               for node in ast.walk(guard)) for guard in guards))
