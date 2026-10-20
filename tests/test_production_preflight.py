"""Pure aggregation/stage barriers; no business day or namespace is executed."""
import copy
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY','preflight-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()

from django.core.management import call_command, CommandError
from mta.runtime import production_preflight as pf
from mta.runtime.production_daily import execute
from mta.mdm.initialization import initialize
from mta.mdm.initialization_contract import decode
from mta.serialization import digest
from tests.production_daily_fixture import initialized_input, day_input
from tests.initialization_input_fixture import encoded
from tests.test_production_daily_contract import encoded_day

INIT='8efa9227-6805-487d-b38a-4344f33f7179'
SOURCE='a'*64
OUTPUT='b'*64


def context(value=None):
    value=initialized_input() if value is None else value
    raw,sha,args=encoded(value)
    return decode(raw,sha,**args)[1]


class ProductionPreflightTests(unittest.TestCase):
    def test_valid_installation_retains_all_types_nulls_duplicates_order_and_full_roster(self):
        value=initialized_input()
        value['masters']['importer']['SKUDescriptionTbl'] *= 2
        before=copy.deepcopy(value)
        raw,sha,args=encoded(value)
        with patch('django.db.backends.utils.CursorWrapper.execute',side_effect=AssertionError('No SQL')):
            report=pf.initialization(raw,sha,**args)
        self.assertTrue(report['contract_valid'])
        self.assertTrue(report['stage_eligibility']['installation'])
        self.assertFalse(report['stage_eligibility']['day'])  # No day facts inspected.
        self.assertFalse(report['stage_eligibility']['preparation'])
        self.assertFalse(report['stage_eligibility']['activation'])
        self.assertEqual(value,before)
        self.assertEqual(raw,encoded(value)[0])
        self.assertIn('bor',report['required_outputs'])
        self.assertIn('boroa',report['required_outputs'])
        self.assertIn('planning_summary',report['required_outputs'])
        self.assertEqual(len(report['required_outputs']),21)
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['execution_acceptance'])

    def test_independent_initial_omissions_and_capabilities_are_aggregated_with_paths_and_owners(self):
        value=initialized_input()
        del value['masters']['importer']['SkuAttributeData'][0]['Weight']
        value['opening']['state']['dbm']['FirstReplenishmentPercentageTbl']=[]
        value['opening']['state']['dbm']['DBMSettingsTbl']=[dict(Parameter='NormZeroOneRuleActive',Value='1')]
        del value['opening']['state']['dbm']['IntermediateTables']
        value['opening']['state']['dbm']['ui_ReportConfigurations']=[]
        value['configuration']['delivery']['batch'].update(ActivateNorm0Report60Days=2,ActivateNorm0Report90Days=-1)
        value['masters']['importer']['SKUDescriptionTbl'][0]['SKUCode']='SKU-ß'
        raw,sha,args=encoded(value)
        report=pf.initialization(raw,sha,**args)
        issues={q['path']:q for q in report['issues']}
        for path in ('/masters/importer/SkuAttributeData/0/Weight',
            '/opening/state/dbm/FirstReplenishmentPercentageTbl',
            '/opening/state/dbm/DBMSettingsTbl/SpikeRuleHorizon',
            '/opening/state/dbm/DBMSettingsTbl/SpikeRuleParCount',
            '/opening/state/dbm/IntermediateTables','/opening/state/dbm/ui_ReportConfigurations',
            '/configuration/delivery/batch/ActivateNorm0Report60Days',
            '/configuration/delivery/batch/ActivateNorm0Report90Days',
            '/configuration/delivery/conditional_dbm',
            '/masters/importer/SKUDescriptionTbl/0/SKUCode'):
            self.assertIn(path,issues)
            self.assertTrue(issues[path]['owner'])
        self.assertEqual(issues['/configuration/delivery/batch/ActivateNorm0Report60Days']['code'],'REPORT_FLAG_INVALID')
        self.assertFalse(report['stage_eligibility']['installation'])
        self.assertEqual(report,pf.initialization(raw,sha,**args))

    def test_missing_opening_does_not_hide_independent_configuration_omissions(self):
        value=initialized_input();del value['opening'];del value['configuration']['force_flags']['nms_active']
        del value['configuration']['delivery']['batch']['AutoDBMActive']
        raw,sha,args=encoded(value)
        report=pf.initialization(raw,sha,**args)
        paths={q['path'] for q in report['issues']}
        self.assertIn('/opening',paths)
        self.assertIn('/configuration/force_flags/nms_active',paths)
        self.assertIn('/configuration/delivery/batch/AutoDBMActive',paths)

    def test_identifier_day_errors_do_not_disable_valid_installation_or_supported_horizon(self):
        value=initialized_input()
        value['configuration']['delivery']['batch']['ActivateNorm0Report60Days']=1
        value['masters']['importer']['SKUDescriptionTbl'][0]['SKUCode']='SKU-9'
        raw,sha,args=encoded(value)
        report=pf.initialization(raw,sha,**args)
        self.assertTrue(report['stage_eligibility']['installation'])
        self.assertFalse(report['stage_eligibility']['day'])
        pf.require(report,'installation')
        with self.assertRaises(pf.PreflightError):pf.require(report,'day')

    def test_supported_60_90_day_flags_remove_only_the_verified_horizon_blocker(self):
        value=initialized_input()
        value['configuration']['delivery']['batch'].update(ActivateNorm0Report60Days=1,ActivateNorm0Report90Days=1)
        frame=context(value);raw,sha=encoded_day(day_input('2037-04-10',root=True))
        with TemporaryDirectory() as root:
            report=pf.daily(raw,sha,frame=frame,initialization_id=INIT,source_digest=SOURCE,
                configuration_digest=digest(frame['profile']),pick_output_root=root,execution_revision='all-horizons')
        self.assertTrue(report['stage_eligibility']['day'],report['issues'])
        self.assertNotIn('NORM_REPORT_HORIZON_UNSUPPORTED',{q['code'] for q in report['issues']})
        self.assertFalse(report['production_ready']);self.assertFalse(report['stage_eligibility']['activation'])
        self.assertTrue({'BOR_SOURCE_UNAVAILABLE','BOROA_SOURCE_UNAVAILABLE','NATIVE_ADMISSION_UNQUALIFIED',
            'SHIPMENT_INTAKE_UNAVAILABLE','GENERAL_RRR_SOURCE_UNQUALIFIED'} <= {q['code'] for q in report['issues']})

    def test_configured_dbm_history_horizons_remove_only_selected_horizon_limits(self):
        value=initialized_input()
        value['configuration']['delivery']['batch'].update(DBMNormChangeReportHorizon=30,
            NormChangeLogHorizon=90,ActivateNormChangeLogReport=1,DailyConsumptionHorizonDBM=365)
        frame=context(value);raw,sha=encoded_day(day_input('2037-04-10',root=True))
        with TemporaryDirectory() as root:
            report=pf.daily(raw,sha,frame=frame,initialization_id=INIT,source_digest=SOURCE,
                configuration_digest=digest(frame['profile']),pick_output_root=root,execution_revision='history')
        self.assertTrue(report['stage_eligibility']['day'],report['issues'])
        codes={issue['code'] for issue in report['issues']}
        self.assertNotIn('NORM_CHANGE_HORIZON_UNSUPPORTED',codes)
        self.assertNotIn('NORM_HISTORY_HORIZON_UNSUPPORTED',codes)
        self.assertFalse(report['production_ready']);self.assertFalse(report['execution_acceptance'])
        self.assertTrue({'BOR_SOURCE_UNAVAILABLE','GENERAL_RRR_SOURCE_UNQUALIFIED'}<=codes)

    def test_bad_dbm_horizon_cutoffs_are_reported_before_day_execution(self):
        raw,sha=encoded_day(day_input('2037-04-10',root=True))
        for name in ('DBMNormChangeReportHorizon','NormChangeLogHorizon','DailyConsumptionHorizonDBM'):
            for horizon in (True,'30',-(2**31),2**31-1):
                with self.subTest(name=name,horizon=horizon),TemporaryDirectory() as root:
                    frame=context();frame['profile']['delivery']['batch'][name]=horizon
                    frame['profile']['delivery']['batch']['ActivateNormChangeLogReport']=1
                    report=pf.daily(raw,sha,frame=frame,initialization_id=INIT,source_digest=SOURCE,
                        configuration_digest=digest(frame['profile']),pick_output_root=root,execution_revision='history')
                    self.assertFalse(report['stage_eligibility']['day'])
                    self.assertIn('/profile/delivery/batch/'+name,{issue['path'] for issue in report['issues']})

    def test_valid_supplied_root_day_is_eligible_but_not_application_or_execution_acceptance(self):
        frame=context();value=day_input('2037-04-10',root=True)
        before=copy.deepcopy((frame,value));raw,sha=encoded_day(value)
        with TemporaryDirectory() as root,patch('django.db.backends.utils.CursorWrapper.execute',side_effect=AssertionError('No SQL')):
            report=pf.daily(raw,sha,frame=frame,initialization_id=INIT,source_digest=SOURCE,
                configuration_digest=digest(frame['profile']),pick_output_root=root,execution_revision='pure-root')
        self.assertTrue(report['stage_eligibility']['day'],report['issues'])
        self.assertFalse(report['stage_eligibility']['preparation'])
        self.assertFalse(report['execution_acceptance'])
        self.assertEqual((frame,value),before)

    def test_daily_independent_bad_facts_flags_remarks_and_owned_queues_are_all_returned(self):
        frame=context();value=day_input('2037-04-10',root=True)
        value['day']['raw_daily'][0]['Stock']='bad'
        value['day']['raw_daily'][1]['ReportDate']='2037-04-12'
        value['day']['control_requests']['phase_stops']=[{}]
        value['consumer_opening']['remarks']['bor']=[{}]
        value['day']['new_force_requests']=[{}]
        raw,sha=encoded_day(value)
        report=pf.daily(raw,sha,frame=frame,initialization_id='bad-id',source_digest='bad',
            configuration_digest='bad',pick_output_root=None,execution_revision='')
        paths={q['path'] for q in report['issues']}
        for path in ('/day/raw_daily/0/Stock','/day/raw_daily/1/ReportDate',
            '/day/control_requests/phase_stops','/day/new_force_requests','/consumer_opening/remarks/bor',
            '/initialization_id','/source_digest','/configuration_digest','/pick_output_root','/execution_revision'):
            self.assertIn(path,paths)

    def test_successor_uses_its_own_closing_shape_and_reports_all_binding_mismatches(self):
        frame=context();value=day_input('2037-04-11');raw,sha=encoded_day(value)
        closing=copy.deepcopy(frame['opening']['state'])
        closing['dbm']['IntermediateTables']=[dict(table='dbo.AcceptedNorms',rows=[])]
        parent=dict(run_id='d30db19c-6d43-4b1b-b7b1-1c2fa0e45bb6',business_date='2037-04-10',
            kind='DAILY_CHAIN',status='SUCCEEDED',output_digest=OUTPUT,initialization_id=INIT,
            source_digest=SOURCE,capture_status='CONSUMED',closing_state=closing)
        with TemporaryDirectory() as root:
            args=dict(frame=frame,predecessor=parent,initialization_id=INIT,source_digest=SOURCE,
                configuration_digest=digest(frame['profile']),predecessor_output_digest=OUTPUT,
                pick_output_root=root,execution_revision='pure-successor')
            report=pf.daily(raw,sha,**args)
            self.assertTrue(report['stage_eligibility']['day'],report['issues'])
            parent.update(status='FAILED',source_digest='c'*64,capture_status='CAPTURED',initialization_id='other')
            report=pf.daily(raw,sha,**args)
        paths={q['path'] for q in report['issues']}
        for field in ('status','source_digest','capture_status','initialization_id'):
            self.assertIn('/predecessor/'+field,paths)

    def test_successor_never_falls_back_to_initialized_state_for_malformed_closing(self):
        frame=context();raw,sha=encoded_day(day_input('2037-04-11'))
        parent=dict(run_id=INIT,business_date='2037-04-10',kind='DAILY_CHAIN',status='SUCCEEDED',
            output_digest=OUTPUT,initialization_id=INIT,source_digest=SOURCE,capture_status='CONSUMED')
        for closing in (None,{},dict(dbm=[],orders={},complete={})):
            with self.subTest(closing=closing),TemporaryDirectory() as root:
                parent['closing_state']=closing
                report=pf.daily(raw,sha,frame=frame,predecessor=parent,initialization_id=INIT,
                    source_digest=SOURCE,configuration_digest=digest(frame['profile']),
                    predecessor_output_digest=OUTPUT,pick_output_root=root,execution_revision='pure')
                self.assertFalse(report['stage_eligibility']['day'])
                self.assertTrue(any(q['path'].startswith('/predecessor/closing_state') for q in report['issues']))

    def test_successor_expedite_age_projection_has_exact_typed_producer_roster(self):
        closing=copy.deepcopy(context()['opening']['state'])
        age=dict(SKUCode='SUPPLIED-Z9',WhCode='OWN-WH8',BRAge=None,BRAgeRedCount=2,BRAgeBlackCount=0)
        for row,code in ((age,None),(None,'OBJECT_REQUIRED'),({k:v for k,v in age.items() if k!='BRAge'},'FIELD_REQUIRED'),
                (dict(age,Norm=18),'FIELD_UNKNOWN'),(dict(age,BRAge='2'),'CONTRACT_INVALID')):
            with self.subTest(row=row):
                closing['btr']['ExpediteDispatches']=[row]
                collector=pf.Requirements('day');pf.closing_shape(collector,closing)
                if code is None:self.assertEqual(collector.issues,[])
                else:self.assertIn(code,{issue['code'] for issue in collector.issues})

    def test_successor_controls_preserve_exact_native_location_spelling(self):
        from mta.mdm.initialization_rows import schema
        for name in ('log','phase_in','phase_out','upload_log'):
            _,fields=schema('input/opening/state/controls/'+name+'/values',[])
            good={('WhCode' if key=='WHCode' else key):None for key in fields}
            good.update(SKUCode='SUPPLIED-Z9',WhCode='OWN-WH8')
            for row,valid in ((good,True),(None,False),(dict(good,WHCode='OWN-WH8'),False),
                    ({key:value for key,value in good.items() if key!='WhCode'},False),
                    (dict(good,WhCode=8),False)):
                with self.subTest(name=name,row=row):
                    closing=copy.deepcopy(context()['opening']['state'])
                    closing['controls'][name]=[row]
                    collector=pf.Requirements('day');pf.closing_shape(collector,closing)
                    self.assertEqual(not collector.issues,valid,collector.issues)

    def test_envelope_errors_are_individually_reported_together(self):
        value=initialized_input()
        value['recipe'].update(extractor='',version=1,projection='unknown')
        value['opening'].update(identity='',date='bad',semantics='unknown',norms_provenance=None)
        value['opening']['state']['publication_context']={'label':1}
        value['pair_exclusions']=[{'SKUCode':99,'WhCode':'x'*51},{}]
        raw,sha,args=encoded(value)
        paths={q['path'] for q in pf.initialization(raw,sha,**args)['issues']}
        for path in ('/recipe/extractor','/recipe/version','/recipe/projection','/opening/identity',
            '/opening/date','/opening/semantics','/opening/norms_provenance',
            '/opening/state/publication_context/label','/pair_exclusions/0/SKUCode',
            '/pair_exclusions/0/WhCode','/pair_exclusions/1/SKUCode','/pair_exclusions/1/WhCode'):
            self.assertIn(path,paths)

    def test_frozen_retry_aggregates_leaf_request_date_revision_and_snapshot_drift(self):
        from datetime import date
        run=SimpleNamespace(status='FAILED',predecessor_id=None,business_date=date(2037,4,10),execution_revision='old')
        capture=SimpleNamespace(run=run,status='CAPTURED',run_id=INIT,request_digest='request',revision_digest='sealed')
        snapshot=dict(revision_digest='sealed',nms_active=True,configuration=dict(task_status_log_horizon=30))
        self.assertEqual(pf.frozen_retry(capture,[INIT],'request',None,'2037-04-10','new',snapshot,True,30),[])
        snapshot.update(revision_digest='changed',nms_active=False,configuration={})
        errors=pf.frozen_retry(capture,[],'changed',None,'2037-04-11','old',snapshot,True,30)
        self.assertEqual({path.removeprefix('/retry_capture_id/') for path,_ in errors},
            {'active_leaf','request_digest','business_date','execution_revision','snapshot/revision_digest',
             'snapshot/nms_active','snapshot/configuration/task_status_log_horizon'})

    def test_shared_pre_capture_request_identity_retains_optional_fields(self):
        from mta.runtime.temporal import request_input
        kwargs=dict(day={'fact':None},profile={'p':1},initial=None,lineage={'own':1},
            initialization_binding={'id':INIT},daily_input_sha256=SOURCE,complete_pick=True,
            pick_output_root='/owned',pick_config_sha256=OUTPUT,shipment_sha256=SOURCE)
        before=copy.deepcopy(kwargs)
        self.assertEqual(request_input(**kwargs),dict(schema='fresh-daily-chain-v1',day=kwargs['day'],
            profile=kwargs['profile'],opening=None,lineage=kwargs['lineage'],report_exceptions={},
            initialization_binding=kwargs['initialization_binding'],daily_input_sha256=SOURCE,
            pick_output_root='/owned',pick_config_sha256=OUTPUT,shipment_sha256=SOURCE))
        self.assertEqual(kwargs,before)

    def test_retry_inspection_verifies_repeated_output_without_leaf_or_file_writes(self):
        from mta.runtime.production_daily import inspect_retry
        frame=context();raw,sha=encoded_day(day_input('2037-04-10',root=True))
        owner=SimpleNamespace(pk=INIT,source=SimpleNamespace(digest=SOURCE),input_sha256=sha,
            input_digest=OUTPUT,configuration_digest=digest(frame['profile']))
        frozen=SimpleNamespace(pk='capture',source_id=SOURCE)
        repeated=SimpleNamespace(origin_id='capture',run=SimpleNamespace(evidence_mode='production',status='SUCCEEDED',production_manifest={'lineage':[{}]}))
        problems=[]
        with TemporaryDirectory() as root,patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects') as captures, \
            patch('mta.runtime.services.read_outputs',return_value={}) as read, \
            patch('mta.application.complete_daily_batch_files.write_run_pick_files') as write:
            captures.select_related.return_value.filter.return_value.first.return_value=repeated
            inspect_retry(raw,sha,owner,frame,None,None,frozen,'new',root,lambda *args:problems.append(args))
            absolute_request=captures.select_related.return_value.filter.call_args.kwargs['request_digest']
            relative=os.path.relpath(root,Path.cwd())
            inspect_retry(raw,sha,owner,frame,None,None,frozen,'new',relative,lambda *args:problems.append(args))
            self.assertEqual(captures.select_related.return_value.filter.call_args.kwargs['request_digest'],absolute_request)
            self.assertEqual(read.call_count,2)
            read.assert_called_with(repeated.run)
            captures.filter.assert_not_called();write.assert_not_called()
        self.assertEqual(problems,[])

    def test_continuation_inspection_reports_seal_and_context_before_any_bootstrap(self):
        from datetime import date
        from mta.runtime.production_daily import inspect_execution
        frame=context();raw,sha=encoded_day(day_input('2037-04-11'))
        owner=SimpleNamespace(pk=INIT,source=SimpleNamespace(digest=SOURCE),input_sha256=sha,
            input_digest=OUTPUT,configuration_digest=digest(frame['profile']))
        parent=SimpleNamespace(pk=INIT,business_date=date(2037,4,10),kind='DAILY_CHAIN',status='SUCCEEDED',
            output_digest=OUTPUT,mdm_input_capture=SimpleNamespace(source=owner.source,status='CONSUMED'))
        binding=dict(id=INIT,source_digest=SOURCE,input_sha256=sha,content_digest=OUTPUT,
            configuration_digest=owner.configuration_digest)
        def inputs(run,components):
            return {'initialization_binding':binding} if components==('initialization_binding',) else {'profile':frame['profile']}
        with TemporaryDirectory() as root, \
            patch('mta.runtime.models.ProductionInitialization.objects') as owners, \
            patch('mta.runtime.models.CalculationRun.objects.get',return_value=parent), \
            patch('mta.mdm.initialization.read_initialized_input',return_value=frame), \
            patch('mta.mdm.production_families.require_initialization'), \
            patch('mta.mdm.production_families.require_binding',side_effect=ValueError('seal drift')), \
            patch('mta.runtime.input_reader.read_input',side_effect=inputs), \
            patch('mta.runtime.services.read_outputs',return_value={'ClosingState':[{}]}), \
            patch('mta.application.daily_finalization.verify_successor'), \
            patch('mta.runtime.production_daily.inspect_completed_request',return_value=False), \
            patch('mta.mdm.integration_source.verify_predecessor',side_effect=ValueError('owner drift')), \
            patch('mta.mdm.production_families.bootstrap_native_families') as bootstrap:
            owners.select_related.return_value.get.return_value=owner
            report,*_=inspect_execution(raw,sha,initialization_id=INIT,source_digest=SOURCE,
                configuration_digest=owner.configuration_digest,pick_output_root=root,
                execution_revision='new',predecessor_id=INIT,predecessor_output_digest=OUTPUT)
        bootstrap.assert_not_called()
        paths={q['path'] for q in report['issues']}
        self.assertIn('/initialization/integration_seal',paths)
        self.assertIn('/predecessor/current_ownership',paths)
        self.assertIn('/predecessor/closing_state/orders',paths)
        self.assertFalse(report['stage_eligibility']['day'])

    def test_completed_normal_request_is_exact_read_only_and_fail_closed(self):
        from datetime import date
        from mta.runtime.production_daily import inspection_request,inspect_completed_request
        frame=context();raw,sha=encoded_day(day_input('2037-04-10',root=True))
        owner=SimpleNamespace(pk=INIT,source=SimpleNamespace(digest=SOURCE),input_sha256=sha,
            input_digest=OUTPUT,configuration_digest=digest(frame['profile']))
        run=SimpleNamespace(status='SUCCEEDED',kind='DAILY_CHAIN',evidence_mode='production',
            predecessor_id=None,business_date=date(2037,4,10))
        repeated=SimpleNamespace(status='CONSUMED',origin_id=None,run=run)
        with TemporaryDirectory() as root:
            _,_,expected,binding=inspection_request(raw,sha,owner,frame,None,None,root)
            args=(raw,sha,owner,frame,None,None,'completed',root)
            with patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects') as captures, \
                    patch('mta.runtime.input_reader.read_input',return_value={
                        'initialization_binding':binding,'daily_input_sha256':sha}) as inputs, \
                    patch('mta.runtime.services.read_outputs',return_value={}) as outputs, \
                    patch('mta.application.complete_daily_batch_files.write_run_pick_files') as files:
                query=captures.select_related.return_value.filter
                query.side_effect=lambda **kw:SimpleNamespace(first=lambda: repeated if
                    kw['source'] is owner.source and kw['request_digest']==expected and
                    kw['run__execution_revision']=='completed' else None)
                self.assertTrue(inspect_completed_request(*args))
                outputs.assert_called_once_with(run);files.assert_not_called()
                self.assertFalse(inspect_completed_request(*args[:6],'different',root))
                changed=day_input('2037-04-10',root=True);changed['day']['raw_daily'][0]['Stock']+=1
                other,other_sha=encoded_day(changed)
                self.assertFalse(inspect_completed_request(other,other_sha,*args[2:]))
                for target,field,bad in ((run,'status','FAILED'),(run,'evidence_mode','validation'),
                        (run,'kind','OTHER'),(run,'predecessor_id',INIT),(run,'business_date',date(2037,4,11)),
                        (repeated,'status','CAPTURED'),(repeated,'origin_id','other-failure')):
                    old=getattr(target,field);setattr(target,field,bad)
                    with self.subTest(field=field),self.assertRaisesRegex(ValueError,'identity/status'):
                        inspect_completed_request(*args)
                    setattr(target,field,old)
                inputs.return_value={'initialization_binding':binding,'daily_input_sha256':'0'*64}
                with self.assertRaisesRegex(ValueError,'input/initialization'):inspect_completed_request(*args)
                inputs.return_value={'initialization_binding':binding,'daily_input_sha256':sha}
                outputs.side_effect=ValueError('typed output drift')
                with self.assertRaisesRegex(ValueError,'typed output drift'):inspect_completed_request(*args)
                files.assert_not_called()

    def test_installation_guard_stops_before_namespace_authorization_or_sql(self):
        value=initialized_input();del value['masters']['importer']['MasterData']
        value['opening']['state']['dbm']['DBMSettingsTbl']=[]
        raw,sha,args=encoded(value)
        with patch('mta.mdm.initialization.authorize_install') as authorize, \
            patch('django.db.backends.utils.CursorWrapper.execute',side_effect=AssertionError('No SQL')):
            with self.assertRaises(pf.PreflightError) as result: initialize(raw,sha,**args)
            authorize.assert_not_called()
        self.assertGreater(len(result.exception.report['issues']),3)

    def test_day_guard_stops_before_bootstrap_owner_queries_or_execute_day(self):
        frame=context();value=day_input('2037-04-10',root=True);value['day']['raw_daily'][0]['Stock']='bad'
        raw,sha=encoded_day(value)
        report=pf.daily(raw,sha,frame=frame,initialization_id=INIT,source_digest=SOURCE,
            configuration_digest=digest(frame['profile']),execution_revision='blocked',pick_output_root=None)
        with patch('mta.runtime.production_daily.inspect_execution',return_value=(report,None,None,frame)), \
            patch('mta.mdm.production_families.bootstrap_native_families') as bootstrap, \
            patch('mta.runtime.temporal.execute_day') as day, \
            patch('django.db.backends.utils.CursorWrapper.execute',side_effect=AssertionError('No SQL')):
            with self.assertRaises(pf.PreflightError):
                execute(raw,sha,initialization_id=INIT,source_digest=SOURCE,
                    configuration_digest=digest(frame['profile']),execution_revision='blocked',pick_output_root='/missing')
        bootstrap.assert_not_called();day.assert_not_called()

    @unittest.skip('S3 preparation/activation command integration is not released')
    def test_native_preparation_and_activation_block_before_writers(self):
        capture=SimpleNamespace(source=SimpleNamespace(receipt=dict(schema='fresh-production-mdm-source-v1')))
        run=SimpleNamespace(pk=INIT)
        for command,writer,options in (
            ('prepare_daily_ui','mta.runtime.management.commands.prepare_daily_ui.prepare_reporting_generation',dict(output_digest=OUTPUT)),
            ('activate_daily_ui','mta.runtime.management.commands.activate_daily_ui.activate',dict(output_digest=OUTPUT,publication_seal=SOURCE))):
            with self.subTest(command=command),patch('mta.runtime.models.CalculationRun.objects.get',return_value=run), \
                patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.filter') as query,patch(writer) as write:
                query.return_value.select_related.return_value.first.return_value=capture
                out=io.StringIO()
                with self.assertRaises(CommandError):call_command(command,run_id=INIT,stdout=out,**options)
                write.assert_not_called()
                report=json.loads(out.getvalue())
                self.assertIn('planning_summary',report['required_outputs'])
                self.assertFalse(report['stage_eligibility'][report['requested_stage']])

    def test_exportable_inspect_cli_reports_all_without_installing(self):
        value=initialized_input();raw,sha,args=encoded(value)
        with TemporaryDirectory() as root:
            file=Path(root)/'supplied.json';file.write_bytes(raw)
            out=io.StringIO()
            # This source-only CLI test has no exported release identity. The
            # independently pinned packaged command is exercised in runtime.
            with patch('mta.runtime.management.commands.initialize_production.initialize') as install, \
                    patch('mta.runtime.management.commands.initialize_production.implementation_digest', return_value='d'*64):
                call_command('initialize_production',str(file),sha256=sha,
                    configuration_digest=args['expected_configuration'],recipe_digest=args['expected_recipe'],inspect=True,stdout=out)
            install.assert_not_called()
        report=json.loads(out.getvalue())
        self.assertTrue(report['stage_eligibility']['installation'])
        self.assertFalse(report['production_ready'])
        self.assertIn('/outputs/bor',{q['path'] for q in report['issues']})

    def test_invalid_inspect_cli_returns_complete_report_and_nonzero_command_error(self):
        value=initialized_input();del value['masters']['importer']['MasterData']
        value['opening']['state']['dbm']['FirstReplenishmentPercentageTbl']=[]
        raw,sha,args=encoded(value)
        with TemporaryDirectory() as root:
            file=Path(root)/'supplied.json';file.write_bytes(raw);out=io.StringIO()
            with patch('mta.runtime.management.commands.initialize_production.implementation_digest', return_value='d'*64), \
                    self.assertRaises(CommandError):
                call_command('initialize_production',str(file),sha256=sha,
                    configuration_digest=args['expected_configuration'],recipe_digest=args['expected_recipe'],inspect=True,stdout=out)
        paths={q['path'] for q in json.loads(out.getvalue())['issues']}
        self.assertIn('/masters/importer/MasterData',paths)
        self.assertIn('/opening/state/dbm/FirstReplenishmentPercentageTbl',paths)

    def test_transport_and_json_errors_are_not_hidden_by_other_capabilities(self):
        raw=b'{"schema":"x","schema":"y"}'
        report=pf.initialization(raw,'0'*64,expected_configuration='bad',expected_recipe='bad')
        codes={q['code'] for q in report['issues']}
        self.assertIn('HASH_DIFFERS',codes);self.assertIn('JSON_INVALID',codes)
        self.assertIn('BOR_SOURCE_UNAVAILABLE',codes)
