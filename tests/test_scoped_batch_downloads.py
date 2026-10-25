"""Pinned finite batch admission without regeneration or serving mutations."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','scoped-batch-download-unit-only')
import django
django.setup()
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import hashlib
import io
import json
import unittest
import zipfile
from unittest.mock import patch
from django.test import override_settings
from mta.presentation import scoped_batch_files as producer, scoped_batch_downloads as download
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest
import test_scoped_batch_files as batch_tests


class ScopedBatchDownloadsTests(unittest.TestCase):
    def setup_files(self,parent,nonempty=False,archive_writer=None):
        helper=batch_tests.ScopedBatchFilesTests()
        phase,bags=helper.fixture(nonempty=nonempty)
        root=Path(parent)/'prepared'
        with helper.context(phase,bags):
            metadata,paths=producer.prepare('phase',expected_digest='phase-digest',
                declaration=deepcopy(producer.TEST_DECLARATION),root=root,archive_writer=archive_writer)
        view=NS(run_id='run',bpr=NS(sources=NS(acceptance_id='phase',acceptance_digest='phase-digest',snapshot_digest='snapshot')))
        return phase,root,view

    def verify(self,phase,root,**changes):
        arguments=dict(expected_digest='phase-digest',expected_run_id='run',expected_snapshot_digest='snapshot',
            manifest_file=root/'scoped-batch-files.json',manifest_sha256=hashlib.sha256((root/'scoped-batch-files.json').read_bytes()).hexdigest())
        arguments.update(changes)
        with patch('mta.runtime.scope_runtime_reports.require_test_database'), \
                patch.object(download.scoped_sources,'_accepted_phase',return_value=phase), \
                patch.object(producer,'payload',side_effect=AssertionError('producer reached')), \
                patch.object(producer,'prepare',side_effect=AssertionError('producer reached')):
            return download.verify('phase',**arguments)

    def rewrite(self,root,change):
        path=root/'scoped-batch-files.json'
        value=json.loads(path.read_text())
        change(value)
        value['payload_digest']=digest({k:v for k,v in value.items() if k not in ('digest','payload_digest','files','wrappers')})
        value['digest']=digest({k:v for k,v in value.items() if k!='digest'})
        path.write_text(json.dumps(value))

    def test_owned_empty_and_no_file_branches_verify_with_compact_identity(self):
        with TemporaryDirectory() as parent:
            phase,root,view=self.setup_files(parent)
            result=self.verify(phase,root)
            self.assertEqual(result['counts']['BPRExceptionReport'],0)
            self.assertEqual(result['files']['output/NoNormParentReport.csv']['size_bytes'],0)
            self.assertNotIn('download/BPRExceptionReport.zip',result['files'])
            self.assertEqual(result['snapshot_digest'],'snapshot')
            self.assertEqual(len(result['files']),4)
            self.assertNotIn('sources',result)

    def test_file_tamper_missing_no_file_and_unexpected_file_deny(self):
        for defect in ('tamper','missing','unexpected','forged-empty'):
            with self.subTest(defect=defect),TemporaryDirectory() as parent:
                phase,root,view=self.setup_files(parent)
                if defect=='tamper':(root/download.DOWNLOAD).write_bytes(b'changed')
                elif defect=='missing':(root/'output/NoNormParentReport.csv').unlink()
                elif defect=='unexpected':(root/'output/BPRExceptionReport.csv').write_bytes(b'')
                else:self.rewrite(root,lambda value:value['payloads']['NoNormParentReport'].update(sha256='1'*64))
                with self.assertRaises(PublicationUnavailable):self.verify(phase,root)

    def test_manifest_pin_owner_recipe_and_physical_source_are_enforced(self):
        for defect in ('pin','run','snapshot','recipe','source'):
            with self.subTest(defect=defect),TemporaryDirectory() as parent:
                phase,root,view=self.setup_files(parent)
                args={}
                if defect=='pin':args['manifest_sha256']='0'*64
                elif defect=='run':args['expected_run_id']='other'
                elif defect=='snapshot':args['expected_snapshot_digest']='other'
                elif defect=='recipe':self.rewrite(root,lambda value:value.update(recipe_digest='0'*64))
                else:self.rewrite(root,lambda value:value['sources']['state/importer/MasterData'].update(physical_image='phase/PRE_BPR/importer/other'))
                with self.assertRaises(PublicationUnavailable):self.verify(phase,root,**args)

    def test_nonempty_archives_verify_exact_decompressed_member_payloads(self):
        def archive(*,root,staging,members,destination):
            target=Path(root)/destination
            target.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(target,'x') as output:
                for name in members:output.write(Path(root)/staging/name,name)
            return dict(test_writer=True)
        with TemporaryDirectory() as parent:
            phase,root,view=self.setup_files(parent,nonempty=True,archive_writer=archive)
            result=self.verify(phase,root)
            self.assertIn('download/BPRExceptionReport.zip',result['files'])
            self.assertIn('output/NoNormParentReport.zip',result['files'])
            self.assertNotIn('output/NoNormParentReport.csv',result['files'])
            # Even a re-pinned archive file must retain the canonical member.
            target=root/'download/BPRExceptionReport.zip'
            target.unlink()
            with zipfile.ZipFile(target,'x') as output:output.writestr('wrong.csv',b'wrong')
            receipt=dict(relative_path='download/BPRExceptionReport.zip',size_bytes=target.stat().st_size,
                         sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            self.rewrite(root,lambda value:value['files'].__setitem__(next(i for i,item in enumerate(value['files'])
                if item['relative_path']==receipt['relative_path']),receipt))
            with self.assertRaises(PublicationUnavailable):self.verify(phase,root)

    def test_unsupported_default_partial_config_and_no_arbitrary_download(self):
        view=NS()
        with override_settings(VF_MTA_SCOPE_BATCH_MANIFEST_FILE='',VF_MTA_SCOPE_BATCH_MANIFEST_SHA256=''):
            self.assertIsNone(download.selected(view))
            with self.assertRaises(PublicationUnavailable):download.open_file(view)
        with override_settings(VF_MTA_SCOPE_BATCH_MANIFEST_FILE='path',VF_MTA_SCOPE_BATCH_MANIFEST_SHA256=''):
            with self.assertRaises(PublicationUnavailable):download.configured()
        for path in ('../secret','output/24-FailedForceNormChanges.csv','download/InputData.zip',
                     'download/../output/BOR_OrderAllocation.csv','/etc/passwd'):
            with self.assertRaises(PublicationUnavailable):download.open_file(view,path)

    def test_re_pinned_manifest_cannot_add_arbitrary_relative_path(self):
        with TemporaryDirectory() as parent:
            phase,root,view=self.setup_files(parent)
            self.rewrite(root,lambda value:value['files'][0].update(relative_path='../secret'))
            with self.assertRaises(PublicationUnavailable):self.verify(phase,root)

    def test_selected_lightweight_view_and_open_only_verified_bor(self):
        with TemporaryDirectory() as parent:
            phase,root,view=self.setup_files(parent)
            expected=self.verify(phase,root)
            path=root/'scoped-batch-files.json'
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            with override_settings(VF_MTA_SCOPE_BATCH_MANIFEST_FILE=str(path),VF_MTA_SCOPE_BATCH_MANIFEST_SHA256=sha), \
                    patch('mta.runtime.scope_runtime_reports.require_test_database'), \
                    patch.object(download.scoped_sources,'_accepted_phase',return_value=phase), \
                    patch.object(download,'_open_download',return_value=io.BytesIO(b'BOR')) as opened:
                self.assertEqual(download.selected(view),expected)
                with download.open_file(view) as stream:self.assertEqual(stream.read(),b'BOR')
                opened.assert_called_once_with(root,expected['files'][download.DOWNLOAD])

    @unittest.skipUnless(os.name=='posix' and hasattr(os,'O_NOFOLLOW'),'Native serving no-follow open runs on Linux')
    def test_native_no_follow_open_verifies_retained_handle_bytes(self):
        with TemporaryDirectory() as parent:
            phase,root,view=self.setup_files(parent)
            verified=self.verify(phase,root)
            with download._open_download(root,verified['files'][download.DOWNLOAD]) as stream:
                self.assertEqual(stream.read(),(root/download.DOWNLOAD).read_bytes())
