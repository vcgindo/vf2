"""Production metadata decoding is separate from captured execution authority."""
from copy import deepcopy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','test-only-not-a-serving-credential')
import django
django.setup()
from django.db.backends.base.base import BaseDatabaseWrapper
from mta.runtime import runtime_report_request as request
from mta.runtime import runtime_report_registered_request as registered
from mta.runtime import report_definition_registration as registration
from mta.serialization import digest
from tests.test_production_scope_policy import reference


class ProductionRequestPatchTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(BaseDatabaseWrapper,'connect',side_effect=AssertionError('No DB in metadata unit proof')))
        self.enterContext(patch('release.native_identity.require_current',return_value={'authenticated-reader':'one'}))

    def value(self):
        return request.request('UptoBPR','one-owned-command',runtime_reports=reference())

    def attachment(self,inner):
        stored=registration.encode(inner['runtime_reports'],
            initialization_id='10000000-0000-4000-8000-000000000001',source_digest='b'*64,
            certificate_id='10000000-0000-4000-8000-000000000002',certificate_digest='c'*64)
        return registered._attachment(inner,stored),stored

    def test_fresh_production_factory_never_enters_whole_native_alias(self):
        with patch('mta.runtime.retained_registered_execution_compatibility._recipe_sources',
                   side_effect=AssertionError('Unrelated code is not a metadata producer dependency')):
            value=self.value()
            self.assertEqual(request.validate_request(value),value)
            outer,_=self.attachment(value)
            self.assertEqual(registered.validate_request(outer,value),outer)

    def test_real_producer_dependency_changes_truthful_new_recipe(self):
        before=request.recipe_digest(production=True)
        with patch('mta.application.runtime_report_btr_stage.recipe_digest',return_value='a'*64):
            self.assertNotEqual(request.recipe_digest(production=True),before)
        value=self.value();old=deepcopy(value)
        value['publication_recipe']='f'*64
        self.assertEqual(request.validate_read_request(value),value)
        with self.assertRaises(ValueError):request.validate_request(value)
        with patch('release.native_identity.require_current',return_value={'authenticated-reader':'two'}):
            self.assertEqual(request.validate_read_request(old),old)
            with self.assertRaises(ValueError):request.validate_request(old)

    def test_supported_read_keeps_original_provenance_and_requires_every_format_field(self):
        value=self.value();value['publication_recipe']='1'*64
        outer,_=self.attachment(value);outer['attachment_recipe']='2'*64
        outer['attachment_digest']=digest({k:v for k,v in outer.items() if k!='attachment_digest'})
        before=deepcopy((value,outer))
        with patch.object(request,'recipe_digest',side_effect=AssertionError('Reader must not produce a current recipe')):
            self.assertEqual(registered.validate_read_request(outer,value),outer)
        self.assertEqual((value,outer),before)
        with self.assertRaises(ValueError):registered.validate_request(outer,value)
        for key,bad in (('schema','unknown-v99'),('scope','PostBPR'),('command_key',''),
                        ('publication_recipe','bad'),('compatibility_digest','bad'),
                        ('report_hooks',{}),('dispositions',{})):
            with self.subTest(key=key),self.assertRaises(ValueError):
                request.validate_read_request(dict(value,**{key:bad}))
        with self.assertRaises(ValueError):request.validate_read_request(dict(value,extra=True))
        for key in ('attachment_recipe','attachment_digest','scope_request_digest'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                registered.validate_read_request(dict(outer,**{key:'bad'}),value)
        for bad in (dict(outer,extra=True),dict(outer,schema='unknown-v99'),
                    dict(outer,attachment_recipe='3'*64)):
            with self.assertRaises(ValueError):registered.validate_read_request(bad,value)

    def test_captured_reader_still_requires_actual_immutable_registration_custody(self):
        from mta.runtime.report_definition_models import ReportDefinitionRegistration
        inner=self.value();outer,stored=self.attachment(inner)
        outer['attachment_recipe']='2'*64
        outer['attachment_digest']=digest({k:v for k,v in outer.items() if k!='attachment_digest'})
        raw=dict(scope_request=inner,report_registration_request=outer,
                 initialization_binding=dict(id=stored['header']['initialization_id'],
                    source_digest=stored['header']['source_digest']))
        with patch('mta.runtime.input_reader.read_input',return_value=raw), \
                patch.object(ReportDefinitionRegistration.objects,'get',return_value='owned-row') as get, \
                patch.object(registration,'_stored',return_value=stored) as read:
            self.assertEqual(registered.read_captured('original-run'),outer)
            get.assert_called_once_with(pk=outer['registration']['registration_digest'],
                initialization_id=outer['registration']['initialization_id'],
                source_digest=outer['registration']['source_digest'],
                certificate_id=outer['registration']['certificate_id'],
                certificate_digest=outer['registration']['certificate_digest'])
            read.assert_called_once_with('owned-row')
            get.side_effect=ReportDefinitionRegistration.DoesNotExist('No matching immutable custody')
            with self.assertRaises(ReportDefinitionRegistration.DoesNotExist):registered.read_captured('original-run')
        changed=deepcopy(raw);changed['initialization_binding']['source_digest']='f'*64
        with patch('mta.runtime.input_reader.read_input',return_value=changed):
            with self.assertRaisesRegex(ValueError,'installation differs'):registered.read_captured('original-run')


class RoutineUpgradeBoundaryTests(unittest.TestCase):
    def test_unfinished_owned_business_work_is_denied_without_mutation(self):
        from release.upgrade_database import require_finished_work
        owner=SimpleNamespace(source_id='owned-source',pk='owned-initialization')
        cursor=Mock();cursor.fetchone.return_value=(False,)
        require_finished_work(cursor,owner)
        self.assertEqual(cursor.execute.call_args.args[1],['owned-source','owned-initialization','owned-initialization'])
        for value in ((True,),None,('false',)):
            cursor.fetchone.return_value=value
            with self.assertRaisesRegex(ValueError,'unfinished daily/scoped'):require_finished_work(cursor,owner)
