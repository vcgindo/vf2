"""Norm0 component proofs; never a production day or fabricated accepted run."""
from copy import deepcopy
from datetime import date,timedelta
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import zipfile

os.environ.setdefault('VF_SECRET_KEY','norm0-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()

from mta.domain.dbm_norm012 import data_stage,detail_stage,export_stage,AmbiguousReport,NORM0_EXPORT_STAGES,CHRONOLOGICAL_RULE
from mta.domain.dbm_selected_chain import selected_norm012_stages
from mta.temporal.chain import retain_dbm_stages
from mta.application.norm0_reports import resultsets,export_files
from mta.application.report_encoding import norm_report_bytes
from mta.serialization import digest

TODAY=date(2037,4,10)
RUN='a1d4d996-a406-41b0-8b15-7e51ca2d2a8f'
OUTPUT='b'*64
COLUMNS=('SKUCode','SKUName','WHCode','WhName','ParentWhCode','ParentNorm','NumOfDaysSold','TotalSale','Occurances')


def observation(days,quantity):
    return dict(SKUCode='SUPPLIEDZ9',WhCode='OWN-WH8',ReportDate=(TODAY+timedelta(days=days)).isoformat(),Consumption=quantity)


def state(rows=()):
    return dict(DBMMaster=[dict(SKUCode='SUPPLIEDZ9',WhCode='OWN-WH8',Norm=0,ParentWhCode='OWN-ROOT7')],
        DailyConsumption=list(rows),LastBatchRunTbl=[dict(LastRunDate=TODAY.isoformat()+'T00:00:00')],
        SKUDescriptionTbl=[dict(SKUCode='SUPPLIEDZ9',SKUDescription='Supplied "name"')],
        SiteDescriptionTbl=[dict(WHCode='OWN-WH8',WHDescription=None)],
        SkuAttributeData=[],SkuLocAttributeData=[],LocationAttributeData=[],
        Norm0Norm1Norm2Report=[],Norm0_1_2ReportDetails=[],IntermediateTables=[],
        ui_ReportConfigurations=[dict(ReportName='Norm_0_1_2Report',Col_Code=name,Col_Position=i+1,
            Header=name,Visible=True) for i,name in enumerate(COLUMNS)])


def batch(horizons=(30,60,90)):
    return {**{f'ActivateNorm0Report{h}Days':int(h in horizons) for h in (30,60,90)},
        'ActivateNorm1Report30Days':0,'ActivateNorm2Report30Days':0}


def retained_reports(source,configuration=None):
    configuration=batch() if configuration is None else configuration
    stages=retain_dbm_stages(selected_norm012_stages(TODAY,source,configuration),[])
    return [dict(stage=name,tables=value) for name,value in stages if name in NORM0_EXPORT_STAGES.values()]


class Norm0HorizonTests(unittest.TestCase):
    def test_strict_boundaries_and_no_upper_cutoff_for_each_horizon(self):
        for horizon in (30,60,90):
            for offset,expected in ((-horizon-1,0),(-horizon,0),(-horizon+1,1),(1,1)):
                with self.subTest(horizon=horizon,offset=offset):
                    result=data_stage(TODAY,state([observation(offset,4)]),0,horizon)['Norm0Norm1Norm2Report']
                    self.assertEqual(len(result),expected)
                    if expected:self.assertEqual((result[0]['Count'],result[0]['TotalSale']),(1,4))

    def test_approved_chronology_keeps_equal_date_source_order_and_duplicates(self):
        rows=[observation(-1,7),observation(-4,3),observation(-1,2),observation(-1,7),
            observation(1,9),observation(-2,0),observation(-3,-1)]
        for horizon in (60,90):
            source=state(rows);before=deepcopy(source)
            row=data_stage(TODAY,source,0,horizon)['Norm0Norm1Norm2Report'][0]
            self.assertEqual(row['Occurances'],'[06/04/37 - 3], [09/04/37 - 7], [09/04/37 - 2], [09/04/37 - 7], [11/04/37 - 9]')
            self.assertEqual((row['Count'],row['TotalSale']),(5,27))
            self.assertEqual(source,before)
            with self.assertRaisesRegex(ValueError,'cannot use occurrence exclusions'):
                data_stage(TODAY,source,0,horizon,[('SUPPLIEDZ9','OWN-WH8')])

    def test_30_retains_ambiguity_and_existing_explicit_qualification(self):
        source=state([observation(-1,2),observation(-3,4)])
        with self.assertRaises(AmbiguousReport):data_stage(TODAY,source,0,30)
        limited=data_stage(TODAY,source,0,30,exclude_all_occurrence_order=True)['Norm0Norm1Norm2Report'][0]
        self.assertIsNone(limited['Occurances'])
        self.assertEqual((limited['Count'],limited['TotalSale']),(2,6))
        before=state([observation(-1,2),observation(-1,2)])
        result=data_stage(TODAY,before,0,30)['Norm0Norm1Norm2Report']
        self.assertEqual(result,[dict(SKUCode='SUPPLIEDZ9',WHCode='OWN-WH8',Count=2,
            Occurances='[09/04/37 - 2], [09/04/37 - 2]',TotalSale=4,SKUName='Supplied "name"')])

    def test_join_multiplication_duplicate_fragments_and_typed_null_attributes(self):
        for horizon in (30,60,90):
            source=state([observation(-1,2),observation(-1,2)])
            source['SKUDescriptionTbl']=[dict(SKUCode='SUPPLIEDZ9',SKUDescription=None)]*2
            attrs={f'c{i}':None for i in range(1,16)}
            source['SkuAttributeData']=[dict(SKUCode='SUPPLIEDZ9',**attrs)]*2
            source['LocationAttributeData']=[dict(WHCode='OWN-WH8',**attrs)]*2
            data=data_stage(TODAY,source,0,horizon)
            self.assertEqual(len(data['Norm0Norm1Norm2Report']),2)
            self.assertEqual([(r['Count'],r['TotalSale']) for r in data['Norm0Norm1Norm2Report']],[(4,8)]*2)
            self.assertEqual(data['Norm0Norm1Norm2Report'][0]['Occurances'],', '.join(['[09/04/37 - 2]']*4))
            detail=detail_stage(data);self.assertEqual(len(detail['Norm0_1_2ReportDetails']),8)
            self.assertTrue(all(r['ParentNorm'] is None and r['SKUAttr1'] is None and r['WhName'] is None for r in detail['Norm0_1_2ReportDetails']))
            exported=export_stage(detail)
            self.assertEqual(len(exported['ReportRows']),8)
            self.assertEqual(exported['ReportRows'][0]['values'][1],'"-"')
            self.assertEqual(exported['ReportRows'][0]['values'][3],' ')

    def test_60_90_sql_null_consumption_and_date_semantics(self):
        for horizon in (60,90):
            source=state([observation(-1,None),observation(-2,4),dict(observation(-3,99),ReportDate=None)])
            row=data_stage(TODAY,source,0,horizon)['Norm0Norm1Norm2Report'][0]
            self.assertEqual((row['Count'],row['TotalSale'],row['Occurances']),(1,4,'[08/04/37 - 4]'))
            with self.assertRaisesRegex(ValueError,'TotalSale requires a non-NULL'):
                data_stage(TODAY,state([observation(-1,None)]),0,horizon)
            with self.assertRaisesRegex(ValueError,'signed32-bit'):
                data_stage(TODAY,state([observation(-1,2147483647),observation(-1,2147483647)]),0,horizon)
            # A valid final cancellation cannot certify an undefined accumulator order.
            with self.assertRaisesRegex(ValueError,'positive subtotal'):
                data_stage(TODAY,state([observation(-1,2147483647),observation(-1,1),observation(-1,-1)]),0,horizon)
            for key in ('SKUCode','WhCode'):
                source=state([dict(observation(-1,4),**{key:None})])
                master_key='SKUCode' if key=='SKUCode' else 'WhCode'
                source['DBMMaster'][0][master_key]=None
                if key=='SKUCode':source['SKUDescriptionTbl'][0]['SKUCode']=None
                self.assertEqual(data_stage(TODAY,source,0,horizon)['Norm0Norm1Norm2Report'],[])

    def test_detail_255_truncation_and_existing_quote_limit_forms(self):
        for horizon in (60,90):
            source=state([observation(-1,q) for q in range(1,30)])
            data=data_stage(TODAY,source,0,horizon)
            detail=detail_stage(data)
            self.assertGreater(len(data['Norm0Norm1Norm2Report'][0]['Occurances']),255)
            self.assertEqual(detail['Norm0_1_2ReportDetails'][0]['Occurances'],data['Norm0Norm1Norm2Report'][0]['Occurances'][:255])
            self.assertEqual(export_stage(detail)['ReportRows'][0]['values'][8],' ')
        report=export_stage(detail_stage(data_stage(TODAY,state([observation(-1,4)]),0,60)))
        self.assertEqual(report['ReportRows'][0]['values'][1],'"Supplied ""name"""')
        self.assertEqual(report['ReportRows'][0]['values'][8],'"[09/04/37 - 4]"')

    def test_simultaneous_dispatch_retains_separate_positive_horizon_families(self):
        source=state([observation(-1,2),observation(-40,4),observation(-70,8)])
        before=deepcopy(source)
        reports=retained_reports(source)
        self.assertEqual([r['stage'] for r in reports],list(NORM0_EXPORT_STAGES.values()))
        self.assertEqual([r['tables']['Norm0Norm1Norm2Report'][0]['TotalSale'] for r in reports],[2,6,14])
        self.assertEqual([r['tables']['Norm0_1_2ReportDetails'][0]['NumOfDaysSold'] for r in reports],[1,2,3])
        self.assertEqual(source,before)
        receipt=resultsets(reports=reports,batch=batch(),run_id=RUN,output_digest=OUTPUT)
        self.assertEqual(receipt['reports']['Norm0_60days']['occurrence_rule'],CHRONOLOGICAL_RULE)
        with TemporaryDirectory() as root:
            files=export_files(root=root,receipt=receipt)
            self.assertEqual(files,export_files(root=root,receipt=receipt))
            for artifact in files['artifacts']:
                csv=Path(root,artifact['csv']['relative_path'])
                with zipfile.ZipFile(Path(root,artifact['archive']['relative_path'])) as archive:
                    self.assertEqual(archive.read(csv.name),csv.read_bytes())
                self.assertIn('/'+RUN+'/'+OUTPUT+'/',artifact['csv']['relative_path'])
                self.assertIn('occurrence_classification',artifact)
                self.assertEqual(csv.read_bytes(),norm_report_bytes(receipt['reports'][f"Norm0_{artifact['horizon']}days"]))

    def test_typed_family_binding_and_full_save_read_preserve_each_horizon(self):
        from mta.runtime import relational_state as rs
        reports=retained_reports(state([observation(-1,2),observation(-40,4),observation(-70,8)]))
        output=dict(ClosingState=[{'dbm':{},'publication_context':{'label':'component only'}}],Reports=reports,Lineage=[],PublicationContext=[])
        images={};exports={};bindings={}
        def save_image(run,path,binding,rows):
            bindings[path]=binding;images[path]=deepcopy(rows)
            return {'image':path,'table':'/'.join(rs.CATALOG['bindings'][binding])}
        def save_export(run,path,rows):
            exports[path]=deepcopy(rows);return {'image':path}
        run=SimpleNamespace(pk=uuid.UUID(RUN))
        with patch.object(rs,'save_image',side_effect=save_image),patch.object(rs,'save_export',side_effect=save_export), \
            patch.object(rs,'load_image',side_effect=lambda run,item:deepcopy(images[item['image']])), \
            patch.object(rs,'load_export',side_effect=lambda run,item:deepcopy(exports[item['image']])):
            run.production_manifest=rs.save_daily(run,output)
            read=rs.read_daily(run)
        self.assertEqual(read['Reports'],reports)
        self.assertEqual(len(exports),6)
        self.assertEqual(bindings['reports/norm0-60-export/Norm0_1_2ReportDetails'],'reports/norm0-export/Norm0_1_2ReportDetails')
        self.assertEqual(bindings['reports/norm0-90-export/Norm0_1_2ReportDetails'],'reports/norm0-export/Norm0_1_2ReportDetails')

    def test_consumer_rejects_missing_duplicate_family_and_drift_before_files(self):
        reports=retained_reports(state([observation(-1,2)]))
        for invalid in (reports[:-1],reports+[reports[1]]):
            with self.assertRaisesRegex(ValueError,'Exactly one'):
                resultsets(reports=invalid,batch=batch(),run_id=RUN,output_digest=OUTPUT)
        receipt=resultsets(reports=reports,batch=batch(),run_id=RUN,output_digest=OUTPUT)
        receipt['reports']['Norm0_90days']['run_id']=str(uuid.uuid4())
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,'owner/horizon differs'):export_files(root=root,receipt=receipt)
            self.assertEqual(list(Path(root).iterdir()),[])

    def test_runtime_consumer_requires_real_native_completed_digest_and_flags(self):
        from mta.runtime.norm0_reports import read_reports
        source=SimpleNamespace(digest='a'*64,receipt={'schema':'fresh-production-mdm-source-v1'})
        run=SimpleNamespace(pk=uuid.UUID(RUN),kind='DAILY_CHAIN',status='SUCCEEDED',output_digest=OUTPUT,
            business_date=TODAY,mdm_input_capture=SimpleNamespace(status='CONSUMED',source=source))
        reports=retained_reports(state([observation(-1,2)]))
        inputs=dict(profile={'delivery':{'batch':batch()}},initialization_binding={'id':RUN,'source_digest':source.digest})
        with patch('mta.runtime.norm0_reports.CalculationRun.objects.get',return_value=run), \
            patch('mta.runtime.norm0_reports.read_input',return_value=inputs), \
            patch('mta.runtime.norm0_reports.read_outputs',return_value={'Reports':reports,'Lineage':[{}]}) as read:
            receipt=read_reports(run_id=RUN,expected_output_digest=OUTPUT)
            self.assertEqual(receipt['enabled_horizons'],[30,60,90])
            read.reset_mock()
            with self.assertRaisesRegex(ValueError,'Exact completed'):read_reports(run_id=RUN,expected_output_digest='c'*64)
            read.assert_not_called()
            run.status='FAILED'
            with self.assertRaisesRegex(ValueError,'Exact completed'):read_reports(run_id=RUN,expected_output_digest=OUTPUT)
            read.assert_not_called()

    def test_export_cli_is_read_only_and_propagates_owner_failure(self):
        from django.core.management import call_command,CommandError
        with TemporaryDirectory() as root, \
            patch('mta.runtime.management.commands.export_norm0_reports.export_reports',side_effect=ValueError('owner drift')) as export:
            with self.assertRaisesRegex(CommandError,'owner drift'):
                call_command('export_norm0_reports',run=RUN,output_digest=OUTPUT,owned_root=root)
            export.assert_called_once_with(run_id=RUN,expected_output_digest=OUTPUT,root=root)
            self.assertEqual(list(Path(root).iterdir()),[])


if __name__=='__main__':unittest.main()
