"""Original diagnostic custody; ORM/byte opening mocked, not native proof."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date
import io
import os
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'diagnostic-unit-only')
import django
django.setup()

from mta.presentation import diagnostic_downloads as subject
from mta.presentation.context import PublicationUnavailable
from mta.runtime import operational_attempts, operational_repair
from mta.runtime.operational_models import OperationalFile
from mta.runtime.operational_reports import REPORT_OPERATIONS
from mta.runtime.operational_alert_runner import ALERT_OPERATION
from mta.application.operational_input_archive import archive_clock


class DiagnosticDownloadTests(unittest.TestCase):
    def fixture(self, selector):
        spec=subject.SELECTORS[selector]
        self.run=Obj(pk='own-run',status='SUCCEEDED',kind='DAILY_CHAIN',business_date=date(2026,10,26))
        self.owner=Obj(run_id=self.run.pk,run=self.run,status='SUCCEEDED',configuration=Obj(pk='config'),
            business_date=self.run.business_date,clock=archive_clock(self.run.business_date)['clock'],
            run_output_digest='o'*64,action_digest='a'*64,source_digest='s'*64,root='owned-original')
        producer=REPORT_OPERATIONS['O5'] if spec['group']=='O5' else ALERT_OPERATION
        self.effect=Obj(attempt=self.owner,status='SUCCEEDED',group=spec['group'],ordinal=5,**producer)
        self.row=Obj(pk=17,operation=self.effect,role='download',relative_path=spec['path'],
            size_bytes=42,sha256='b'*64,members=MagicMock())
        self.members=[dict(ordinal=0,name=spec['member'],size_bytes=9,sha256='c'*64)]
        self.row.members.order_by.return_value.values.return_value=self.members
        self.config=dict(bindings=dict(operation_roster=[dict(group=spec['group'],ordinal=5,**producer)]))

    @contextmanager
    def storage(self):
        with patch.object(OperationalFile.objects,'select_related') as query, \
                patch.object(operational_attempts,'configuration_value',return_value=self.config), \
                patch.object(operational_attempts,'_identity',return_value=dict(
                    output_digest='o'*64,action_digest='a'*64,source_digest='s'*64)) as identity, \
                patch.object(operational_repair,'resolve_operational_file',return_value=self.row) as resolve, \
                patch.object(subject,'_open',return_value=io.BytesIO(b'original zip')) as opened:
            query.return_value.get.return_value=self.row
            yield query,identity,resolve,opened

    def test_ten_exact_original_paths_and_single_members(self):
        self.assertEqual(len(subject.SELECTORS),10)
        for selector in subject.SELECTORS:
            self.fixture(selector)
            with self.subTest(selector=selector),self.storage() as (query,_,resolve,opened):
                stream,name,mime=subject.open_operational_file(self.run,selector,17)
                self.assertEqual(stream.read(),b'original zip')
                self.assertEqual(name,self.row.relative_path.rsplit('/',1)[1])
                self.assertEqual(mime,'application/zip')
                query.return_value.get.assert_called_once_with(pk=17)
                resolve.assert_called_once_with(self.row)
                opened.assert_called_once_with('owned-original',self.row.relative_path,
                    dict(size_bytes=42,sha256='b'*64))

    def test_explicit_report_entitlement_not_actor_or_product_grants(self):
        subject.require_entitlement({'entitlements':['mta-report-urls']})
        for value in (None,{},dict(is_admin=True),dict(entitlements=['mta-input-archive']),
                      dict(entitlements=['mta-report-urls','other']),dict(entitlements='mta-report-urls')):
            with self.subTest(value=value),self.assertRaises(PermissionError):
                subject.require_entitlement(value)

    def test_foreign_incomplete_changed_or_wrong_producer_refused_before_bytes(self):
        changes=(('owner','run_id','foreign'),('run','status','FAILED'),('run','kind','OTHER'),
            ('owner','status','RUNNING'),('owner','business_date',date(2026,10,25)),('owner','clock',None),
            ('effect','status','FAILED'),('effect','name','foreign'),('effect','source_digest','f'*64),
            ('effect','group','O6'),('effect','ordinal',6),('row','role','output'),
            ('row','relative_path','download/foreign.zip'),('owner','action_digest','changed'))
        for target,field,value in changes:
            self.fixture('InvalidDataReport')
            setattr(getattr(self,target),field,value)
            with self.subTest(target=target,field=field),self.storage() as (_,_,resolve,opened):
                with self.assertRaises(PublicationUnavailable):
                    subject.open_operational_file(self.run,'InvalidDataReport',17)
                resolve.assert_not_called();opened.assert_not_called()

    def test_config_member_and_byte_tampering_refused(self):
        for change in ('duplicate_operation','no_operation','member','ordinal','extra_member','bytes'):
            self.fixture('NMSAddNewSKULoc')
            if change=='duplicate_operation':self.config['bindings']['operation_roster']*=2
            if change=='no_operation':self.config['bindings']['operation_roster']=[]
            if change=='member':self.members[0]['name']='Other.csv'
            if change=='ordinal':self.members[0]['ordinal']=1
            if change=='extra_member':self.members.append(deepcopy(self.members[0]))
            with self.subTest(change=change),self.storage() as (_,_,resolve,opened):
                if change=='bytes':resolve.side_effect=ValueError('Original file hash mismatch')
                with self.assertRaises(PublicationUnavailable):
                    subject.open_operational_file(self.run,'NMSAddNewSKULoc',17)
                opened.assert_not_called()

    def test_only_existing_linked_repair_resolver_can_select_replacement(self):
        self.fixture('DailyDataUnavailabilityReport')
        replacement=deepcopy(self.row)
        replacement.operation.attempt.root='owned-linked-repair'
        replacement.sha256='d'*64
        with self.storage() as (_,_,resolve,opened):
            resolve.return_value=replacement
            subject.open_operational_file(self.run,'DailyDataUnavailabilityReport',17)
            resolve.assert_called_once_with(self.row)
            opened.assert_called_once_with('owned-linked-repair',replacement.relative_path,
                dict(size_bytes=42,sha256='d'*64))

    def test_aliases_do_not_lookup_receipts(self):
        self.fixture('InvalidDataReport')
        with self.storage() as (query,_,_,opened):
            for selector in ('InvalidDataReport.zip','invaliddatareport','../InvalidDataReport',
                             'FailedForceNormChanges','InputData','NMSAddNewSKULocLog'):
                with self.subTest(selector=selector),self.assertRaises(PublicationUnavailable):
                    subject.open_operational_file(self.run,selector,17)
            query.assert_not_called();opened.assert_not_called()
