"""Native entry identities and unchanged Full request bytes; no native acceptance."""
import unittest
from unittest.mock import patch


class ProductionScopeTests(unittest.TestCase):
    def test_request_has_native_compatibility_and_no_worker_identity(self):
        from mta.runtime.production_scope import request,validate_request
        from mta.runtime.temporal import request_input
        with patch('release.native_identity.require_current',return_value={'source_commit':'a'*40}), \
                patch('mta.runtime.phase_state.recipe_digest',return_value='b'*64):
            value=request('command')
            self.assertEqual(validate_request(value),value)
            for key,replacement in (('scope','PostBPR'),('compatibility_digest','c'*64),('worker','new')):
                changed=dict(value,**{key:replacement})
                with self.assertRaisesRegex(ValueError,'identity differs'):validate_request(changed)
            with self.assertRaises(ValueError):request('')
        arguments=dict(day={'day':1},profile={'profile':2},initial=None,lineage={'lineage':3})
        full=request_input(**arguments)
        self.assertEqual(full,dict(schema='fresh-daily-chain-v1',day={'day':1},profile={'profile':2},
            opening=None,lineage={'lineage':3},report_exceptions={}))
        scoped=request_input(**arguments,scope_request=value)
        self.assertEqual({k:v for k,v in scoped.items() if k!='scope_request'},full)
        self.assertIsNot(scoped['scope_request'],value)

    def test_native_role_authorization_requires_installer_and_actual_registration(self):
        from mta.runtime.production_scope import authorize
        with patch('mta.runtime.production_scope.connection') as db, \
                patch('mta.mdm.owned_namespace._database_identity',return_value={'db':1}), \
                patch('mta.mdm.owned_namespace._registered_identity',return_value={'reg':2}), \
                patch('mta.mdm.owned_namespace._catalogue_evidence',return_value={'evidence':3}), \
                patch('mta.mdm.owned_namespace._validate_identity',side_effect=ValueError('unapproved role')) as guard:
            with self.assertRaisesRegex(ValueError,'unapproved role'):authorize()
            guard.assert_called_once_with({'db':1},{'reg':2},{'evidence':3},installer=True)
            db.cursor.return_value.__enter__.return_value.execute.assert_not_called()

    def test_command_exposes_scope_recovery_without_mutating_full_command(self):
        from mta.runtime.management.commands.run_production_day import Command as Full
        from mta.runtime.management.commands.run_production_upto_bpr import Command as Scoped
        full=Full().create_parser('manage.py','run_production_day')
        scoped=Scoped().create_parser('manage.py','run_production_upto_bpr')
        self.assertNotIn('--command-key',full._option_string_actions)
        self.assertIn('--command-key',scoped._option_string_actions)
        self.assertIn('--recovery-of',scoped._option_string_actions)
        self.assertIn('--repair-files',scoped._option_string_actions)
        self.assertNotIn('--retry-capture',scoped._option_string_actions)
        self.assertNotIn('--report-disposition',scoped._option_string_actions)

    def test_retry_authenticates_all_frozen_arguments_without_live_admission(self):
        from types import SimpleNamespace
        from mta.runtime.production_scope import repeated
        arguments=dict(execution_revision='same',source_digest='a'*64,initialization_id='init',
            configuration_digest='b'*64,pick_output_root='/owned',predecessor_id=None,
            predecessor_output_digest=None)
        run=SimpleNamespace(predecessor_id=None)
        frozen=dict(initialization_binding=dict(id='init',source_digest='a'*64,
            configuration_digest='b'*64),daily_input_sha256='c'*64,pick_output_root='/owned',lineage={})
        with patch('mta.runtime.production_daily.decode',return_value={'day':{'business_date':'2037-04-10'}}), \
                patch('mta.runtime.models.CalculationRun.objects') as runs, \
                patch('mta.runtime.production_scope.captured_run') as captured, \
                patch('mta.runtime.input_reader.read_input',return_value=frozen), \
                patch('mta.runtime.temporal.resolved_pick_root',side_effect=lambda value:value), \
                patch('mta.runtime.ingestion_admission.preparation_source') as live:
            runs.filter.return_value.__getitem__.return_value=[run]
            self.assertIs(repeated(b'input','c'*64,{'scope':'UptoBPR'},arguments),run)
            captured.assert_called_once_with(run,{'scope':'UptoBPR'})
            for key,value in (('initialization_id','other'),('source_digest','d'*64),
                    ('configuration_digest','d'*64),('pick_output_root','/other'),
                    ('predecessor_id','other'),('predecessor_output_digest','d'*64)):
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'frozen arguments'):
                    repeated(b'input','c'*64,{'scope':'UptoBPR'},dict(arguments,**{key:value}))
            with self.assertRaisesRegex(ValueError,'frozen arguments'):
                repeated(b'input','d'*64,{'scope':'UptoBPR'},arguments)
            live.assert_not_called()


if __name__=='__main__':unittest.main()
