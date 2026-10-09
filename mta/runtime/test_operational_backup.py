"""Explicit real backup proof on an owned protocol database and stub daily run."""
import os
import json
from pathlib import Path
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch
from django.test import override_settings
from mta.runtime import test_temporal as fixture
from mta.runtime.operational_attempts import register_configuration,start_attempt
from mta.runtime.operational_backup import materialize_backup,verify_backup,BACKUP_OPERATION
from mta.runtime.operational_effects import verify_files
from mta.serialization import digest
from mta.application.operational_restore_qualification import RUNTIME_POLICY


class BackupReceiptVerification(unittest.TestCase):
    """Reject stale/misattributed backup receipts before accepting logical proof."""

    def setUp(self):
        owner=SimpleNamespace(root='/owned',configuration=object())
        effect=SimpleNamespace(pk=1,attempt_id=uuid.uuid4(),attempt=owner,
                               group='O8',**BACKUP_OPERATION)
        file=SimpleNamespace(operation_id=1,role='postgres-backup',
            relative_path='backup/post.dump',sha256='a'*64,size_bytes=20)
        self.backup=SimpleNamespace(operation=effect,file=file,database_system='PostgreSQL',
            database_name='fresh_cohort2_protocol_test',method='pg_dump-custom-snapshot',
            snapshot_identity='snapshot-1',restore_target='fresh_cohort2_restore_'+effect.attempt_id.hex,
            restore_status='VERIFIED',tool_sha256='b'*64,qualification='',qualification_sha256='',
            logical_digest='c'*64,restored_digest='c'*64)
        config=dict(bindings=dict(postgres_backup=dict(source_database=self.backup.database_name,
            pg_dump_sha256=self.backup.tool_sha256,qualification=None)))
        self.result=dict(status='VERIFIED',logical_digest='c'*64,restored_digest='c'*64)
        for name,value in (('configuration_value',config),('_read_image',{}),
                           ('compare_restore_images',self.result),('verify_file',{})):
            mock=patch('mta.runtime.operational_backup.'+name,return_value=value)
            setattr(self,name,mock.start());self.addCleanup(mock.stop)

    def test_exact_receipt_checks_dump_and_complete_images(self):
        self.assertEqual(verify_backup(self.backup),self.result)
        self.verify_file.assert_called_once_with('/owned',dict(relative_path='backup/post.dump',
            sha256='a'*64,size_bytes=20))
        self.assertEqual(self._read_image.call_count,2)

    def test_rejects_changed_dump(self):
        self.verify_file.side_effect=ValueError('changed dump')
        with self.assertRaisesRegex(ValueError,'changed dump'):verify_backup(self.backup)
        self._read_image.assert_not_called()

    def test_rejects_wrong_database_tool_and_qualification(self):
        for field,value in (('database_name','another_database'),('tool_sha256','d'*64),
                            ('restore_target','fresh_cohort2_restore_wrong_attempt'),
                            ('qualification','unapproved-policy')):
            with self.subTest(field=field):
                old=getattr(self.backup,field);setattr(self.backup,field,value)
                with self.assertRaisesRegex(ValueError,'ownership'):verify_backup(self.backup)
                setattr(self.backup,field,old)
        self._read_image.assert_not_called()

    def test_rejects_wrong_operation_or_file(self):
        for owner,field,value in ((self.backup.operation,'group','O7'),
                (self.backup.operation,'source_digest','d'*64),
                (self.backup.file,'operation_id',2),(self.backup.file,'relative_path','other.dump'),
                (self.backup.file,'role','report')):
            with self.subTest(field=field):
                old=getattr(owner,field);setattr(owner,field,value)
                with self.assertRaisesRegex(ValueError,'ownership'):verify_backup(self.backup)
                setattr(owner,field,old)
        self._read_image.assert_not_called()

    def test_rejects_changed_logical_receipt(self):
        self.backup.restored_digest='d'*64
        with self.assertRaisesRegex(ValueError,'logical proof differs'):verify_backup(self.backup)


class BackupRuntimeProtocol(unittest.TestCase):
    run_day=fixture.TemporalPersistenceTest.run_day
    calculate=fixture.TemporalPersistenceTest.calculate

    def test_real_dump_restore_and_truthful_operation(self):
        if os.environ.get('VF_COHORT2_REAL_BACKUP_PROOF')!='1':
            self.skipTest('Explicit owned real-backup proof invocation required')
        fixture.TemporalPersistenceTest.setUp(self)
        flags=override_settings(VF_MTA_DAILY_PUBLICATION=False,VF_OPERATIONAL_UNLEASED_TESTS=True)
        flags.enable();self.addCleanup(flags.disable)
        self.opening['identity']='backup-protocol-'+uuid.uuid4().hex
        run=self.run_day();calls=len(self.seen)
        from django.db import connection
        database=connection.settings_dict['NAME']
        self.assertEqual(database,'fresh_cohort2_protocol_20261008_001')
        config=register_configuration(source_digest=digest(BACKUP_OPERATION),
            bindings=dict(operation_roster=[dict(ordinal=0,group='O8',**BACKUP_OPERATION)],
                postgres_backup=dict(source_database=database,pg_dump_path='/usr/local/bin/pg_dump',
                    pg_dump_sha256='b24e777de7beeb22f41c8233285c7f15c5c936739a38330bd780ea7252865cfe',
                    pg_restore_path='/usr/local/bin/pg_restore',
                    pg_restore_sha256='a3fbe6a9f8b13d451ac94a720c72cade1dc1261a9a50604fe4c90aa7d233c285',qualification=RUNTIME_POLICY)),
            settings=[dict(ordinal=i,name=name,value='1') for i,name in enumerate((
                'DoPostBkpImporter','DoPostBkpDBM','DoPostBkpBPR','DoPostBkpBTR','DBBkpCompress'))],tables=[],alerts=[])
        root=Path(os.environ['VF_COHORT2_BACKUP_PROOF_ROOT']);root.mkdir(parents=True,exist_ok=False)
        owner=start_attempt(run_id=run.pk,configuration_id=config.pk,request_key=uuid.uuid4().hex,
                            owned_root=root,expected_output_digest=run.output_digest)
        receipt=dict(run_id=str(run.pk),attempt_id=str(owner.pk),root=owner.root,
                     source_database=database,status='STARTED')
        try:
            effect=materialize_backup(owner.pk)
            verify_files(effect)
            backup=effect.backups.get()
            receipt['comparison']=verify_backup(backup)
            receipt['restore_target']=backup.restore_target
            receipt['status']='PASS'
        except Exception as error:
            owner.refresh_from_db()
            receipt.update(status='FAIL',error=type(error).__name__+': '+str(error),
                           attempt_status=owner.status)
            if owner.operations.exists() and owner.operations.get().backups.exists():
                backup=owner.operations.get().backups.get()
                receipt.update(restore_target=backup.restore_target,restore_status=backup.restore_status,
                    logical_digest=backup.logical_digest,restored_digest=backup.restored_digest)
            raise
        finally:
            receipt['additional_calculation_calls']=len(self.seen)-calls
            with (root/'receipt.json').open('x',encoding='utf-8') as stream:
                json.dump(receipt,stream,indent=2)
            self.assertEqual(len(self.seen),calls)
