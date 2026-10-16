"""Exact report-only authorization and disclosure; no daily execution."""
from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

os.environ.setdefault('VF_SECRET_KEY', 'native-disposition-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.application import native_report_disposition as d
from mta.application.norm0_reports import resultsets, export_files
from mta.domain.dbm_norm012 import AmbiguousReport, NORM0_EXPORT_STAGES
from mta.domain.dbm_selected_chain import selected_norm012_stages
from mta.temporal.chain import retain_dbm_stages
from mta.evidence import evidence_mode
from mta.serialization import digest

RUN = '842136be-162e-4da7-a692-686224e007cf'
OUTPUT = 'b' * 64
COLUMNS = ('SKUCode','SKUName','WHCode','WhName','ParentWhCode','ParentNorm',
           'NumOfDaysSold','TotalSale','Occurances')


def state():
    return dict(DBMMaster=[dict(SKUCode=d.KEY[0],WhCode=d.KEY[1],Norm=0,ParentWhCode='LDC001')],
        SKUDescriptionTbl=[dict(SKUCode=d.KEY[0],SKUDescription='KLOP SALUTO CHOCO 105 GR')],
        DailyConsumption=[dict(SKUCode=d.KEY[0],WhCode=d.KEY[1],ReportDate=day,Consumption=q)
                          for day,q in d.OBSERVATIONS],
        LastBatchRunTbl=[dict(LastRunDate=d.DAY+'T00:00:00')],
        SiteDescriptionTbl=[dict(WHCode=d.KEY[1],WHDescription='CONSOLE CIRACAS')],
        SkuAttributeData=[],SkuLocAttributeData=[],LocationAttributeData=[],
        Norm0Norm1Norm2Report=[],Norm0_1_2ReportDetails=[],IntermediateTables=[],
        ui_ReportConfigurations=[dict(ReportName='Norm_0_1_2Report',Col_Code=name,
            Col_Position=i+1,Header=name,Visible=True) for i,name in enumerate(COLUMNS)])


def batch(horizons=(30,60,90)):
    return {**{f'ActivateNorm0Report{h}Days':int(h in horizons) for h in (30,60,90)},
            'ActivateNorm1Report30Days':0,'ActivateNorm2Report30Days':0}


def reports(source=None, exceptions=None, configuration=None):
    with evidence_mode('production'):
        stages=retain_dbm_stages(selected_norm012_stages(d.DAY, source or state(),
            configuration or batch(), exceptions), [])
    return [dict(stage=name,tables=value) for name,value in stages if name in NORM0_EXPORT_STAGES.values()]


class NativeReportDispositionTests(unittest.TestCase):
    def limited(self, source=None):
        return reports(source, {'native_report_disposition':d.binding()})

    def test_exact_group_keeps_typed_data_and_visible_export(self):
        source=state();before=deepcopy(source)
        actual=self.limited(source)
        self.assertEqual(source,before)
        thirty=actual[0]['tables']
        row=thirty['Norm0Norm1Norm2Report'][0]
        self.assertEqual(row,dict(SKUCode=d.KEY[0],WHCode=d.KEY[1],Count=5,
            TotalSale=5,Occurances=None,SKUName='KLOP SALUTO CHOCO 105 GR'))
        self.assertIs(type(row['Count']),int);self.assertIs(type(row['TotalSale']),int)
        self.assertIsNone(thirty['Norm0_1_2ReportDetails'][0]['Occurances'])
        self.assertEqual(thirty['ReportRows'][0]['values'][8],'"'+d.DISPLAY+'"')

    def test_no_disposition_still_fails(self):
        with self.assertRaises(AmbiguousReport):reports()

    def test_sixty_and_ninety_unchanged(self):
        self.assertEqual(self.limited()[1:],reports(configuration=batch((60,90))))

    def test_other_ambiguous_group_is_not_excluded(self):
        source=state()
        source['DBMMaster'].append(dict(SKUCode='OTHER',WhCode=d.KEY[1],Norm=0,ParentWhCode='LDC001'))
        source['SKUDescriptionTbl'].append(dict(SKUCode='OTHER',SKUDescription='Other'))
        source['DailyConsumption'] += [dict(r,SKUCode='OTHER') for r in source['DailyConsumption']]
        with self.assertRaises(AmbiguousReport):self.limited(source)

    def test_changed_observations_duplicates_types_and_order_denied(self):
        for change in ('quantity','bool','date','duplicate','missing','order'):
            with self.subTest(change=change):
                source=state();rows=source['DailyConsumption']
                if change=='quantity':rows[0]['Consumption']=2
                if change=='bool':rows[0]['Consumption']=True
                if change=='date':rows[0]['ReportDate']='2026-10-12'
                if change=='duplicate':rows.append(deepcopy(rows[0]))
                if change=='missing':rows.pop()
                if change=='order':rows.reverse()
                with self.assertRaisesRegex(ValueError,'observations'):self.limited(source)

    def test_master_and_description_multiplicity_denied(self):
        for table in ('DBMMaster','SKUDescriptionTbl'):
            source=state();source[table].append(deepcopy(source[table][0]))
            with self.assertRaisesRegex(ValueError,'multiplicity'):self.limited(source)

    def test_scope_and_boolean_substitution_denied(self):
        for field,value in (('SKUCode','OTHER'),('horizon',60),('business_date','2026-10-18'),
                            ('input_digest','a'*64),('norm',False),('field','TotalSale')):
            value_binding=d.binding();value_binding['policy'][field]=value
            with self.assertRaises(ValueError):d.require_binding(value_binding)
        for day,norm,horizon in (('2026-10-18',0,30),(d.DAY,1,30),(d.DAY,0,60)):
            with self.assertRaises(ValueError):d.report_group(day,state(),d.binding(),norm=norm,horizon=horizon)
        with self.assertRaisesRegex(ValueError,'widen'):
            reports(exceptions={'native_report_disposition':d.binding(),'norm012_occurrence_order_scope':{}})

    def test_readback_csv_and_zip_carry_exact_limitation(self):
        receipt=resultsets(reports=self.limited(),batch=batch(),run_id=RUN,output_digest=OUTPUT,
                           lineage=[{'native_report_disposition':d.binding()}])
        self.assertEqual(receipt['qualification'],'COMPLETE_WITH_LEGACY_FLAWS')
        self.assertEqual(receipt['reports']['Norm0_30days']['limitations'],[d.limitation(d.binding())])
        self.assertNotIn('limitations',receipt['reports']['Norm0_60days'])
        with TemporaryDirectory() as root:
            exported=export_files(root=root,receipt=receipt)
            self.assertEqual(exported,export_files(root=root,receipt=receipt))
            artifact=exported['artifacts'][0]
            with zipfile.ZipFile(Path(root,artifact['archive']['relative_path'])) as archive:
                self.assertEqual(len(archive.namelist()),2)
                self.assertIn(d.DISPLAY.encode(),archive.read('Norm_0_Report_30Days.csv'))
                metadata=json.loads(archive.read('Norm_0_Report_30Days.metadata.json'))
                self.assertEqual(metadata['native_report_disposition'],d.binding())
                self.assertEqual(metadata['limitations'],[d.limitation(d.binding())])
            self.assertEqual([len(a['members']) for a in exported['artifacts']],[2,1,1])

    def test_lost_or_forged_disclosure_is_denied_before_files(self):
        for change in ('blank','number','detail','duplicate'):
            values=self.limited();tables=values[0]['tables']
            if change=='blank':tables['ReportRows'][0]['values'][8]=' '
            if change=='number':tables['Norm0Norm1Norm2Report'][0]['TotalSale']=6
            if change=='detail':tables['Norm0_1_2ReportDetails'][0]['Occurances']='invented'
            if change=='duplicate':tables['ReportRows'].append(deepcopy(tables['ReportRows'][0]))
            with self.assertRaises(ValueError):
                resultsets(reports=values,batch=batch(),run_id=RUN,output_digest=OUTPUT,
                           lineage=[{'native_report_disposition':d.binding()}])

    def test_commit_and_repeated_attempt_require_same_binding(self):
        run=SimpleNamespace(input_digest=d.INPUT,predecessor_id=d.PARENT,business_date=date.fromisoformat(d.DAY),
            execution_revision=d.RETRY,status='SUCCEEDED',production_manifest={})
        lineage=[{'native_report_disposition':d.binding()}]
        d.verify_commit(d.binding(),lineage,run);d.verify_replay(run,lineage,d.ID)
        for requested in (None,'other'):
            with self.assertRaises(ValueError):d.verify_replay(run,lineage,requested)
        with self.assertRaises(ValueError):d.verify_commit(None,lineage,run)
        with self.assertRaises(ValueError):d.verify_commit(d.binding(),[{}],run)
        run.status='FAILED';run.production_manifest={'native_report_disposition':d.binding()}
        d.verify_replay(run,None,d.ID)
        with self.assertRaises(ValueError):d.verify_replay(run,None,None)
        run.input_digest='a'*64
        with self.assertRaises(ValueError):d.verify_replay(run,None,d.ID)

    def test_ordinary_outputs_do_not_inherit_parent_disposition(self):
        run=SimpleNamespace(status='SUCCEEDED',production_manifest={})
        d.verify_commit(None,[{'run_id':RUN}],run)
        d.verify_replay(run,[{'run_id':RUN}],None)
        with self.assertRaises(ValueError):d.verify_replay(run,[{'run_id':RUN}],d.ID)

    def test_native_guard_rejects_generic_exceptions_before_day_calculation(self):
        from mta.runtime.temporal import execute_day
        with patch('mta.runtime.temporal.transaction.get_autocommit',return_value=True):
            with self.assertRaisesRegex(ValueError,'unchanged calculations'):
                execute_day(day={},profile={'delivery':{'site_code':'unit-only'}},execution_revision='test',opening={},
                    production_initialization=object(),daily_input_sha256='a'*64,
                    report_exceptions={'norm012_occurrence_order_scope':{}})


if __name__ == '__main__':unittest.main()
