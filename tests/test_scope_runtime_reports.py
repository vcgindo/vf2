"""Native configuration capture and operator file boundary; no renderer claims."""
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from mta.runtime import scope_runtime_reports as module


def declaration(provenance='User-approved empty RuntimeReports for newly owned scoped tests'):
    return dict(schema=module.SCHEMA,purpose='owned-scoped-test',provenance=provenance,RuntimeReports=[])


def reference():
    raw=json.dumps(declaration(),ensure_ascii=False).encode()
    return module.decode(raw,hashlib.sha256(raw).hexdigest())


class ScopeRuntimeReportsTests(unittest.TestCase):
    def test_file_identity_is_exact_bounded_and_duplicate_safe(self):
        raw=json.dumps(declaration('Explicit test declaration — retained user approval')).encode()
        pin=hashlib.sha256(raw).hexdigest()
        with TemporaryDirectory() as root:
            path=Path(root)/'runtime-reports.json';path.write_bytes(raw)
            actual=module.load(path,pin)
            self.assertEqual(actual['configuration'],json.loads(raw))
            self.assertEqual(module.status(actual),dict(configured=True,purpose='owned-scoped-test',row_count=0,
                sha256=pin,configuration_digest=actual['configuration_digest']))
            path.write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'bytes differ'):module.load(path,pin)
            with path.open('wb') as stream:stream.write(b' '*(module.LIMIT+1))
            with self.assertRaisesRegex(ValueError,'bytes differ'):module.load(path,pin)
        duplicate=raw[:-1]+b',"RuntimeReports":[]}'
        with self.assertRaises(ValueError):module.decode(duplicate,hashlib.sha256(duplicate).hexdigest())
        self.assertEqual(module.status(None),dict(configured=False))

    def test_nonempty_wrong_purpose_and_corrupt_references_deny(self):
        for changes in (dict(RuntimeReports=[dict(Id=1,Active=True,Placement='PostBPR')]),
                dict(RuntimeReports={}),dict(purpose='production'),dict(provenance=' '),dict(extra=[])):
            raw=json.dumps(dict(declaration(),**changes)).encode()
            with self.subTest(changes=changes),self.assertRaises(ValueError):module.decode(raw,hashlib.sha256(raw).hexdigest())
        valid=reference()
        for changes in (dict(schema='other'),dict(configuration_digest='f'*64),dict(sha256=True),dict(extra=1)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):module.validate(dict(valid,**changes))
        checked=module.validate(valid);checked['configuration']['provenance']='changed caller object'
        self.assertNotEqual(checked,valid)

    def test_configured_request_is_frozen_and_default_full_and_scope_bytes_stay_unchanged(self):
        from mta.runtime.production_scope import request,validate_request,CONFIGURED_SCHEMA
        from mta.runtime.temporal import request_input
        with patch('release.native_identity.require_current',return_value={'source_commit':'a'*40}), \
                patch('mta.runtime.phase_state.recipe_digest',return_value='b'*64):
            ordinary=request('command');configured=request('command',runtime_reports=reference())
            self.assertEqual(configured['schema'],CONFIGURED_SCHEMA)
            self.assertEqual({k:v for k,v in configured.items() if k not in ('schema','runtime_reports')},
                {k:v for k,v in ordinary.items() if k!='schema'})
            self.assertEqual(validate_request(configured),configured)
            self.assertEqual(validate_request(ordinary),ordinary)
            with self.assertRaises(ValueError):validate_request(dict(configured,runtime_reports=None))
            raw=request_input(day={},profile={},initial=None,lineage={},scope_request=configured)
            configured['runtime_reports']['configuration']['provenance']='later caller change'
            self.assertNotEqual(raw['scope_request'],configured)
            full=request_input(day={},profile={},initial=None,lineage={})
            self.assertNotIn('scope_request',full)
            self.assertEqual({k:v for k,v in raw.items() if k!='scope_request'},full)

    def options(self,root):
        source=Path(root)/'day.json';source.write_bytes(b'day')
        return dict(input=source,sha256='d'*64,initialization='init',source_digest='s'*64,
            configuration_digest='c'*64,revision='rev',pick_output_root=root,predecessor=None,
            predecessor_output_digest=None,command_key='command',worker_reference='worker',
            recovery_of=None,repair_files=False,inspect=False,runtime_reports_file=None,runtime_reports_sha256=None)

    def test_command_requires_pair_and_forwards_checked_declaration(self):
        from django.core.management.base import CommandError
        from mta.runtime.management.commands.run_production_upto_bpr import Command
        from mta.runtime.management.commands.run_production_day import Command as Full
        with TemporaryDirectory() as root,patch('mta.presentation.native_mode.require_configuration'), \
                patch('mta.runtime.production_scope.execute',return_value={'scope_ready':False}) as execute:
            path=Path(root)/'roster.json';raw=json.dumps(declaration()).encode();path.write_bytes(raw)
            options=self.options(root);command=Command(stdout=io.StringIO())
            for pair in ((path,None),(None,'a'*64)):
                with self.assertRaisesRegex(CommandError,'supplied together'):
                    command.handle(**dict(options,runtime_reports_file=pair[0],runtime_reports_sha256=pair[1]))
            execute.assert_not_called()
            command.handle(**dict(options,runtime_reports_file=path,runtime_reports_sha256=hashlib.sha256(raw).hexdigest()))
            self.assertEqual(execute.call_args.kwargs['runtime_reports'],module.decode(raw,hashlib.sha256(raw).hexdigest()))
            command.handle(**options)
            self.assertIsNone(execute.call_args.kwargs['runtime_reports'])
            for name in ('--runtime-reports-file','--runtime-reports-sha256'):
                self.assertNotIn(name,Full().create_parser('manage.py','run_production_day')._option_string_actions)
                self.assertIn(name,command.create_parser('manage.py','run_production_upto_bpr')._option_string_actions)

    def test_production_database_denied_before_any_retry_or_new_capture(self):
        from mta.runtime import production_scope as scope
        with patch('release.native_identity.require_current',return_value={'source_commit':'a'*40}), \
                patch('mta.runtime.phase_state.recipe_digest',return_value='b'*64), \
                patch.object(scope.transaction,'get_autocommit',return_value=True), \
                patch.object(scope,'authorize') as authorize, \
                patch('mta.runtime.scope_runtime_reports.require_test_database',side_effect=ValueError('test database required')), \
                patch.object(scope,'repeated') as repeated,patch('mta.runtime.production_daily.execute') as capture:
            with self.assertRaisesRegex(ValueError,'test database required'):
                scope.execute(b'day','a'*64,command_key='command',worker_reference='worker',runtime_reports=reference())
            authorize.assert_called_once_with();repeated.assert_not_called();capture.assert_not_called()

    def test_database_restriction_uses_actual_connection_identity(self):
        with patch('django.db.connection') as db:
            cursor=db.cursor.return_value.__enter__.return_value
            for name in ('vectorflow_mta','VFTEST_Other','VFTEST_Fresh'):
                cursor.fetchone.return_value=(name,)
                with self.assertRaisesRegex(ValueError,'owned VFTEST_Fresh database'):module.require_test_database()
            cursor.fetchone.return_value=('VFTEST_Fresh_LifecycleG2_20261024',)
            module.require_test_database()
            cursor.execute.assert_called_with('SELECT current_database()')

    def test_v3_metadata_codec_retains_complete_configuration_without_row_payloads(self):
        # Pure storage contract only. The real native V3 pipeline's separate
        # initialization owner still needs its own supported-command proof.
        from types import SimpleNamespace
        from tests.test_input_storage_v3 import MemoryImages,run_identity,OWNER
        from mta.runtime import input_storage
        from mta.serialization import digest
        raw=dict(profile=dict(delivery=dict(site_code='SCOPED-TEST')),
            scope_request=dict(runtime_reports=reference()))
        owner=SimpleNamespace(pk=OWNER,input_digest=digest(raw),kind='DAILY_CHAIN')
        images=MemoryImages()
        owner.input_payload=input_storage.save_input(owner,raw,version=3,
            image_writer=images.write,table_selector=lambda *args:None,identity_resolver=run_identity)
        owner.input_manifest_digest=digest(owner.input_payload)
        self.assertEqual(input_storage.read_input(owner,image_reader=images.read,identity_resolver=run_identity),raw)
        self.assertEqual(images.writes,[])
