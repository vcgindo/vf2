"""Admission fixtures only: no execute_day, engine, consumer or restore campaign.

Native producer proofs remain Cohorts1–4. These fixtures prove orchestration,
denial, atomic persistence and database gates, not a newly calculated business day.
"""
from copy import deepcopy
from datetime import date
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import uuid

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction, DatabaseError
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from mta.serialization import digest
from mta.presentation import operational_admission as op, daily_activation, daily_publication
from mta.presentation.context import PublicationUnavailable
from mta.runtime.models import (CalculationRun, DailyUiPublication, DailyUiActivation,
    OperationalAcceptance, OperationalAttempt, OperationalOperation)
from mta.runtime.operational_attempts import register_configuration
from mta.runtime.operational_runner import ROSTER, RUNNER_POLICY


POLICY_SETTINGS = dict(VF_MTA_OPERATIONAL_POLICY=op.POLICY, VF_MTA_OPERATIONAL_RECEIPT='',
    VF_MTA_CONSUMPTION_POLICY='', VF_MTA_DAILY_PUBLICATION=True,
    VF_MTA_SYNTHETIC_ROSTER='core-without-bor-v1', VF_MTA_PUBLISHED_RUN='',
    VF_MTA_PUBLISHED_DIGEST='', VF_BTR_REPORTING_GENERATION='', VF_MTA_ACTIONS_ENABLED=False,
    VF_MTA_PERMISSIONS_SHA256='', VF_MTA_HIERARCHY_SHA256='')


