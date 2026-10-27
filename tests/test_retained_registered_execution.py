"""Component-only retained execution checks; no database/native acceptance."""
import ast
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import itertools
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','retained-execution-component-only')
import django
django.setup()
from mta.runtime import retained_registered_execution_compatibility as compatible
from mta.runtime import runtime_report_request as placement,runtime_report_registered_request as registered
from mta.serialization import digest
from tests import test_runtime_report_registered_request as registered_request_tests


class RetainedFactsTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.original={'component-only':'original-release'}
        self.actual={'manifest_sha256':'e'*64,'source_commit':'f'*40}
        self.phase_recipe='2'*64
        for target,value in (('release.native_identity.require_current',self.original),
                ('mta.runtime.phase_state.recipe_digest',self.phase_recipe)):
            self.stack.enter_context(patch(target,return_value=value))
        self.stack.enter_context(patch.object(compatible,'ORIGINAL_RELEASE',self.original))
        self.stack.enter_context(patch.object(placement,'recipe_digest',return_value=compatible.PUBLICATION_RECIPE))
        self.stack.enter_context(patch.object(registered,'recipe_digest',return_value=compatible.ATTACHMENT_RECIPE))
        captured=registered_request_tests.RegisteredRequestTests().request()
        self.value=captured['scope_request'];self.outer=captured['report_registration_request']
        self.run=SimpleNamespace(pk='10000000-0000-4000-8000-000000000099',kind='DAILY_CHAIN',
            evidence_mode='production',status='RUNNING',input_digest='a'*64,
            input_payload={'schema':'component-only-input','content_digest':'a'*64})
        self.run.input_manifest_digest=digest(self.run.input_payload)
        binding=self.outer['registration']
        self.pin=dict(scope=self.value['scope'],input_digest=self.run.input_digest,
            input_manifest_digest=self.run.input_manifest_digest,scope_request_digest=digest(self.value),
            compatibility_digest=self.value['compatibility_digest'],phase_recipe=self.phase_recipe,
            outer_digest=digest(self.outer),initialization_id=binding['initialization_id'],
            source_digest=binding['source_digest'],registration_digest=binding['registration_digest'],
            phase_id='20000000-0000-4000-8000-000000000001',phase_digest='3'*64,
            database='component_only_database',original_certification_digest='4'*64,
            publications={'PostBPR':{'id':'30000000-0000-4000-8000-000000000001','digest':'5'*64}})
        self.stack.enter_context(patch.object(compatible,'RETAINED_RUNS',{str(self.run.pk):self.pin}))
        self.stack.enter_context(patch('release.native_identity.require_current',return_value=self.actual))
        self.expected=placement.request(self.value['scope'],self.value['command_key'],
            runtime_reports=self.value['runtime_reports'])

    def test_original_release_phase_request_and_input_identity_are_preserved(self):
        before=deepcopy((self.run,self.value,self.expected,self.pin))
        self.assertIs(compatible.retained_facts(self.run,self.value,self.expected),self.pin)
        body={key:value for key,value in self.value.items() if key!='compatibility_digest'}
        self.assertEqual(self.value['compatibility_digest'],digest(dict(request=body,
            release=self.original,phase_recipe=self.phase_recipe)))
        self.assertNotEqual(self.expected['compatibility_digest'],self.value['compatibility_digest'])
        self.assertEqual((self.run,self.value,self.expected,self.pin),before)
        for status in ('RUNNING','SUCCEEDED'):
            with self.subTest(status=status):
                run=deepcopy(self.run);run.status=status
                compatible.retained_facts(run,self.value,self.expected)

    def test_run_input_request_compatibility_and_phase_drift_are_rejected(self):
        changes=[('unknown run',lambda r,v,p:setattr(r,'pk','unknown')),
            ('nonproduction',lambda r,v,p:setattr(r,'evidence_mode','synthetic')),
            ('failed run',lambda r,v,p:setattr(r,'status','FAILED')),
            ('run kind',lambda r,v,p:setattr(r,'kind','CURRENT_DAY')),
            ('input',lambda r,v,p:setattr(r,'input_digest','b'*64)),
            ('manifest',lambda r,v,p:setattr(r,'input_manifest_digest','b'*64)),
            ('payload',lambda r,v,p:r.input_payload.update(extra='changed')),
            ('request',lambda r,v,p:v.update(command_key='changed')),
            ('compatibility',lambda r,v,p:v.update(compatibility_digest='b'*64)),
            ('phase pin',lambda r,v,p:p.update(phase_recipe='b'*64)),
            ('Full scope',lambda r,v,p:v.update(scope='Full'))]
        for label,change in changes:
            run,value,pin=deepcopy((self.run,self.value,self.pin));change(run,value,pin)
            with self.subTest(label=label),patch.object(compatible,'RETAINED_RUNS',{str(self.run.pk):pin}),\
                    self.assertRaises(ValueError):compatible.retained_facts(run,value,self.expected)
        with patch.object(compatible,'ORIGINAL_RELEASE',{'component-only':'wrong-origin'}),\
                self.assertRaisesRegex(ValueError,'origin or phase recipe'):
            compatible.retained_facts(self.run,self.value,self.expected)
        # Coordinating the new request hash and compatibility pin still cannot
        # replace the digest made by the original release and phase recipe.
        forged=deepcopy(self.value);forged['compatibility_digest']='b'*64
        pin=dict(self.pin,compatibility_digest='b'*64,scope_request_digest=digest(forged))
        with patch.object(compatible,'RETAINED_RUNS',{str(self.run.pk):pin}),\
                self.assertRaisesRegex(ValueError,'origin or phase recipe'):
            compatible.retained_facts(self.run,forged,self.expected)
        changed=deepcopy(self.expected);changed['report_hooks']['site_code']='foreign'
        with self.assertRaises(ValueError):compatible.retained_facts(self.run,self.value,changed)

    def test_new_capture_and_full_keep_current_release_strictness(self):
        with patch.object(compatible,'validate_retained',side_effect=AssertionError('fallback reached')):
            with self.assertRaisesRegex(ValueError,'implementation differs'):
                placement.validate_request(self.value) # no persisted owner: never adopt
            self.assertEqual(placement.validate_request(self.expected),self.expected)
            full=placement.request('Full','new-full',runtime_reports=self.value['runtime_reports'])
            self.assertEqual(placement.validate_request(full),full)
        with patch('release.native_identity.require_current',return_value=self.original):
            old_full=placement.request('Full','old-full',runtime_reports=self.value['runtime_reports'])
        # Even a known retained scoped run cannot supply execution authority to Full.
        with self.assertRaisesRegex(ValueError,'retained registered execution'):
            placement.validate_request(old_full,run=self.run)

    def native_dependencies(self):
        """Mock only persisted owners/SQL transport; execute actual validator."""
        phase=SimpleNamespace(phase='BPR',digest=self.pin['phase_digest'],attempt=SimpleNamespace(
            compatibility_digest=self.value['compatibility_digest'],input_digest=self.run.input_digest,
            input_manifest_digest=self.run.input_manifest_digest))
        raw={'scope_request':self.value,'report_registration_request':self.outer,
            'initialization_binding':{'id':self.pin['initialization_id'],'source_digest':self.pin['source_digest']}}
        publication=SimpleNamespace(pk=self.pin['publications']['PostBPR']['id'],digest='5'*64)
        certificate={'source_digest':self.pin['source_digest'],'receipt_digest':'4'*64}
        cursor=MagicMock();cursor.__enter__.return_value=cursor
        cursor.fetchone.side_effect=itertools.cycle([(self.pin['database'],),('0238_registered_read_action_cut',)])
        stack=ExitStack()
        stack.enter_context(patch.object(compatible,'process_release',return_value=self.actual))
        stack.enter_context(patch('mta.runtime.input_reader.read_input',return_value=raw))
        stack.enter_context(patch.object(registered,'read_captured',return_value=self.outer))
        stack.enter_context(patch('mta.runtime.models.RunPhaseAcceptance.objects.get',return_value=phase))
        stack.enter_context(patch('mta.runtime.scope_execution.receipt_digest',return_value=self.pin['phase_digest']))
        stack.enter_context(patch('mta.runtime.runtime_report_placement_publication.read',return_value=publication))
        stack.enter_context(patch('django.db.connection.cursor',return_value=cursor))
        stack.enter_context(patch('mta.runtime.ingestion_authority.read',return_value={'target_commit':self.actual['source_commit']}))
        stack.enter_context(patch('mta.runtime.ingestion_admission.validate_activation',return_value=certificate))
        return stack,raw,phase,publication,certificate

    def test_persisted_source_phase_registration_and_publication_cannot_be_substituted(self):
        with self.native_dependencies()[0]:
            compatible.validate_retained(self.run,self.value,self.expected)
        for change in ('source','initialization','outer','phase','phase_digest','attempt','publication','certificate'):
            stack,raw,phase,publication,certificate=self.native_dependencies()
            with stack:
                if change=='source':raw['initialization_binding']['source_digest']='c'*64
                elif change=='initialization':raw['initialization_binding']['id']='foreign'
                elif change=='outer':raw['report_registration_request']=dict(self.outer,attachment_digest='b'*64)
                elif change=='phase':phase.phase='DBM'
                elif change=='phase_digest':phase.digest='b'*64
                elif change=='attempt':phase.attempt.compatibility_digest='b'*64
                elif change=='publication':publication.pk='foreign'
                else:certificate['source_digest']='foreign'
                with self.subTest(change=change),self.assertRaises(ValueError):
                    compatible.validate_retained(self.run,self.value,self.expected)

    def test_execution_request_returns_original_facts_only_after_explicit_owner_validation(self):
        before=deepcopy(self.value)
        with self.native_dependencies()[0]:
            self.assertEqual(placement.validate_request(self.value,run=self.run),before)
            self.assertEqual(registered.validate_request(self.outer,self.value,run=self.run),self.outer)
        self.assertEqual(self.value,before)

    def test_frozen_request_and_explicit_retry_validate_the_actual_selected_owner(self):
        arguments=dict(initialization_id=self.pin['initialization_id'],source_digest=self.pin['source_digest'],
                       execution_revision='component-only-existing')
        for retry in (False,True):
            options=dict(arguments,**({'retry_capture_id':str(self.run.pk)} if retry else {}))
            with self.native_dependencies()[0],\
                    patch('mta.runtime.production_daily.decode',return_value={'day':{'business_date':'2026-10-26'}}),\
                    patch('mta.runtime.models.CalculationRun.objects.filter',return_value=[] if retry else [self.run]),\
                    patch('mta.runtime.models.CalculationRun.objects.get',return_value=self.run) as lookup,\
                    patch.object(registered,'request',side_effect=AssertionError('live factory reached')):
                result=registered.request_for_execution(b'component-only','a'*64,scope=self.value['scope'],
                    command_key=self.value['command_key'],registration_digest=self.pin['registration_digest'],
                    arguments=options)
                self.assertEqual(result,dict(scope_request=self.value,report_registration_request=self.outer))
                if retry:lookup.assert_called_once_with(pk=str(self.run.pk))
                else:lookup.assert_not_called()
        # Selection order is a component check, not authorization to retry a
        # scoped capture; native Full/scoped preflight retains that boundary.


class SourceClosureTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(compatible,'ORIGINAL_FILES',{'producer.py':'raw-producer','adapter.py':'raw-old'}))
        self.stack.enter_context(patch.object(compatible,'ADAPTED_FILES',{'adapter.py':'raw-new','bridge.py':'raw-bridge'}))
        self.stack.enter_context(patch.object(compatible,'NEW_FILES',{'bridge.py','profile.py'}))
        self.stack.enter_context(patch.object(compatible,'PROFILE_FILES',{'profile.py'}))
        self.files={'producer.py':'raw-producer','adapter.py':'raw-new','bridge.py':'raw-bridge','profile.py':'self-pinned-by-native-manifest'}
        compatible._recipe_sources.cache_clear();compatible.process_release.cache_clear()
        self.addCleanup(compatible._recipe_sources.cache_clear);self.addCleanup(compatible.process_release.cache_clear)

    def test_raw_source_closure_refuses_addition_deletion_and_changed_producer_or_adapter(self):
        compatible.check_source_manifest(self.files)
        for name in self.files:
            changed=dict(self.files);del changed[name]
            with self.subTest(deleted=name),self.assertRaisesRegex(ValueError,'closure'):
                compatible.check_source_manifest(changed)
        changed=dict(self.files,undeclared='hash')
        with self.assertRaises(ValueError):compatible.check_source_manifest(changed)
        for name in ('producer.py','adapter.py','bridge.py'):
            changed=dict(self.files);changed[name]='changed'
            with self.subTest(changed=name),self.assertRaises(ValueError):compatible.check_source_manifest(changed)
        with patch.object(compatible,'ADAPTED_FILES',{'adapter.py':'raw-new'}),self.assertRaises(ValueError):
            compatible.check_source_manifest(self.files)

    def test_recipe_adapters_require_exact_text_fingerprints_and_observed_recipe(self):
        sha=lambda value:hashlib.sha256(value.encode()).hexdigest()
        original={'producer.py':sha('original\r\n'),'adapter.py':sha('old\r\n')}
        text={'producer.py':sha('original\n')}
        adapted={'adapter.py':sha('new\n'),'bridge.py':sha('bridge\n')}
        sources={'producer.py':'original\n','adapter.py':'new\n','bridge.py':'bridge\n'}
        def read(path,**kwargs):return sources[path.name]
        with patch.object(compatible,'ORIGINAL_FILES',original),\
                patch.object(compatible,'ORIGINAL_PYTHON_TEXT_OVERRIDES',text),\
                patch.object(compatible,'ADAPTED_PYTHON_TEXT',adapted),\
                patch.object(compatible,'OBSERVED_PUBLICATION_RECIPE','observed-publication'),\
                patch.object(compatible,'OBSERVED_ATTACHMENT_RECIPE','observed-attachment'),\
                patch.object(Path,'read_text',read):
            self.assertEqual(compatible.publication_recipe('observed-publication'),compatible.PUBLICATION_RECIPE)
            self.assertEqual(compatible.attachment_recipe('observed-attachment'),compatible.ATTACHMENT_RECIPE)
            with self.assertRaises(ValueError):compatible.publication_recipe('changed')
            with self.assertRaises(ValueError):compatible.attachment_recipe('changed')
            for name in sources:
                compatible._recipe_sources.cache_clear();old=sources[name];sources[name]='changed\n'
                with self.subTest(source=name),self.assertRaisesRegex(ValueError,'source differs'):
                    compatible.publication_recipe('observed-publication')
                sources[name]=old
            compatible._recipe_sources.cache_clear()
            with patch.object(compatible,'ADAPTED_PYTHON_TEXT',{}),self.assertRaisesRegex(ValueError,'roster'):
                compatible.attachment_recipe('observed-attachment')

    def test_actual_process_release_is_not_relabelled_as_original(self):
        actual={'component-only':'actual-current-release'}
        with patch('release.native_identity.require_current',return_value=actual),\
                patch.object(Path,'read_bytes',return_value=json.dumps({'files':self.files}).encode()),\
                patch.object(compatible,'_recipe_sources') as text_check:
            self.assertIs(compatible.process_release(),actual)
            text_check.assert_called_once()


