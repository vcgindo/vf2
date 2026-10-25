"""Native Step4 mode/registration/dispatch contracts; every DB call is forbidden."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from contextlib import nullcontext
from unittest.mock import patch,MagicMock
from uuid import uuid4

os.environ.setdefault('VF_SECRET_KEY','step4-boundary-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.test import override_settings
from django.core.management.base import CommandError
from mta.presentation import native_mode
from mta.presentation.context import PublicationUnavailable
from mta.runtime.management.commands import register_operational_configuration as registration
from mta.runtime.operational_attempts import POLICY
from mta.runtime.operational_runner import RUNNER_POLICY,ROSTER
from mta.serialization import digest


class Step4NativeBoundaryTests(unittest.TestCase):
    def setUp(self):
        guard=patch('django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection',
                    side_effect=AssertionError('No Step4 DB authority'))
        guard.start();self.addCleanup(guard.stop)

    def configuration(self):
        return dict(source_digest=digest(ROSTER),bindings=dict(opening_input_digest='a'*64,
            runner_policy=RUNNER_POLICY,operation_roster=deepcopy(ROSTER),
            zip_tool={'path':str(Path.cwd()/'owned-pinned-tool'),'sha256':'c'*64}),
            settings=[{'ordinal':0,'name':'UIUploadLogHorizon','value':'7'}],
            tables=[{'ordinal':0,'database_name':'owned','table_name':'MasterDataRaw','condition':None}],
            alerts=[{'ordinal':0,'name':'native-local-alert','active':False}])

    def test_each_removed_setting_rejects_before_selection_query_or_unselected_startup(self):
        from mta.presentation.context import selected_run
        from mta.presentation.admission import AdmittedApplication
        for name in native_mode.REMOVED_SETTINGS:
            with self.subTest(name=name),override_settings(**{name:'configured-historical'}):
                with self.assertRaisesRegex(PublicationUnavailable,'removed_historical_mode'):
                    native_mode.require_configuration()
                with self.assertRaises(PublicationUnavailable):
                    selected_run()
                with self.assertRaises(PublicationUnavailable):
                    AdmittedApplication(lambda *a:None)

    def test_preparation_requires_explicit_native_run_before_owner_query(self):
        from mta.presentation.daily_preparation import command_binding
        with self.assertRaisesRegex(PublicationUnavailable,'explicit_native_preparation_run_required'):
            command_binding()

    def test_all_four_native_builder_targets_dispatch_without_old_commands(self):
        from mta.presentation import daily_preparation as prep,daily_native_prepared as native
        self.assertEqual(set(native.BUILDERS),{'bpr','guided_history','guided_dbm','guided_chronic'})
        self.assertFalse(set(native.BUILDERS)&set(prep.COMMANDS))
        run=NS(pk='run')
        for layer in native.BUILDERS:
            receipt={'source_digest':'source','recipe_digest':'recipe','rows_digest':'rows','row_count':2}
            with self.subTest(layer=layer),patch('mta.presentation.native_publication.require_mode'), \
                    patch.object(prep,'source_digest',return_value='source'), \
                    patch.object(prep,'_require_ancillary'),patch.object(native,'prepare',return_value=receipt) as owner, \
                    patch.object(prep,'_command_result',side_effect=AssertionError('historical command fallback')):
                self.assertEqual(prep.prepare_layer(run,layer),receipt)
                owner.assert_called_once_with(run,layer)
                owner.reset_mock()
                self.assertEqual(prep.verify_layer(run,layer,receipt),receipt)
                owner.assert_called_once_with(run,layer,verify_only=True)

    def test_registration_preserves_exact_ordered_config_and_repeated_owner_identity(self):
        config=self.configuration();before=deepcopy(config)
        source=NS(digest='d'*64,database_name='owned',
            receipt={'schema':'fresh-production-mdm-source-v1','owned_namespace':{'database_name':'owned'}})
        run=NS(pk=uuid4(),kind='DAILY_CHAIN',status='SUCCEEDED',evidence_mode='production',
            input_digest='a'*64,output_digest='b'*64,mdm_input_capture=NS(source=source))
        expected={'policy':POLICY,**config};owner=NS(pk=digest(expected))
        with TemporaryDirectory() as directory:
            path=Path(directory)/'configuration.json';raw=json.dumps(config).encode();path.write_bytes(raw)
            options=dict(configuration=path,sha256=hashlib.sha256(raw).hexdigest(),run_id=str(run.pk),
                input_digest=run.input_digest,output_digest=run.output_digest,mdm_source_digest=source.digest)
            with patch.object(registration.transaction,'atomic',return_value=nullcontext()), \
                    patch('mta.runtime.models.CalculationRun.objects') as runs, \
                    patch('mta.mdm.production_families.require_binding') as binding, \
                    patch('mta.runtime.services.read_outputs',return_value={}) as outputs, \
                    patch('mta.runtime.operational_attempts.register_configuration',return_value=owner) as register, \
                    patch('mta.runtime.operational_attempts.configuration_value',return_value=expected), \
                    patch('mta.runtime.operational_runner.validate_configuration',return_value=expected) as validate:
                runs.select_related.return_value.get.return_value=run
                for _ in range(2):
                    out=io.StringIO();registration.Command(stdout=out).handle(**options)
                    self.assertEqual(json.loads(out.getvalue())['configuration_id'],owner.pk)
                self.assertEqual(register.call_count,2)
                register.assert_called_with(**config)
                binding.assert_called_with(source,read_only=True)
                outputs.assert_called_with(run);validate.assert_called_with(owner)
            self.assertEqual(config,before)

    def test_configuration_bad_hash_placeholder_fields_and_ordinals_deny_before_db(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'config.json'
            for change in (
                lambda c:c['bindings'].update(opening_input_digest='$FIRST_RUN_INPUT_DIGEST'),
                lambda c:c['settings'][0].update(ordinal=1),
                lambda c:c.update(extra='unbounded'),
                lambda c:c['tables'][0].update(extra='wrong')):
                value=self.configuration();change(value);raw=json.dumps(value).encode();path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    registration.read_configuration(path,hashlib.sha256(raw).hexdigest())
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError,'SHA256'):
                registration.read_configuration(path,'0'*64)

    def test_target_fixture_guards_reject_instead_of_admitting_empty_native(self):
        from mta.mdm import target_fixture as target
        with self.assertRaisesRegex(ValueError,'removed'):
            target.require_family(NS(),NS(provenance={'schema':target.SCHEMA}),'force')
        self.assertFalse(target.require_family(NS(),NS(provenance={'schema':'native'}),'force'))
        with self.assertRaises(ValueError):
            target.consumer_rows(NS(digest=target.SOURCE),NS(),'path')

    def test_native_count_uses_ordinary_cursor_without_fixture_settings(self):
        from mta.presentation import btr_sql
        import inspect
        self.assertNotIn('count_cursor',inspect.getsource(btr_sql))
        self.assertNotIn('SET LOCAL',inspect.getsource(btr_sql))

    def test_final_command_inventory_preserves_all_released_native_owners(self):
        from release.export import SUPPORTED_MTA_COMMANDS,included
        self.assertEqual(len(SUPPORTED_MTA_COMMANDS),29)
        self.assertTrue({'run_production_upto_bpr','run_production_upto_dbm','fence_production_scope'}<=SUPPORTED_MTA_COMMANDS)
        for name in SUPPORTED_MTA_COMMANDS:
            self.assertTrue(included('mta/runtime/management/commands/'+name+'.py'))
        for name in ('run_current_day','publish_pick_projection','activate_offline_readers','install_offline_input_source',
                     'prepare_bor_sources','prepare_boroa_sources','accept_daily_operational',
                     'register_cohort6_operational','bind_mdm_integration','install_mdm_force'):
            self.assertFalse(included('mta/runtime/management/commands/'+name+'.py'))
        self.assertTrue(included('baseline/operational-alert-source-pins.json'))
        self.assertFalse(included('development/step4_originals/mta/presentation/fixture.py'))



    def test_registration_readback_and_validator_are_atomic_and_failure_has_no_success_output(self):
        from contextlib import contextmanager
        config=self.configuration()
        source=NS(digest='d'*64,database_name='owned',
            receipt={'schema':'fresh-production-mdm-source-v1','owned_namespace':{'database_name':'owned'}})
        run=NS(pk=uuid4(),kind='DAILY_CHAIN',status='SUCCEEDED',evidence_mode='production',
            input_digest='a'*64,output_digest='b'*64,mdm_input_capture=NS(source=source))
        expected={'policy':POLICY,**config};owner=NS(pk=digest(expected))
        for failure in (None,'readback','validator'):
            events=[];inside=[False]
            @contextmanager
            def atomic():
                inside[0]=True;events.append('enter')
                try:yield
                except Exception:
                    events.append('rollback');raise
                else:events.append('commit')
                finally:inside[0]=False
            def operation(name,value):
                def call(*a,**kw):
                    self.assertTrue(inside[0],name)
                    events.append(name)
                    if failure==name:raise ValueError('forced '+name+' failure')
                    return value
                return call
            with TemporaryDirectory() as directory:
                path=Path(directory)/'configuration.json';raw=json.dumps(config).encode();path.write_bytes(raw)
                options=dict(configuration=path,sha256=hashlib.sha256(raw).hexdigest(),run_id=str(run.pk),
                    input_digest=run.input_digest,output_digest=run.output_digest,mdm_source_digest=source.digest)
                output=io.StringIO()
                with patch.object(registration.transaction,'atomic',side_effect=atomic), \
                        patch('mta.runtime.models.CalculationRun.objects') as runs, \
                        patch('mta.mdm.production_families.require_binding'), \
                        patch('mta.runtime.services.read_outputs',return_value={}), \
                        patch('mta.runtime.operational_attempts.register_configuration',side_effect=operation('register',owner)), \
                        patch('mta.runtime.operational_attempts.configuration_value',side_effect=operation('readback',expected)), \
                        patch('mta.runtime.operational_runner.validate_configuration',side_effect=operation('validator',expected)):
                    runs.select_related.return_value.get.return_value=run
                    if failure:
                        with self.assertRaisesRegex(CommandError,'forced '+failure):
                            registration.Command(stdout=output).handle(**options)
                        self.assertEqual(output.getvalue(),'')
                        self.assertEqual(events[-1],'rollback')
                    else:
                        registration.Command(stdout=output).handle(**options)
                        self.assertEqual(events,['enter','register','readback','validator','commit'])
                        self.assertEqual(json.loads(output.getvalue())['configuration_id'],owner.pk)
                    self.assertFalse(inside[0])



    def test_registration_denies_wrong_run_source_namespace_opening_and_readback(self):
        config=self.configuration()
        source=NS(digest='d'*64,database_name='owned',
            receipt={'schema':'fresh-production-mdm-source-v1','owned_namespace':{'database_name':'owned'}})
        template=NS(pk=uuid4(),kind='DAILY_CHAIN',status='SUCCEEDED',evidence_mode='production',
            input_digest='a'*64,output_digest='b'*64,mdm_input_capture=NS(source=source))
        for fault in ('status','output','source','namespace','opening','runner'):
            value=deepcopy(config);run=deepcopy(template)
            if fault=='status':run.status='FAILED'
            if fault=='output':run.output_digest='x'*64
            if fault=='source':run.mdm_input_capture.source.digest='x'*64
            if fault=='namespace':run.mdm_input_capture.source.receipt['owned_namespace']['database_name']='foreign'
            if fault=='opening':value['bindings']['opening_input_digest']='x'*64
            if fault=='runner':value['bindings']['runner_policy']='arbitrary'
            with self.subTest(fault=fault),TemporaryDirectory() as directory:
                path=Path(directory)/'config.json';raw=json.dumps(value).encode();path.write_bytes(raw)
                options=dict(configuration=path,sha256=hashlib.sha256(raw).hexdigest(),run_id=str(template.pk),
                    input_digest=template.input_digest,output_digest=template.output_digest,mdm_source_digest=source.digest)
                output=io.StringIO()
                with patch('mta.runtime.models.CalculationRun.objects') as runs, \
                        patch('mta.mdm.production_families.require_binding'), \
                        patch('mta.runtime.services.read_outputs',return_value={}), \
                        patch('mta.runtime.operational_attempts.register_configuration',side_effect=AssertionError('must not register')) as register:
                    runs.select_related.return_value.get.return_value=run
                    with self.assertRaises(CommandError):
                        registration.Command(stdout=output).handle(**options)
                    register.assert_not_called()
                    self.assertEqual(output.getvalue(),'')



    def test_native_command_guards_reject_before_input_query_or_writer(self):
        from importlib import import_module
        from mta.presentation.daily_preparation import command_binding
        commands=('prepare_daily_ui','activate_daily_ui','check_daily_selection','prepare_guided_aggregates',
                  'initialize_production','run_production_day','run_production_upto_bpr','fence_production_scope')
        for name in commands:
            command=import_module('mta.runtime.management.commands.'+name).Command(stdout=io.StringIO())
            with self.subTest(command=name),override_settings(VF_MTA_FIXTURE_FILE='retired.json'):
                with self.assertRaisesRegex(PublicationUnavailable,'removed_historical_mode'):
                    command.handle()
        for name in commands[:4]:
            command=import_module('mta.runtime.management.commands.'+name).Command(stdout=io.StringIO())
            with self.subTest(command=name),override_settings(VF_MTA_NATIVE_PUBLICATION=False,VF_MTA_DAILY_PUBLICATION=False):
                with self.assertRaisesRegex(PublicationUnavailable,'native_daily_publication_required'):
                    command.handle()
        with override_settings(VF_MTA_NATIVE_PUBLICATION=False,VF_MTA_DAILY_PUBLICATION=False):
            with self.assertRaisesRegex(PublicationUnavailable,'native_daily_publication_required'):
                command_binding('explicit-run-not-queried')


if __name__=='__main__':unittest.main()
