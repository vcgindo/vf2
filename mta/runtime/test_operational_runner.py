"""Full O1–O9 persisted-stub protocol; actual files, tools, backup and commands."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import io
import json
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from mta.runtime.test_operational_alert_runner import AlertRunnerProtocol
from mta.runtime.test_operational_reports import OperationalReportProtocol
from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY, capture_input_tables, _schema
from mta.application.operational_inputs import PHYSICAL_TABLES
from mta.application.operational_alerts import ALERT_SEEDS
from mta.application.operational_restore_qualification import RUNTIME_POLICY
from mta.runtime.operational_models import OperationalAttempt
from mta.runtime.operational_attempts import register_configuration, verify_attempt
from mta.runtime.operational_alert_sources import ABORT_OPENING_POLICY
from mta.runtime.operational_opening import OPENING_POLICY, OPENING_TABLES, ACTION_TYPES
from mta.runtime.operational_bor import COLOR_SEQUENCE
from mta.runtime.operational_runner import ROSTER, RUNNER_POLICY
from mta.runtime.services import read_outputs
from mta.serialization import digest


class IntegratedOperationalProtocol(unittest.TestCase):
    run_day = AlertRunnerProtocol.run_day

    def setUp(self):
        AlertRunnerProtocol.setUp(self)
        self.profile['operational_input_sources'] = INPUT_CAPTURE_POLICY
        self.state['controls']['upload_log'] = []
        self.state['supplier'] = dict(SOBData=[], MOQData=[])
        self.input_tables = {}
        for name in PHYSICAL_TABLES:
            row = {}
            for c in _schema['tables']['Importer/'+name]:
                kind = c['type']
                row[c['name']] = (None if c['nullable'] else 'S' if kind in ('nvarchar','varchar') else
                    date(2026,6,6) if kind=='date' else Decimal('1.000') if kind=='decimal' else 1.0 if kind=='float' else 1)
            row['SKUCode']='S'
            self.input_tables[name] = [row, deepcopy(row)]

    def calculate(self, *args):
        result = OperationalReportProtocol.calculate(self, *args)
        result['Reports'][-1]['tables'] = deepcopy(self.control_reports)
        result['_OperationalForceSources'] = deepcopy(self.populations)
        result['_OperationalInputTables'] = capture_input_tables(
            controls={'raw_master':self.input_tables['MasterDataRaw']},
            daily={'DailyDataRaw':self.input_tables['DailyDataRaw']}, supplier=self.input_tables)
        return result

    def test_actual_commands_complete_retry_and_missing_copy_recovery_without_calculation(self):
        day = dict(business_date='2026-06-06', new_force_requests=[],
            raw_master=self.input_tables['MasterDataRaw'], raw_daily=self.input_tables['DailyDataRaw'],
            supplier_feeds={name:self.input_tables[name] for name in ('SOBDataRaw','MOQDataRaw1')},
            shipment_input=dict(schema='daily-transit-raw-v1',business_date='2026-06-06',rows=[]))
        run = self.run_day(day=day)
        before = read_outputs(run)
        calls = len(self.seen)
        root = Path('/cohort2/integrated-runtime-a001')/str(run.pk)
        root.mkdir(parents=True, exist_ok=False)
        opening = {name:[] for name in OPENING_TABLES}
        opening['UIUploadLogActionType'] = deepcopy(ACTION_TYPES)
        label='VFTEST_Fresh_CompleteDaily_fdc5bc5e4d684b3ab8e6d2754df0e2f4_Importer'
        bindings = dict(runner_policy=RUNNER_POLICY, operation_roster=ROSTER,
            opening_policy=OPENING_POLICY, opening_input_digest=run.input_digest, opening_digest=digest(opening),
            abort_opening_policy=ABORT_OPENING_POLICY, abort_opening_digest=digest([]),
            input_export_database=label, input_archive_clock='business-midnight-Asia-Kolkata',
            bor_color_sequence=deepcopy(COLOR_SEQUENCE), upload_log_client_folder=None,
            zip_tool=dict(path='/cohort2/tools/linux/7zz',sha256='d1bc79f00e9815b24048ab167690bdd1dbc387de7dbc47e8d75d68689e49cf4f'),
            alert_configuration=dict(recipient='Not-Defined',cc_recipient='support@vectorconsulting.in',
                profile='Not-Defined',site='VECTORFLOW-DEMO',attach_invalid_data_report_zip=True,
                auto_dbm_active=False,distributor_system_active=False,nms_active=False,fnc_match_master_norm=True),
            postgres_backup=dict(source_database=connection.settings_dict['NAME'],pg_dump_path='/usr/local/bin/pg_dump',
                pg_dump_sha256='b24e777de7beeb22f41c8233285c7f15c5c936739a38330bd780ea7252865cfe',
                pg_restore_path='/usr/local/bin/pg_restore',
                pg_restore_sha256='a3fbe6a9f8b13d451ac94a720c72cade1dc1261a9a50604fe4c90aa7d233c285',qualification=RUNTIME_POLICY))
        settings = [('UIUploadLogHorizon','7'),('IsMTOEnvironment','0'),('BOROAHistoryHorizon','90'),('RRROAHistoryHorizon','90')]
        settings += [(name,'1') for name in ('DoPostBkpImporter','DoPostBkpDBM','DoPostBkpBPR','DoPostBkpBTR','DBBkpCompress')]
        config = register_configuration(source_digest=digest(ROSTER),bindings=bindings,
            settings=[dict(ordinal=i,name=name,value=value) for i,(name,value) in enumerate(settings)],
            tables=[dict(ordinal=i,database_name=label,table_name=name,condition=None) for i,name in enumerate(PHYSICAL_TABLES)],
            alerts=[dict(ordinal=i,name=s['name'],active=s['active']=='1') for i,s in enumerate(ALERT_SEEDS)])
        request = dict(run_id=str(run.pk),configuration_id=config.pk,request_key=uuid.uuid4().hex,
            owned_root=str(root),expected_output_digest=run.output_digest,openings=opening,abort_opening=[])
        request_path=root/'materialize.json'
        request_path.write_text(json.dumps(request),encoding='utf-8')
        with patch('mta.runtime.operational_runner.materialize_backup', side_effect=RuntimeError('after recorded intents')):
            with self.assertRaisesRegex(CommandError, 'after recorded intents'):
                call_command('cohort2_operational','materialize',request=str(request_path),stdout=io.StringIO())
        failed=OperationalAttempt.objects.get(request_key=request['request_key'])
        self.assertEqual(failed.status,'FAILED')
        old_intents=set(failed.operations.get(group='O7').operationalintentevaluation_set.values_list('intent_id',flat=True))
        self.assertEqual(len(old_intents),14)
        old_archives={file.relative_path:file.sha256 for effect in failed.operations.all()
                      for file in effect.files.all() if file.relative_path.endswith('.zip')}
        request.update(request_key=uuid.uuid4().hex,retry_of_id=str(failed.pk))
        request_path=root/'retry.json'
        request_path.write_text(json.dumps(request),encoding='utf-8')
        out=io.StringIO()
        call_command('cohort2_operational','recover',request=str(request_path),stdout=out)
        result=json.loads(out.getvalue())
        self.assertEqual(result['status'],'SUCCEEDED')
        owner=OperationalAttempt.objects.get(pk=result['attempt'])
        self.assertEqual(set(owner.operations.get(group='O7').operationalintentevaluation_set.values_list('intent_id',flat=True)),old_intents)
        self.assertEqual({file.relative_path:file.sha256 for effect in owner.operations.all()
                         for file in effect.files.all() if file.relative_path.endswith('.zip')},old_archives)
        call_command('cohort2_operational','check',attempt=str(owner.pk),stdout=io.StringIO())
        out=io.StringIO()
        call_command('cohort2_operational','recover',request=str(request_path),stdout=out)
        self.assertEqual(json.loads(out.getvalue())['attempt'],str(owner.pk))
        original=owner.operations.get(group='O4').files.get(relative_path='output/InputData.zip')
        receipt=(original.sha256,original.size_bytes)
        (Path(owner.root)/original.relative_path).unlink()
        repair={k:v for k,v in request.items() if k not in ('openings','abort_opening','retry_of_id')}
        repair.update(request_key=uuid.uuid4().hex,repair_of_id=str(owner.pk),repair_file_ids=[original.pk])
        repair_path=root/'repair.json'
        repair_path.write_text(json.dumps(repair),encoding='utf-8')
        call_command('cohort2_operational','recover',request=str(repair_path),stdout=io.StringIO())
        verify_attempt(owner)
        original.refresh_from_db()
        self.assertEqual((original.sha256,original.size_bytes),receipt)
        self.assertFalse((Path(owner.root)/original.relative_path).exists())
        self.assertEqual(read_outputs(run),before)
        self.assertEqual(len(self.seen),calls)
        (root/'receipt.json').write_text(json.dumps(dict(status='PASS',run=str(run.pk),attempt=str(owner.pk),
            failed_attempt=str(failed.pk),preserved_intents=len(old_intents),preserved_archives=len(old_archives),
            configuration=config.pk,calculation_calls_added=len(self.seen)-calls)),encoding='utf-8')