class TerminalReaderTransitionTests(unittest.TestCase):
    def test_code_only_transition_requires_exact_predecessor_owner_and_actual_target(self):
        target = {'manifest_sha256': 'actual-target', 'source_commit': 'actual-commit'}
        previous = dict(source_commit=compatible.READ_ROUTING_PREVIOUS_COMMIT,
                        manifest_sha256=compatible.READ_ROUTING_PREVIOUS_RELEASE)
        with patch.object(compatible, 'RETAINED_RUNS', {'run': {'initialization_id': 'owned'}}), \
                patch.object(compatible, 'process_release', return_value=target) as release:
            self.assertTrue(compatible.transition_profile('owned', previous, target))
            original = dict(source_commit=compatible.PREVIOUS_COMMIT,
                            manifest_sha256=compatible.PREVIOUS_RELEASE)
            self.assertTrue(compatible.transition_profile('owned', original, target))
            for field in previous:
                release.reset_mock()
                self.assertFalse(compatible.transition_profile('owned', dict(previous, **{field: 'other'}), target))
                release.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'owned initialization'):
                compatible.transition_profile('foreign', previous, target)
            with self.assertRaisesRegex(ValueError, 'release differs'):
                compatible.transition_profile('owned', previous, dict(target, source_commit='other'))


class EntryForwardingTests(unittest.TestCase):
    def test_deep_mutation_validators_receive_the_persisted_run(self):
        # Static routing proof only: these deep functions require native SQL and
        # transaction ownership for their behavioral acceptance checks.
        root=Path(__file__).resolve().parents[1]
        cases=[('scope_execution.py','_claim','validate_request','run'),
            ('runtime_report_execution.py','publish_phase','contract.validate_request','attempt.run'),
            ('placement_master_publication.py','_owner','validate_request','run'),
            ('production_scope.py','fence','validate_request','attempt.run'),
            ('production_report_placement.py','fence','contract.validate_request','attempt.run'),
            ('runtime_report_registered_request.py','request_for_execution','validate_request','owner')]
        for file,function,callee,argument in cases:
            tree=ast.parse((root/'mta/runtime'/file).read_text())
            owner=next(node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==function)
            calls=[node for node in ast.walk(owner) if isinstance(node,ast.Call) and ast.unparse(node.func)==callee]
            with self.subTest(file=file,function=function):
                self.assertTrue(calls)
                self.assertTrue(all(any(keyword.arg=='run' and ast.unparse(keyword.value)==argument
                    for keyword in call.keywords) for call in calls))


if __name__=='__main__':unittest.main()