@override_settings(**POLICY_SETTINGS)
class OperationalAcceptancePersistence(TestCase):
    def setUp(self):
        no_engine = patch('mta.runtime.temporal.execute_day', side_effect=AssertionError('No calculation authorized'))
        no_engine.start(); self.addCleanup(no_engine.stop)
        self.run = CalculationRun.objects.create(kind='DAILY_CHAIN', status='SUCCEEDED',
            business_date=date(2026,6,6), input_digest=digest('input'), input_manifest_digest=digest('manifest'),
            output_digest=digest('output'), production_digest=digest('production'),
            execution_revision=self._testMethodName, parity_summary={},
            input_payload={'schema':'fresh-daily-input-manifest-v2'}, production_manifest={'version':2})
        self.config = register_configuration(source_digest=digest('source'), bindings={
            'runner_policy':RUNNER_POLICY, 'operation_roster':ROSTER,
            'zip_tool':{'path':'/fixture/zip','sha256':digest('zip')}}, settings=[], tables=[], alerts=[])
        self.attempt = OperationalAttempt.objects.create(run=self.run, configuration=self.config,
            request_key=uuid.uuid4().hex, root='/fixture/'+uuid.uuid4().hex, business_date=self.run.business_date,
            run_output_digest=self.run.output_digest, action_digest=digest([]), source_digest=digest('source'),
            clock=timezone.now(), status='SUCCEEDED')
        for item in ROSTER:
            OperationalOperation.objects.create(attempt=self.attempt, status='SUCCEEDED', **item)
        from mta.presentation.daily_preparation import required_layers
        self.generation = str(uuid.uuid4())
        layers = {name:{'status':'READY','receipt':{'generation':self.generation} if name=='btr' else {}}
                  for name in required_layers()}
        self.pub = DailyUiPublication(run=self.run, status='READY', output_digest=self.run.output_digest,
            source_digest=digest('source'), recipe_digest=daily_publication.recipe_identity(),
            configuration_digest=daily_publication.configuration_identity(), layers=layers, sealed_at=timezone.now())
        self.pub.seal_digest=daily_publication.seal_identity(self.pub); self.pub.save()
        self.original = DailyUiPublication.objects.filter(run=self.run).values().get()
        access = override_settings(VF_MTA_PERMISSIONS_SHA256=daily_activation.CATALOGUE,
                                  VF_MTA_HIERARCHY_SHA256=digest('hierarchy'))
        access.enable(); self.addCleanup(access.disable)
        allowed = patch('mta.presentation.daily_activation.access_manifest',return_value={'fixture':True})
        allowed.start(); self.addCleanup(allowed.stop)
        self.state = dict(code=digest('code'), artifact=digest('artifact'), actions=digest([]),
            sources=digest('sources'), operations=digest('operations'),
            access=daily_activation.values(self.run,self.pub), generation=self.generation)
        # Only the expensive native validators are substituted for transaction fixtures.
        # Separate tests below exercise their required orchestration and failures.
        self.candidate=patch.object(op,'verify_candidate',return_value=(self.state,digest('profile'))).start()
        self.addCleanup(patch.stopall)
        patch.object(op,'snapshot',side_effect=lambda *a:self.state).start()

    def issue(self, **changes):
        args=dict(output_digest=self.run.output_digest, attempt_id=self.attempt.pk,
                  artifact_path='/fixture/artifact', finalization_path='/fixture/finalization')
        args.update(changes)
        return op.issue(self.run.pk,**args)

    def test_atomic_receipt_activation_and_exact_retry(self):
        row=self.issue()
        self.assertEqual(self.issue().receipt_digest,row.receipt_digest)
        self.assertEqual(self.candidate.call_count,2)
        self.assertEqual(OperationalAcceptance.objects.count(),1)
        self.assertEqual(DailyUiActivation.objects.get().activation_digest,row.activation_digest)
        self.assertEqual(DailyUiPublication.objects.filter(run=self.run).values().get(),self.original)
        self.run.refresh_from_db(); self.assertEqual(self.run.parity_summary,{})
        with connection.cursor() as cursor: cursor.execute('SET CONSTRAINTS operational_acceptance_pair IMMEDIATE')

    def test_activation_failure_rolls_back_receipt(self):
        with patch.object(DailyUiActivation.objects,'create',side_effect=ValueError('injected activation')):
            with self.assertRaisesRegex(ValueError,'injected activation'): self.issue()
        self.assertFalse(OperationalAcceptance.objects.exists())
        self.assertFalse(DailyUiActivation.objects.exists())

    def test_failed_verification_never_creates_either_owner(self):
        self.candidate.side_effect=ValueError('native file mismatch')
        with self.assertRaisesRegex(ValueError,'native file mismatch'): self.issue()
        self.assertFalse(OperationalAcceptance.objects.exists())
        self.assertFalse(DailyUiActivation.objects.exists())

    def test_database_denies_partial_operation_even_with_candidate_claim(self):
        OperationalOperation.objects.filter(attempt=self.attempt,group='O8').update(status='DISABLED')
        with self.assertRaises(DatabaseError),transaction.atomic(): self.issue()
        self.assertFalse(OperationalAcceptance.objects.exists())

    def test_database_denies_wrong_attempt_owner(self):
        OperationalAttempt.objects.filter(pk=self.attempt.pk).update(run_output_digest=digest('different'))
        with self.assertRaises(DatabaseError),transaction.atomic(): self.issue()

    def test_database_denies_caller_flag_without_receipt(self):
        with self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.daily_activation',%s,true)",[str(self.run.pk)])
            cursor.execute("SELECT set_config('fresh.operational_daily_activation',%s,true)",[digest('fake')])
            DailyUiActivation.objects.create(publication=self.pub,**self.state['access'])

    def test_nonmember_database_session_cannot_assume_offline_issuer(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SET SESSION AUTHORIZATION pg_read_all_data')
            with self.assertRaises(DatabaseError),transaction.atomic(): self.issue()
        finally:
            with connection.cursor() as cursor: cursor.execute('RESET SESSION AUTHORIZATION')
        self.assertFalse(OperationalAcceptance.objects.exists())

    def test_receipt_is_append_only(self):
        self.issue()
        with connection.cursor() as cursor: cursor.execute('SET LOCAL ROLE NONE')
        for action in (lambda:OperationalAcceptance.objects.update(code_digest=digest('changed')),
                       lambda:OperationalAcceptance.objects.all().delete()):
            with self.assertRaises(DatabaseError),transaction.atomic(): action()
        with self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as cursor:
            cursor.execute('TRUNCATE mta.fresh_mta_operationalacceptance')

    def test_changed_retry_preserves_original(self):
        row=self.issue(); self.state={**self.state,'sources':digest('changed')}
        self.candidate.return_value=(self.state,digest('profile'))
        with self.assertRaisesRegex(PublicationUnavailable,'retry_tuple_changed'): self.issue()
        self.assertEqual(OperationalAcceptance.objects.get().receipt_digest,row.receipt_digest)

    def test_native_operation_metadata_handles_uuids_and_detects_drift(self):
        before=op.operation_metadata(self.attempt,None)
        OperationalOperation.objects.filter(attempt=self.attempt,group='O8').update(reason='changed')
        self.assertNotEqual(before,op.operation_metadata(self.attempt,None))

    def test_successful_repair_cannot_be_omitted(self):
        repair=OperationalAttempt.objects.create(run=self.run,configuration=self.config,
            repair_of=self.attempt,request_key=uuid.uuid4().hex,root='/fixture/'+uuid.uuid4().hex,
            business_date=self.run.business_date,run_output_digest=self.run.output_digest,
            action_digest=self.attempt.action_digest,source_digest=self.attempt.source_digest,
            clock=timezone.now(),status='SUCCEEDED')
        with self.assertRaisesRegex(PublicationUnavailable,'repair_lineage'):op.operation_metadata(self.attempt,None)
        self.assertEqual(len(op.operation_metadata(self.attempt,repair)),64)
        OperationalAttempt.objects.create(run=self.run,configuration=self.config,repair_of=self.attempt,
            request_key=uuid.uuid4().hex,root='/fixture/'+uuid.uuid4().hex,
            business_date=self.run.business_date,run_output_digest=self.run.output_digest,
            action_digest=self.attempt.action_digest,source_digest=self.attempt.source_digest,
            clock=timezone.now(),status='FAILED')
        with self.assertRaisesRegex(PublicationUnavailable,'detached_repair'):op.operation_metadata(self.attempt,repair)

    def test_successor_database_binds_exact_predecessor_receipt_and_output(self):
        parent=self.issue();parent_run=self.run;parent_attempt=self.attempt
        with connection.cursor() as cursor:cursor.execute('SET LOCAL ROLE NONE')
        self.run=CalculationRun.objects.create(kind='DAILY_CHAIN',status='SUCCEEDED',
            predecessor=parent_run,business_date=date(2026,6,7),input_digest=digest('child input'),
            input_manifest_digest=digest('child manifest'),output_digest=digest('child output'),
            production_digest=digest('child production'),execution_revision='child-'+self._testMethodName[:60],
            input_payload={'schema':'fresh-daily-input-manifest-v2'},production_manifest={'version':2},parity_summary={})
        self.attempt=OperationalAttempt.objects.create(run=self.run,configuration=self.config,
            predecessor=parent_attempt,request_key=uuid.uuid4().hex,root='/fixture/'+uuid.uuid4().hex,
            business_date=self.run.business_date,run_output_digest=self.run.output_digest,
            action_digest=digest([]),source_digest=digest('child source'),clock=timezone.now(),status='SUCCEEDED')
        for item in ROSTER:OperationalOperation.objects.create(attempt=self.attempt,status='SUCCEEDED',**item)
        self.pub=DailyUiPublication(run=self.run,status='READY',output_digest=self.run.output_digest,
            source_digest=digest('child source'),recipe_digest=daily_publication.recipe_identity(),
            configuration_digest=daily_publication.configuration_identity(access=daily_activation.EMPTY_ACCESS),
            layers=deepcopy(self.pub.layers),sealed_at=timezone.now())
        self.pub.seal_digest=daily_publication.seal_identity(self.pub);self.pub.save()
        self.state={**self.state,'access':daily_activation.values(self.run,self.pub),
                    'predecessor_receipt':digest('wrong'), 'predecessor_output':parent_run.output_digest}
        self.candidate.return_value=(self.state,digest('profile'))
        with patch.object(op,'verify',return_value=parent):
            with self.assertRaises(DatabaseError),transaction.atomic():self.issue()
            self.assertFalse(OperationalAcceptance.objects.filter(run=self.run).exists())
            self.state['predecessor_receipt']=parent.receipt_digest
            child=self.issue()
        self.assertEqual(child.predecessor_id,parent.pk)
        self.assertEqual(child.predecessor_output_digest,parent_run.output_digest)

    def test_database_deferred_pair_rejects_receipt_without_activation(self):
        values=op.receipt_values(self.run,self.attempt,None,'/fixture/artifact',
                                '/fixture/finalization',self.state,digest('profile'))
        with self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as cursor:
            cursor.execute('SET LOCAL ROLE fresh_operational_acceptor')
            cursor.execute("SELECT set_config('fresh.operational_acceptance',%s,true)",[str(self.run.pk)])
            OperationalAcceptance.objects.create(run=self.run,attempt=self.attempt,**values)
            cursor.execute('SET CONSTRAINTS operational_acceptance_pair IMMEDIATE')
        self.assertFalse(OperationalAcceptance.objects.exists())

    def test_selected_receipt_generation_and_identity_drift_deny(self):
        row=self.issue()
        with override_settings(VF_MTA_OPERATIONAL_RECEIPT=row.receipt_digest,VF_BTR_REPORTING_GENERATION=self.generation):
            self.assertEqual(op.identity(self.run).pk,row.pk)
            with override_settings(VF_BTR_REPORTING_GENERATION=str(uuid.uuid4())):
                with self.assertRaisesRegex(PublicationUnavailable,'selected_receipt_or_generation'): op.identity(self.run)
            self.state={**self.state,'code':digest('new code')}
            with self.assertRaisesRegex(PublicationUnavailable,'receipt_identity_changed'): op.identity(self.run)

    def test_strict_cli_still_rejects_operational_receipt(self):
        self.issue()
        with override_settings(VF_MTA_OPERATIONAL_POLICY=''):
            with self.assertRaisesRegex(CommandError,'independently accepted'):
                call_command('check_daily_selection',run_id=str(self.run.pk),output_digest=self.run.output_digest)

    def test_explicit_selection_cli_emits_one_tuple_without_mutation(self):
        row=self.issue(); out=StringIO()
        with patch.object(op,'verify',return_value=row),patch('mta.presentation.daily_publication.require_ready',return_value=self.pub):
            call_command('check_daily_selection',run_id=str(self.run.pk),output_digest=self.run.output_digest,stdout=out)
        import json
        result=json.loads(out.getvalue())
        self.assertEqual(result['VF_MTA_OPERATIONAL_RECEIPT'],row.receipt_digest)
        self.assertEqual(result['VF_BTR_REPORTING_GENERATION'],self.generation)
        from django.conf import settings
        self.assertEqual(settings.VF_MTA_PUBLISHED_RUN,'')

    def test_failed_candidate_preserves_prior_selection_and_emits_nothing(self):
        out=StringIO();prior=str(uuid.uuid4())
        with override_settings(VF_MTA_PUBLISHED_RUN=prior,VF_MTA_PUBLISHED_DIGEST=digest('prior')):
            with patch.object(op,'verify',side_effect=PublicationUnavailable('candidate_denied')):
                with self.assertRaises(PublicationUnavailable):
                    call_command('check_daily_selection',run_id=str(self.run.pk),output_digest=self.run.output_digest,stdout=out)
            from django.conf import settings
            self.assertEqual(settings.VF_MTA_PUBLISHED_RUN,prior)
            self.assertEqual(settings.VF_MTA_PUBLISHED_DIGEST,digest('prior'))
        self.assertEqual(out.getvalue(),'')

    def test_startup_reverification_and_request_identity_denial(self):
        from mta.presentation import admission
        row=self.issue()
        with override_settings(VF_MTA_OPERATIONAL_RECEIPT=row.receipt_digest,VF_BTR_REPORTING_GENERATION=self.generation),\
                patch.object(admission,'binding',return_value=(self.run,'verified')) as binding,\
                patch('mta.presentation.btr_reporting.selected_generation'),\
                patch('mta.presentation.btr_reporting.verify_generation'):
            admission.admit()
            self.assertEqual(admission.require_admission(),'verified')
            self.assertGreaterEqual(self.candidate.call_count,2)
            binding.return_value=(self.run,'changed')
            with self.assertRaises(PublicationUnavailable):admission.require_admission()
            self.assertIsNone(admission._admitted)


@override_settings(**POLICY_SETTINGS)
class OperationalVerifierProtocol(SimpleTestCase):
    def test_native_frozen_input_comparator_accepts_supplement_and_denies_drift(self):
        import json,hashlib,tempfile
        from pathlib import Path
        from contextlib import ExitStack
        from mta.application import daily_finalization as final
        from mta.application.operational_capture import CAPTURE_POLICY
        from mta.mdm.daily_source import ARTIFACT_SHA
        opening_complete={name:[] for name in final.REQUIRED}
        opening_complete['ScriptExecutedFlag']=deepcopy(final.FLAG_SEED)
        settings=[{'Parameter':k,'Value':v} for k,v in (('NMSActive','0'),('IsBatchFileExecuted','0'),('IsBPRBatchFileExecuted','1'),('BatchFileExecutionDate','2026-06-05'))]
        case=dict(case='admission-fixture',profile={'force_flags':{'nms_active':False}},
                  opening={'importer_settings':settings},opening_date='2026-06-05',
                  days=[{'business_date':'2026-06-06','raw_master':[],'new_force_requests':[]}],static_day={})
        artifact={'schema':'block3-sizeable-input-v1','case':case}
        supplement={'schema':'generic-finalization-input-v1','artifact_sha256':ARTIFACT_SHA,
            'configuration':{'policy':final.POLICY,'consumption_days':90,'remark_days':90},
            'opening_complete':opening_complete}
        content=json.dumps(supplement).encode()
        profile=dict(force_flags={'nms_active':False},complete_daily=supplement['configuration'],
            complete_daily_config_sha256=hashlib.sha256(content).hexdigest(),
            complete_daily_artifact_sha256=ARTIFACT_SHA,operational_sources=CAPTURE_POLICY,
            daily_publication=True,daily_publication_config={'bpr_remark_horizon':90})
        opening=dict(state={**case['opening'],'complete':opening_complete},opening_date=case['opening_date'],
                     identity=case['case']+'-'+ARTIFACT_SHA+'-daily')
        mdm=dict(revision_digest=digest('mdm'),nms_active=False,pair_exclusions=[])
        raw=dict(schema='fresh-daily-chain-v1',profile=profile,opening=opening,
            day={'business_date':'2026-06-06','raw_master':[],'exclusions':[],'new_force_requests':[]},
            lineage={'opening_identity':opening['identity'],'opening_digest':digest(opening)},
            mdm_input=mdm,report_exceptions={},finalization_binding={
                'sha256':profile['complete_daily_config_sha256'],'artifact_sha256':ARTIFACT_SHA,
                'opening_digest':digest(opening_complete)})
        closing=deepcopy(opening['state'])
        closing['controls']={'upload_log':[]}
        for flag in closing['complete']['ScriptExecutedFlag']:
            flag['IsScriptExecuted']=flag['ScriptName'] not in ('NMSImportData.sql','NMSClearInputTables.sql')
        closing['importer_settings']=[{'Parameter':k,'Value':v} for k,v in (
            ('NMSActive','0'),('IsBatchFileExecuted','0'),('IsBPRBatchFileExecuted','1'),('BatchFileExecutionDate','2026-06-06'))]
        output={'ClosingState':[closing],'DBMFinal':[{}],'Lineage':[{'cohort1':{
            'policy':final.POLICY,'business_date':'2026-06-06','configuration_digest':digest(profile),
            'qualification':op.QUALIFICATION,'flag_digest':digest(closing['complete']['ScriptExecutedFlag'])}}]}
        run=SimpleNamespace(input_digest=digest(raw),business_date=date(2026,6,6),predecessor_id=None,
            mdm_input_capture=SimpleNamespace(source=object(),revision_digest=mdm['revision_digest']),
            execution_revision='explicit-fixture',opening_key=digest({'identity':opening['identity'],'revision':'explicit-fixture'}))
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            ap=Path(directory)/'artifact.json';ap.write_text(json.dumps(artifact))
            fp=Path(directory)/'finalization.json';fp.write_bytes(content)
            stack.enter_context(patch('mta.mdm.daily_source_install.registered',return_value=artifact))
            binding=stack.enter_context(patch('mta.mdm.daily_source.require_binding'))
            stack.enter_context(patch('mta.presentation.operational_mdm.verify_consumed'))
            stack.enter_context(patch('mta.mdm.daily_input.compose',return_value=[]))
            stack.enter_context(patch('mta.runtime.temporal.command_state',return_value=({},[])))
            stack.enter_context(patch.object(op,'actions',return_value=[]))
            self.assertEqual(op.verify_input_domain(run,raw,output,ap,fp),digest(profile))
            self.assertEqual(binding.call_args.kwargs['artifact_sha256'],ARTIFACT_SHA)
            for change in ('profile','day','opening','lineage','source_omission','remark_horizon','upload_source'):
                bad=deepcopy(raw)
                if change=='remark_horizon':bad['profile']['daily_publication_config']['bpr_remark_horizon']=89
                if change=='upload_source':bad['day']['new_force_requests']=[{}]
                if change=='profile':bad['profile']['unexpected']=True
                if change=='day':bad['day']['unexpected']=[]
                if change=='opening':bad['opening']['identity']='foreign'
                if change=='lineage':bad['lineage']['opening_digest']=digest('wrong')
                if change=='source_omission':bad.pop('finalization_binding')
                run.input_digest=digest(bad)
                with self.subTest(change=change),self.assertRaises((ValueError,PublicationUnavailable)):
                    op.verify_input_domain(run,bad,output,ap,fp)

    def test_explicit_operational_opening_roster_and_binding(self):
        from mta.runtime.operational_opening import OPENING_TABLES, OPENING_POLICY, ACTION_TYPES
        from mta.runtime.operational_alert_sources import ABORT_OPENING_POLICY
        rows={name:[] for name in OPENING_TABLES}
        rows['UIUploadLogActionType']=ACTION_TYPES
        bindings=dict(opening_policy=OPENING_POLICY,opening_input_digest=digest('input'),
            opening_digest=digest(rows),abort_opening_policy=ABORT_OPENING_POLICY,abort_opening_digest=digest([]))
        owner=SimpleNamespace(predecessor_id=None,configuration=object(),run=SimpleNamespace(input_digest=digest('input')))
        def read(owner,image):
            return [] if image=='opening/RunAbortReasons' else rows[image.removeprefix('opening/')]
        with patch('mta.runtime.operational_attempts.configuration_value',return_value={'bindings':bindings}), \
                patch('mta.runtime.operational_native.read_population',side_effect=read) as reader:
            op.verify_operational_opening(owner)
            self.assertEqual(reader.call_count,len(OPENING_TABLES)+1)
            bindings['opening_input_digest']=digest('wrong')
            with self.assertRaises(PublicationUnavailable):op.verify_operational_opening(owner)
            bindings['opening_input_digest']=digest('input')
            del rows['RRR_OrderAllocation']
            with self.assertRaises(KeyError):op.verify_operational_opening(owner)

    def test_policy_conflicts_and_unknown_values_deny(self):
        self.assertTrue(op.enabled())
        for field,value in [('VF_MTA_CONSUMPTION_POLICY','cohort2-qualified-consumption-v1'),
                ('VF_MTA_ACTIONS_ENABLED',True),('VF_MTA_FIXTURE_FILE','fixture'),
                ('VF_MTA_TERMINAL_FILE','supplement'),('VF_MTA_SYNTHETIC_ROSTER',''),
                ('VF_MTA_OPERATIONAL_POLICY','unknown')]:
            with self.subTest(field=field),override_settings(**{field:value}):
                with self.assertRaises(PublicationUnavailable): op.enabled()
        with override_settings(VF_MTA_OPERATIONAL_POLICY='',VF_MTA_OPERATIONAL_RECEIPT='stale'):
            with self.assertRaises(PublicationUnavailable): op.enabled()

    def test_native_completion_zero_qualification_is_narrow(self):
        from mta.application import daily_finalization as final
        complete={'ScriptExecutedFlag':deepcopy(final.FLAG_SEED)}
        for flag in complete['ScriptExecutedFlag']:
            flag['IsScriptExecuted']=flag['ScriptName'] not in ('NMSImportData.sql','NMSClearInputTables.sql')
        settings=[{'Parameter':k,'Value':v} for k,v in [('NMSActive','0'),('IsBatchFileExecuted','0'),
            ('IsBPRBatchFileExecuted','1'),('BatchFileExecutionDate','2026-06-06')]]
        self.assertEqual(final.finish(deepcopy(complete),settings,'2026-06-06'),settings)
        for key,value in [('NMSActive','1'),('IsBPRBatchFileExecuted','0'),('BatchFileExecutionDate','2026-06-05')]:
            bad=deepcopy(settings)
            next(r for r in bad if r['Parameter']==key)['Value']=value
            with self.subTest(key=key),self.assertRaises(ValueError): final.finish(deepcopy(complete),bad,'2026-06-06')
        next(r for r in complete['ScriptExecutedFlag'] if r['IsScriptCritical']==1 and r['IsScriptExecuted'])['IsScriptExecuted']=0
        with self.assertRaises(ValueError): final.finish(complete,settings,'2026-06-06')

    def test_candidate_calls_all_existing_validators_and_propagates_each_failure(self):
        from contextlib import ExitStack
        from mta.presentation.daily_preparation import required_layers
        from mta.presentation.daily_requests import PATH
        remark='sources/bpr/BPRReport_RemarkDetails'
        paths=['mta.presentation.operational_admission.snapshot',
            'mta.presentation.operational_admission.verify_input_domain',
            'mta.runtime.services.read_outputs','mta.runtime.validation_storage.read_input',
            'mta.runtime.operational_runner.validate_configuration',
            'mta.runtime.operational_attempts.verify_attempt',
            'mta.presentation.daily_sources.receipt','mta.presentation.daily_requests.metadata',
            'mta.presentation.ancillary_live.image_metadata','mta.presentation.ancillary_live.image_rows',
            'mta.presentation.daily_activation.access_manifest',
            'mta.presentation.daily_preparation.verify_layer','mta.presentation.admission.verify_native',
            'mta.presentation.operational_admission.verify_operational_opening']
        publication=SimpleNamespace(layers={k:{'receipt':{}} for k in required_layers()})
        attempt=SimpleNamespace(configuration=object())
        with ExitStack() as stack:
            mocks={p:stack.enter_context(patch(p)) for p in paths}
            mocks[paths[0]].return_value={'identity':'same'}
            mocks[paths[6]].return_value=SimpleNamespace(images={PATH:{},remark:{}})
            mocks[paths[7]].return_value={};mocks[paths[8]].return_value={}
            args=(object(),publication,attempt,None,'/artifact','/finalization')
            op.verify_candidate(*args)
            self.assertEqual(mocks[paths[11]].call_count,18)
            for p in (paths[1],paths[4],paths[5],paths[7],paths[8],paths[9],paths[10],paths[11],paths[12],paths[13]):
                with self.subTest(stage=p):
                    mocks[p].side_effect=ValueError('injected')
                    with self.assertRaisesRegex(ValueError,'injected'): op.verify_candidate(*args)
                    mocks[p].side_effect=None
            mocks[paths[6]].return_value=SimpleNamespace(images={})
            with self.assertRaisesRegex(PublicationUnavailable,'native_remark_request'):op.verify_candidate(*args)
            mocks[paths[6]].return_value=SimpleNamespace(images={PATH:{},remark:{}})
            mocks[paths[0]].side_effect=[{'identity':'before'},{'identity':'after'}]
            with self.assertRaisesRegex(PublicationUnavailable,'changed_during_verification'):op.verify_candidate(*args)
