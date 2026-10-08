"""Real PG capture protocol using declared stub calculations, never engine days."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import unittest
import uuid
import os
from pathlib import Path
from functools import partial
from zipfile import ZipFile
from unittest.mock import patch
from django.db import DatabaseError, transaction, connection
from django.test import override_settings
from mta.application.operational_capture import CAPTURE_POLICY
from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY, capture_input_tables, _schema
from mta.application.operational_inputs import PHYSICAL_TABLES
from mta.runtime import test_temporal as fixture
from mta.runtime.operational_input_source import read_input_source, write_input_source, STORAGE_BINDINGS
from mta.runtime.operational_source_models import OperationalInputSource
from mta.runtime.relational_state import table_sql
from mta.runtime.models import CalculationRun
from mta.serialization import storage
from tests.test_operational_capture import calculated


class InputCaptureProtocol(unittest.TestCase):
    run_day=fixture.TemporalPersistenceTest.run_day

    def setUp(self):
        fixture.TemporalPersistenceTest.setUp(self)
        settings=override_settings(VF_MTA_DAILY_PUBLICATION=False,VF_OPERATIONAL_UNLEASED_TESTS=True)
        settings.enable();self.addCleanup(settings.disable)
        self.profile.update(operational_sources=CAPTURE_POLICY,operational_input_sources=INPUT_CAPTURE_POLICY)
        self.opening['identity']='input-capture-'+uuid.uuid4().hex
        # Explicit protocol-only values for each native column, including NULLs,
        # decimal scale and duplicates. These are not business input defaults.
        self.populations={}
        for name in PHYSICAL_TABLES:
            row={}
            for c in _schema['tables']['Importer/'+name]:
                kind=c['type']
                value=(None if c['nullable'] else 'S' if kind in ('nvarchar','varchar') else
                       date(2026,6,6) if kind=='date' else Decimal('1.000') if kind=='decimal' else
                       1.0 if kind=='float' else 1)
                row[c['name']]=value
            row['SKUCode']='S'
            self.populations[name]=[deepcopy(row),deepcopy(row)]

    def calculate(self,*args):
        result=fixture.TemporalPersistenceTest.calculate(self,*args)
        result['CalculationOutputs'].extend(calculated())
        result['_OperationalInputTables']=capture_input_tables(
            controls={'raw_master':self.populations['MasterDataRaw']},
            daily={'DailyDataRaw':self.populations.get('DailyDataRaw')},supplier=self.populations)
        return result

    def test_live_readback_idempotence_and_late_rollback(self):
        run=self.run_day()
        expected=storage(self.populations)
        self.assertEqual(read_input_source(run),expected)
        calls=len(self.seen)
        self.assertEqual(self.run_day().pk,run.pk)
        self.assertEqual(read_input_source(run),expected)
        self.assertEqual(len(self.seen),calls)
        with transaction.atomic(),self.assertRaisesRegex(ValueError,'live production'):
            write_input_source(run,self.populations)
        with self.assertRaises(DatabaseError),transaction.atomic():
            OperationalInputSource.objects.filter(run=run).update(rows_digest='0'*64)
        self.assertEqual(read_input_source(run),expected)
        self.opening['identity']='input-capture-failed-'+uuid.uuid4().hex
        self.revision='input-failed-'+uuid.uuid4().hex
        with patch('mta.presentation.excess_storage.write_excess',side_effect=RuntimeError('after input capture')):
            with self.assertRaisesRegex(RuntimeError,'after input capture'):
                self.run_day()
        failed=CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(failed.status,'FAILED')
        self.assertFalse(OperationalInputSource.objects.filter(run=failed).exists())
        with connection.cursor() as cursor:
            for name in PHYSICAL_TABLES:
                cursor.execute('SELECT COUNT(*) FROM '+table_sql(STORAGE_BINDINGS[name])+
                    ' WHERE vf_run_id=%s AND vf_image=%s',[failed.pk,'operational/input/'+name])
                self.assertEqual(cursor.fetchone()[0],0)
        self.revision='input-retry-'+uuid.uuid4().hex
        retried=self.run_day()
        self.assertEqual(read_input_source(retried),expected)
        self.assertNotEqual(retried.pk,failed.pk)

    def test_missing_processed_table_denied_without_partial_capture(self):
        self.populations.pop('DailyDataRaw')
        with self.assertRaisesRegex(ValueError,'processed input-table source absent'):
            self.run_day()
        failed=CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(failed.status,'FAILED')
        self.assertFalse(OperationalInputSource.objects.filter(run=failed).exists())

    def test_archive_keeps_intake_and_processed_sources_distinct(self):
        from mta.application.operational_io import archive_files
        from mta.application.operational_inputs import encode_csv
        from mta.application.operational_sqlcmd import input_table_bytes
        from mta.runtime.operational_attempts import register_configuration,start_attempt
        from mta.runtime.operational_reports import REPORT_OPERATIONS,materialize_report_operation
        from mta.runtime.operational_effects import verify_files
        from mta.serialization import digest
        intake=deepcopy(self.populations)
        intake['DailyDataRaw'][0]['Stock']=123
        day=dict(business_date='2026-06-06',raw_master=intake['MasterDataRaw'],raw_daily=intake['DailyDataRaw'],
            supplier_feeds={name:intake[name] for name in ('SOBDataRaw','MOQDataRaw1')},
            shipment_input=dict(schema='daily-transit-raw-v1',business_date='2026-06-06',rows=[]))
        run=self.run_day(day=day);calls=len(self.seen)
        label='VFTEST_Fresh_CompleteDaily_fdc5bc5e4d684b3ab8e6d2754df0e2f4_Importer'
        config=register_configuration(source_digest=digest(REPORT_OPERATIONS['O4']),
            bindings=dict(operation_roster=[dict(ordinal=0,group='O4',**REPORT_OPERATIONS['O4'])],
                input_export_database=label,input_archive_clock='business-midnight-Asia-Kolkata'),
            tables=[dict(ordinal=i,database_name=label,table_name=name,condition=None)
                    for i,name in enumerate(PHYSICAL_TABLES)],settings=[],alerts=[])
        root=Path(os.environ['VF_COHORT2_ARCHIVE_PROOF_ROOT'])/str(run.pk)
        root.mkdir(parents=True,exist_ok=False)
        owner=start_attempt(run_id=run.pk,configuration_id=config.pk,request_key=uuid.uuid4().hex,
                            owned_root=root,expected_output_digest=run.output_digest)
        writer=partial(archive_files,executable='/cohort2/tools/linux/7zz',
            tool_sha256='d1bc79f00e9815b24048ab167690bdd1dbc387de7dbc47e8d75d68689e49cf4f')
        effect=materialize_report_operation(owner.pk,group='O4',archive_writer=writer)
        verify_files(effect)
        with ZipFile(Path(owner.root)/'output/InputData.zip') as archive:
            self.assertEqual(len(archive.namelist()),10)
            columns=_schema['tables']['Importer/DailyDataRaw']
            self.assertEqual(archive.read('DailyDataRaw.csv'),encode_csv(columns,intake['DailyDataRaw']))
            self.assertEqual(archive.read(label+'_DailyDataRaw.CSV'),input_table_bytes(columns,self.populations['DailyDataRaw']))
            self.assertEqual(archive.read('06_06_2026_12_00.txt'),b'File creation date stamp present in file name \r\n')
        self.assertEqual((Path(owner.root)/'output/InputData.zip').read_bytes(),
                         (Path(owner.root)/'download/InputData.zip').read_bytes())
        self.assertEqual(effect.files.count(),2)
        self.assertFalse((Path(owner.root)/'output/InputData').exists())
        self.assertEqual(read_input_source(run),storage(self.populations))
        self.assertEqual(len(self.seen),calls)
