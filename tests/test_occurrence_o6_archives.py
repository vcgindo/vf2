"""Actual O6 CSV/ZIP consumers with temporary owned files and no database."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

from tests.test_occurrence_consumers import fixture
from tests.test_operational_norm_reports import reports as generic_reports
from tests.test_operational_report_files import archive_writer
from mta.application import occurrence_text_policy as policy
from mta.application.operational_norm_reports import norm_report_resultsets, REQUIRED_CONFIGURATION
from mta.application.operational_report_files import norm_report_files, NORM_REPORTS, occurrence_member_names
from mta.application.report_encoding import norm_report_bytes


def inputs():
    run, profile, binding, _ = fixture()
    reports = generic_reports()
    facts = {}
    for norm in (1,2):
        _, _, _, family = fixture(norm)
        report = family['Reports'][0]
        if norm == 1:
            for rows in report['tables'].values():
                if rows: rows.append(deepcopy(rows[0]))
            # The header is a singleton; duplicates belong to data and details.
            report['tables']['ReportHeader'].pop()
        reports[norm+1] = report
        facts[f'Norm{norm}_30days'] = dict(tables=report['tables'],
            summary=policy.summaries([report],binding)[report['stage']])
    resultsets = norm_report_resultsets(reports=reports,configuration=REQUIRED_CONFIGURATION,
        occurrence_text_policy=binding)
    metadata = dict(run_id=str(run.pk),output_digest=run.output_digest,binding=binding,reports=facts)
    return run, profile, metadata, {name:norm_report_bytes(report) for name,report in resultsets.items()}


class OccurrenceO6ArchiveTests(unittest.TestCase):
    def test_empty_affected_population_still_has_explicit_empty_group_member(self):
        _,_,metadata,payloads=inputs()
        report=metadata['reports']['Norm2_30days']
        for name in ('Norm0Norm1Norm2Report','Norm0_1_2ReportDetails','ReportRows'):
            report['tables'][name]=[]
        report['summary']=policy.summaries([dict(stage='norm2-export',tables=report['tables'])],metadata['binding'])['norm2-export']
        payloads['Norm2_30days']=payloads['Norm2_30days'].split(b'\r\n',1)[0]+b'\r\n'
        with TemporaryDirectory() as root:
            norm_report_files(root=root,payloads=payloads,archive_writer=archive_writer,occurrence_metadata=metadata)
            with zipfile.ZipFile(Path(root,'download/Norm_2_Report_30Days.zip')) as archive:
                self.assertEqual(archive.read('Norm_2_Report_30Days.affected-groups.jsonl'),b'')
                summary=json.loads(archive.read('Norm_2_Report_30Days.metadata.json'))['occurrence_text_availability']
                self.assertEqual((summary['affected_groups'],summary['affected_rows']),(0,0))

    def test_actual_norm12_archives_include_exact_metadata_and_duplicate_rows(self):
        run, profile, metadata, payloads = inputs()
        before = deepcopy(metadata)
        with TemporaryDirectory() as root:
            for _ in range(2):
                receipt = norm_report_files(root=root,payloads=payloads,archive_writer=archive_writer,
                    occurrence_metadata=metadata)
                for norm in (1,2):
                    name=f'Norm{norm}_30days';base=NORM_REPORTS[name]
                    with zipfile.ZipFile(Path(root,'download',base+'.zip')) as archive:
                        self.assertEqual(archive.namelist(),[base+'.csv',*occurrence_member_names(name)])
                        self.assertEqual(archive.read(base+'.csv'),payloads[name])
                        body=json.loads(archive.read(base+'.metadata.json'))
                        self.assertEqual(body['run_id'],str(run.pk))
                        self.assertEqual(body['output_digest'],run.output_digest)
                        self.assertEqual(body['occurrence_text_policy'],metadata['binding'])
                        groups=[json.loads(line) for line in archive.read(base+'.affected-groups.jsonl').splitlines()]
                        self.assertEqual(len(groups),2 if norm==1 else 1)
                        self.assertEqual([g['ordinal'] for g in groups],list(range(len(groups))))
                        self.assertTrue(all(g['classification']==policy.CLASSIFICATION for g in groups))
                    self.assertTrue(Path(root,'output',base+'.csv').is_file())
                    self.assertFalse(Path(root,'output',base+'.metadata.json').exists())
                    self.assertFalse(Path(root,'output',base+'.affected-groups.jsonl').exists())
                for name in ('DBMNormChange','NormChangeLog'):
                    with zipfile.ZipFile(Path(root,'download',NORM_REPORTS[name]+'.zip')) as archive:
                        self.assertEqual(archive.namelist(),[NORM_REPORTS[name]+'.csv'])
        self.assertEqual(metadata,before)

    def test_all_metadata_and_csv_rejections_precede_any_file_effect(self):
        for change in ('binding','owner','summary','roster','blank','csv'):
            _, _, metadata, payloads = inputs()
            if change=='binding': metadata['binding']['policy']['version']=99
            if change=='owner': metadata['run_id']='wrong'
            if change=='summary': metadata['reports']['Norm2_30days']['summary']['affected_groups']=99
            if change=='roster': metadata['reports'].pop('Norm2_30days')
            if change=='blank': metadata['reports']['Norm2_30days']['tables']['ReportRows'][0]['values'][8]=' '
            if change=='csv': payloads['Norm2_30days']=b'wrong'
            with TemporaryDirectory() as root:
                writer=Mock()
                with self.assertRaises(ValueError):
                    norm_report_files(root=root,payloads=payloads,archive_writer=writer,occurrence_metadata=metadata)
                self.assertEqual(list(Path(root).iterdir()),[])
                writer.assert_not_called()

    def test_archive_writer_cannot_silently_omit_sidecar(self):
        _, _, metadata, payloads=inputs()
        def incomplete(**arguments):
            arguments['members']=arguments['members'][:1]
            return archive_writer(**arguments)
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,'Occurrence archive member bytes differ'):
                norm_report_files(root=root,payloads=payloads,archive_writer=incomplete,occurrence_metadata=metadata)

    def test_explicit_retry_reuses_exact_zip_and_rejects_changed_sidecar(self):
        from mta.application import operational_io as files
        from mta.runtime import operational_retry as retry
        _,_,metadata,payloads=inputs()
        relative='download/Norm_1_Report_30Days.zip'
        with TemporaryDirectory() as retained_root,TemporaryDirectory() as target_root:
            norm_report_files(root=retained_root,payloads=payloads,archive_writer=archive_writer,occurrence_metadata=metadata)
            file=files.inspect_file(retained_root,relative)
            members=files.zip_members(retained_root,relative)
            original=SimpleNamespace(pk=7,**file,members=Mock())
            original.members.order_by.return_value.values.return_value=members
            effect=SimpleNamespace(files=Mock())
            effect.files.filter.return_value=[original]
            shared={name:'same' for name in ('run_id','configuration_id','predecessor_id','run_output_digest',
                'action_digest','source_digest','business_date','clock')}
            previous=SimpleNamespace(pk='previous',status='FAILED',root=retained_root,retry_of_id=None,
                operations=Mock(),**shared)
            previous.operations.filter.return_value=[effect]
            current=SimpleNamespace(ordinal=5,group='O6',name='NormReports',stage='dbm-files',source_digest='s'*64)
            owner=SimpleNamespace(pk='current',root=target_root,retry_of_id=previous.pk,operations=Mock(),**shared)
            owner.operations.get.return_value=current
            with zipfile.ZipFile(Path(retained_root,relative)) as archive:
                for member in members: files.write_file(target_root,'output/'+member['name'],archive.read(member['name']))
            with patch.object(retry,'require_attempt_lease'),patch.object(retry,'verify_file_direct'), \
                    patch.object(retry.files,'tool_identity'), \
                    patch.object(retry.OperationalAttempt.objects,'get',return_value=previous), \
                    patch.object(retry.files,'archive_files') as fresh_writer:
                writer=retry.retry_archive_writer(owner,executable='unused',tool_sha256='f'*64)
                receipt=writer(root=target_root,staging='output',members=[row['name'] for row in members],destination=relative)
                self.assertEqual(receipt['reused_from_file'],original.pk)
                self.assertEqual(Path(target_root,relative).read_bytes(),Path(retained_root,relative).read_bytes())
                files.remove_file(target_root,relative)
                files.remove_file(target_root,'output/'+members[1]['name'])
                files.write_file(target_root,'output/'+members[1]['name'],b'changed')
                with self.assertRaisesRegex(ValueError,'Retained archive differs'):
                    writer(root=target_root,staging='output',members=[row['name'] for row in members],destination=relative)
                fresh_writer.assert_not_called()

    def test_runner_requires_policy_members_and_preserves_legacy_roster(self):
        from mta.runtime import operational_runner as runner
        run,profile,metadata,_=inputs()
        binding=metadata['binding']
        run.production_manifest={'lineage':[{policy.KEY:binding}]}
        owner=SimpleNamespace(run=run,business_date=run.business_date)
        config={'bindings':{'input_export_database':'DB','upload_log_client_folder':None}}
        alerts={'configuration':{'attach_invalid_data_report_zip':False},'reports':{'phase_exceptions':[]}}
        with patch.object(runner,'read_population',return_value=[]), \
                patch.object(runner,'read_alert_inputs',return_value=alerts), \
                patch('mta.runtime.input_reader.read_input',return_value={'profile':profile}):
            actual=runner._expected_files(owner,config)['O6']
            for norm in (1,2):
                key=f'Norm{norm}_30days';base=NORM_REPORTS[key]
                self.assertEqual(actual['download/'+base+'.zip'],sorted([base+'.csv',*occurrence_member_names(key)]))
            run.production_manifest={'lineage':[{}]}
            legacy=runner._expected_files(owner,config)['O6']
            for key,base in NORM_REPORTS.items():
                self.assertEqual(legacy['download/'+base+'.zip'],[base+'.csv'])

