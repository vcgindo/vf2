"""Existing business rejection outcomes become durable CSV diagnostics; no daily engine."""
from copy import deepcopy
import csv
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

os.environ.setdefault('VF_SECRET_KEY','csv-diagnostic-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()

from mta.application.r1_importer_master import RAW_COLUMNS, PRIOR_TABLES, process_importer_master
from mta.application.r1_supplier_input import process_supplier_validation, STAGES
from mta.application.intake_errors import NativeIntakeRejected
from mta.runtime.daily_feed import diagnostics


def master_payload():
    row=dict.fromkeys(RAW_COLUMNS)
    row.update(SKUCode='CSV-1',WhCode='CSV-W',ParentWhCode='CSV-P',Norm=10,
               MinNorm=0,RLT=3,RCP=3,GCP=3,PackSize=1)
    return dict(schema='r1-importer-master-input-v1',business_date='2026-10-18',
        run_timestamp='2026-10-18T00:00:00',import_non_nms=False,
        settings=[dict(Parameter=k,Value=v) for k,v in
            (('NMSActive',0),('DBMActive',1),('UpdatePWh_RLT_RCP_GCP',1))],
        prior_provenance=dict(kind='SYNTHETIC_PRIOR_IMPORTER',identity='csv-component-only',business_date='2026-10-17'),
        prior={name:[] for name in PRIOR_TABLES},raw_master=[row],raw_non_nms=[],raw_no_norm=[])


class CsvDiagnosticsTests(unittest.TestCase):
    def test_master_and_supplier_native_reasons_are_preserved_without_repair(self):
        value=master_payload();good=process_importer_master(value)
        self.assertEqual(good['outcome'],'APPLIED')
        duplicate=deepcopy(value);duplicate['raw_master']*=2
        rejected=process_importer_master(duplicate)
        self.assertEqual(rejected['outcome'],'EARLY_RETURN')
        self.assertEqual(rejected['rejects_added'][0]['ReasonCode'],1)
        self.assertEqual(rejected['rejects_added'][0]['ReasonDescription'],
                         'Duplicate entries SKU+Location in Master File/table')
        feeds=dict(SOBDataRaw=[dict(SKUCode='CSV-1',WHCode='CSV-W',SupplierCode='CSV-P',
             SupplierDescription='Parent',SOB=-1.0)],MOQDataRaw1=[],MOQDataRaw2=[])
        supplier=process_supplier_validation(feeds,good,value['settings'],value['run_timestamp'])
        reasons=supplier[STAGES[-1]]['tables']['RejectedMaster']
        self.assertTrue(any(r['ReasonCode']==183 and r['ReasonDescription']==
                            'Negative SOB value in SOB file/table' for r in reasons))
        with tempfile.TemporaryDirectory() as directory:
            attempt=SimpleNamespace(archive_path=directory)
            error=NativeIntakeRejected('producer rejected',stage='component-only',
                                       rejections=rejected['rejects_added']+reasons)
            diagnostics(attempt,error)
            path=Path(directory)/'business-rejections.csv';original=path.read_bytes()
            with path.open(newline='',encoding='utf-8') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual([int(r['ReasonCode']) for r in rows],
                             [r['ReasonCode'] for r in error.rejections])
            diagnostics(attempt,error)
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(len(list(Path(directory).glob('business-rejections*.csv'))),2)

    def test_daily_rejected_subset_retains_other_native_processed_rows(self):
        from tests.test_native_daily_modules import fixture,row,run
        value,master=fixture();value['raw_daily_data'].append(dict(row('D'),Stock=8))
        actual=run(value,master)
        self.assertEqual([r['ReasonCode'] for r in actual['RejectedMaster']],[14])
        self.assertEqual({r['WhCode'] for r in actual['DailyDataProcessed']},{'W','W2','V'})


if __name__=='__main__':unittest.main()
