"""Actual canonical ZIP creation, mocked database custody and HTTP selection."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime,date
from hashlib import sha256
import io
from inspect import unwrap
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import MagicMock,patch
import uuid

from tests.test_intake_diagnostics import rejected
from mta.runtime import diagnostic_publication as subject,intake_diagnostics as custody
from mta.presentation import diagnostic_downloads,views,scoped_api
from mta.presentation.context import PublicationUnavailable
from mta.application import operational_io
from mta.serialization import digest
from django.test import RequestFactory


class DiagnosticPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='diagnostic-zip-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.initial=Obj(pk=uuid.uuid4(),source_id=1)
        self.owner=Obj(pk=uuid.uuid4(),initialization=self.initial,initialization_id=self.initial.pk,
            kind='IMPORTER',clock=datetime(2026,10,26,10,15,0,3000),digest='a'*64)
        self.rows=dict(rejections=custody.rejection_rows(rejected()),aborts=[],observations=[],settings=[])
        for row in self.rows['rejections']:row['RejectionDate']=self.owner.clock
        history=deepcopy(self.rows['rejections'][0])
        history.update(ordinal=2,RejectionDate=datetime(2026,10,25,10,15,0,7000),ReasonDescription='old rejection')
        self.rows['rejections'].append(history)

    def test_canonical_download_zip_is_written_once_from_committed_failure_rows(self):
        saved=[]
        def archive(**values):
            row=Obj(**values,save=MockSave(saved));return row
        with patch.object(subject.transaction,'get_autocommit',return_value=True), \
                patch.object(subject.transaction,'atomic',side_effect=lambda:nullcontext()), \
                patch('mta.runtime.production_scope.authorize'), \
                patch('mta.runtime.daily_feed.job_lock',side_effect=lambda *_:nullcontext()), \
                patch.object(custody,'read',return_value=(self.owner,self.rows)), \
                patch.object(custody,'setting',side_effect=lambda *_:nullcontext()), \
                patch.object(subject,'IntakeDiagnosticArchive') as model, \
                patch('mta.runtime.models.ProductionInitialization.objects.select_for_update') as lock, \
                patch.object(subject,'_publish',return_value='published') as publish:
            model.objects.filter.return_value.first.return_value=None;model.side_effect=archive
            lock.return_value.get.return_value=self.initial
            self.assertEqual(subject.publish_failure(self.owner.pk,output_root=self.root),'published')
            row=publish.call_args.kwargs['failure_archive'];payload=subject._payload(self.owner,self.rows)
            self.assertNotIn(b'old rejection',payload)
            members=operational_io.zip_members(row.root,row.relative_path)
            self.assertEqual(members,[dict(ordinal=0,name='InvalidDataReport.csv',sha256=sha256(payload).hexdigest(),size_bytes=len(payload))])
            self.assertEqual(row.sha256,operational_io.sha256_file(Path(row.root)/row.relative_path))
            self.assertEqual(len(saved),1)
            self.assertEqual(publish.call_args.kwargs['owner_digest'],row.digest)
            # Repeated acknowledgement uses the accepted original and creates
            # no new archive directory, producer call or database file receipt.
            model.objects.filter.return_value.first.return_value=row
            before=list(self.root.iterdir())
            with patch.object(subject,'read_archive',return_value=(self.owner,row)), \
                    patch.object(subject.writers,'invalid_data_report_files') as writer:
                subject.publish_failure(self.owner.pk,output_root=self.root)
                writer.assert_not_called()
            self.assertEqual(list(self.root.iterdir()),before);self.assertEqual(len(saved),1)

    def test_fullkit_original_hash_and_canonical_current_clock_are_required(self):
        self.owner.kind='FULLKIT';self.owner.metadata={'capture_root':str(self.root)}
        (self.root/'original.csv').write_bytes(b'original')
        self.rows['observations']=[dict(Exists=True,member='original.csv',sha256=sha256(b'original').hexdigest(),size_bytes=8),
            dict(Exists=False,member=None,sha256=None,size_bytes=None)]
        self.rows['aborts']=[dict(ordinal=0,FileId=3,RunDateTime=datetime(2026,10,25,10,15,0,7000),Reason='old',inherited=True),
            dict(ordinal=1,FileId=4,RunDateTime=self.owner.clock,Reason='actual missing',inherited=False)]
        subject._verify_originals(self.owner,self.rows)
        payload=subject._payload(self.owner,self.rows)
        self.assertIn(b'actual missing',payload);self.assertNotIn(b'old',payload)
        (self.root/'original.csv').write_bytes(b'changed')
        with self.assertRaises(ValueError):subject._verify_originals(self.owner,self.rows)

    def test_archive_error_cannot_publish_or_discard_failure_custody(self):
        with patch.object(subject.transaction,'get_autocommit',return_value=True), \
                patch('mta.runtime.production_scope.authorize'), \
                patch('mta.runtime.daily_feed.job_lock',side_effect=lambda *_:nullcontext()), \
                patch.object(custody,'read',return_value=(self.owner,self.rows)), \
                patch.object(subject.IntakeDiagnosticArchive.objects,'filter') as query, \
                patch.object(subject.writers,'invalid_data_report_files',side_effect=OSError('disk failure')), \
                patch.object(subject,'_publish') as publish:
            query.return_value.first.return_value=None
            with self.assertRaises(OSError):subject.publish_failure(self.owner.pk,output_root=self.root)
            publish.assert_not_called()
            self.assertEqual(len(list(self.root.iterdir())),1) # failed attempt preserved


class MockSave:
    def __init__(self,events):self.events=events
    def __call__(self,**kwargs):self.events.append(kwargs)


class DiagnosticHttpTests(unittest.TestCase):
    def test_all_ten_existing_full_and_phase_handlers_return_original_zip_and_deny_missing_entitlement(self):
        factory=RequestFactory();run=Obj(pk=uuid.uuid4())
        for name in diagnostic_downloads.SELECTORS:
            request=factory.get('/api/mta/DownloadReports/'+name)
            for handler in ('full','phase'):
                with self.subTest(name=name,handler=handler), \
                        patch.object(views,'identity',return_value={'id':7,'entitlements':['mta-report-urls']}), \
                        patch.object(views,'selected_run',return_value=run), \
                        patch.object(diagnostic_downloads,'open_file',return_value=(io.BytesIO(b'zip bytes'),name+'.zip','application/zip')) as opened:
                    response=(unwrap(views.download_report)(request,{},report_name=name) if handler=='full'
                        else scoped_api._download(Obj(run=run),request,{},name))
                    self.assertEqual(response.status_code,200);self.assertEqual(response['Content-Type'],'application/zip')
                    self.assertEqual(b''.join(response.streaming_content),b'zip bytes');response.close()
                    self.assertIs(opened.call_args.args[0],run)
            with patch.object(views,'identity',return_value={'id':7}),patch.object(diagnostic_downloads,'open_file') as opened:
                self.assertEqual(unwrap(views.download_report)(request,{},report_name=name).status_code,403)
                self.assertEqual(scoped_api._download(Obj(run=run),request,{},name).status_code,403)
                opened.assert_not_called()

    def test_source_qualified_publication_digest_and_absence_fail_closed(self):
        run=Obj(mdm_input_capture=Obj(source_id=1));initial=Obj(pk=uuid.uuid4(),source_id=1)
        owner=Obj(pk=uuid.uuid4(),initialization_id=initial.pk,kind='FULLKIT')
        archive=Obj(root='archive-root',relative_path='download/DailyDataUnavailabilityReport.zip',
            sha256='a'*64,size_bytes=10,digest='b'*64)
        selected=Obj(initialization_id=initial.pk,selector='DailyDataUnavailabilityReport',
            failure_archive_id=owner.pk,operational_file_id=None)
        selected.digest=digest(subject._publication_body(selected,archive.digest))
        with patch('django.db.connection.cursor'),patch.object(custody,'verify_guards'), \
                patch('mta.runtime.models.ProductionInitialization.objects.get',return_value=initial), \
                patch.object(subject.DiagnosticPublication.objects,'filter') as publications, \
                patch.object(subject,'read_archive',return_value=(owner,archive)), \
                patch.object(diagnostic_downloads,'_open',return_value=io.BytesIO(b'zip bytes')) as opened:
            query=publications.return_value.select_related.return_value.order_by.return_value
            query.first.return_value=selected
            identity={'entitlements':['mta-report-urls']}
            diagnostic_downloads.open_file(run,identity,'DailyDataUnavailabilityReport')
            publications.assert_called_with(initialization=initial,selector='DailyDataUnavailabilityReport')
            opened.assert_called_once();opened.reset_mock()
            for change in ('digest','foreign','absent'):
                selected.digest=digest(subject._publication_body(selected,archive.digest));owner.initialization_id=initial.pk
                query.first.return_value=selected
                if change=='digest':selected.digest='f'*64
                if change=='foreign':owner.initialization_id=uuid.uuid4()
                if change=='absent':query.first.return_value=None
                with self.subTest(change=change),self.assertRaises(PublicationUnavailable):
                    diagnostic_downloads.open_file(run,identity,'DailyDataUnavailabilityReport')
                opened.assert_not_called()
