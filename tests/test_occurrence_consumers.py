"""Consumer-only disclosure proofs; no database or day execution."""
from copy import deepcopy
from datetime import date
import json
import os
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

os.environ.setdefault('VF_SECRET_KEY', 'occurrence-consumer-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.application import occurrence_text_policy as p
from mta.application.norm0_reports import resultsets, export_files
from mta.application.operational_norm_reports import norm_report_resultsets, REQUIRED_CONFIGURATION
from mta.runtime import occurrence_reports as consumer
from mta.serialization import digest
from tests.test_operational_norm_reports import reports as generic_reports


def fixture(norm=0):
    run = SimpleNamespace(pk='842136be-162e-4da7-a692-686224e007cf', business_date=date(2026, 10, 30),
        input_digest='a'*64, predecessor_id=None, execution_revision='test', output_digest='b'*64,
        kind='DAILY_CHAIN', status='SUCCEEDED')
    profile = {'unit': 'profile'}
    binding = p.binding(p.owner_for(run, digest(profile), 'c'*40))
    data = dict(SKUCode='S', WHCode='W', Count=2, Occurances=None, TotalSale=4, SKUName='Name')
    detail = dict(SKUCode='S', SKUName='Name', WhCode='W', WhName='Warehouse',
        ParentWhCode='P', ParentNorm=2, NumOfDaysSold=2, TotalSale=4, Occurances=None)
    tables = dict(Norm0Norm1Norm2Report=[data], Norm0_1_2ReportDetails=[detail],
        ReportHeader=[dict(values=['SKUCode','SKUName','WHCode','WHName','ParentCode','ParentNorm',
            'NumOfDaysSold','TotalSale','Occurances'])],
        ReportRows=[dict(values=['S','"Name"','W','"Warehouse"','P','2','2','4','"'+p.DISPLAY+'"'])])
    reports = [dict(stage=f'norm{norm}-export', tables=tables)]
    lineage = [{p.KEY: binding, 'occurrence_text_availability': p.summaries(reports, binding)}]
    run.production_manifest = dict(lineage=lineage)
    run.production_digest = digest(run.production_manifest)
    return run, profile, binding, dict(Reports=reports, Lineage=lineage)


class OccurrenceConsumerTests(unittest.TestCase):
    def test_metadata_discloses_classification_without_reading_outputs(self):
        run, profile, binding, output = fixture(2)
        with patch('mta.runtime.input_reader.read_input', return_value={'profile': profile}):
            values = consumer.metadata(run)
        self.assertEqual(values['Norm2_30days']['occurrence_classification'],p.CLASSIFICATION)
        self.assertEqual(values['Norm2_30days']['occurrence_text_availability']['affected_groups'],1)
        self.assertEqual(values['Norm2_30days'][p.KEY], binding)

    def test_download_preserves_null_and_contains_visible_csv_and_group_metadata(self):
        for norm in (0, 1, 2):
            run, profile, binding, output = fixture(norm)
            before = deepcopy(output)
            with patch('mta.runtime.input_reader.read_input', return_value={'profile': profile}), \
                    patch('mta.runtime.services.read_outputs', return_value=output), \
                    patch('mta.presentation.pick_downloads._attributes', return_value={}), \
                    patch.object(consumer, 'scope', return_value=(['S'], ['W','P'])):
                stream, name = consumer.archive(run, {}, f'Norm{norm}_30days')
            with zipfile.ZipFile(stream) as archive:
                self.assertIn(p.DISPLAY.encode(), archive.read(name[:-4]+'.csv'))
                metadata = json.loads(archive.read(name[:-4]+'.metadata.json'))
                self.assertEqual(metadata[p.KEY], binding)
                group = json.loads(archive.read(name[:-4]+'.affected-groups.jsonl'))
                self.assertEqual((group['norm'],group['Count'],group['TotalSale']), (norm,2,4))
            self.assertEqual(output, before)

    def test_partial_scope_missing_policy_and_blank_disclosure_are_denied(self):
        for change in ('scope', 'policy', 'blank'):
            run, profile, binding, output = fixture()
            if change == 'policy': output['Lineage'] = [{}]
            if change == 'blank': output['Reports'][0]['tables']['ReportRows'][0]['values'][8] = ' '
            with patch('mta.runtime.input_reader.read_input', return_value={'profile': profile}), \
                    patch('mta.runtime.services.read_outputs', return_value=output), \
                    patch('mta.presentation.pick_downloads._attributes', return_value={}), \
                    patch.object(consumer, 'scope', return_value=(['S'], ['W'])):
                with self.assertRaises((ValueError, PermissionError)):
                    consumer.archive(run, {}, 'Norm0_30days')

    def test_native_norm0_zip_sidecar_and_generic_norm12_receipts(self):
        run, profile, binding, output = fixture()
        receipt = resultsets(reports=output['Reports'], batch={
            'ActivateNorm0Report30Days':1,'ActivateNorm0Report60Days':0,'ActivateNorm0Report90Days':0},
            run_id=run.pk, output_digest=run.output_digest, lineage=output['Lineage'])
        with TemporaryDirectory() as root:
            files = export_files(root=root, receipt=receipt)
            self.assertEqual(files['artifacts'][0]['occurrence_text_availability']['affected_groups'], 1)
            self.assertEqual(len(files['artifacts'][0]['members']), 2)
        reports = generic_reports()
        for norm in (1,2):
            _, _, _, family = fixture(norm)
            reports[norm+1] = family['Reports'][0]
        result = norm_report_resultsets(reports=reports, configuration=REQUIRED_CONFIGURATION,
            occurrence_text_policy=binding)
        for norm in (1,2):
            self.assertEqual(result[f'Norm{norm}_30days']['occurrence_classification'], p.CLASSIFICATION)

