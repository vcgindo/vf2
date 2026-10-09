"""Owned restore boundaries without engine or business-day invocation."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock,patch
from contextlib import ExitStack
from types import SimpleNamespace
import uuid
from django.test import SimpleTestCase
from mta.runtime.owned_restore import OwnedRestore,bind_restore,POLICY


class OwnedRestoreTests(SimpleTestCase):
    def test_native_network_values_keep_family_address_and_prefix(self):
        from ipaddress import ip_address,ip_interface,ip_network
        from mta.application.operational_pg_backup import _value
        self.assertEqual(_value(ip_address('127.0.0.1')),['IPv4Address','127.0.0.1'])
        self.assertEqual(_value(ip_address('::1')),['IPv6Address','::1'])
        self.assertNotEqual(_value(ip_interface('10.0.0.1/24')),_value(ip_interface('10.0.0.1/25')))
        self.assertEqual(_value(ip_network('10.0.0.0/24')),['IPv4Network','10.0.0.0/24'])
        with self.assertRaises(ValueError):_value(object())

    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'private.json'
        self.path.write_text(json.dumps(dict(user='restore_fixture',password='fixture-secret')))
        self.namespace=dict(registration_digest='a'*64,database_oid=10,owner_oid=11,
            database_name='source_fixture',owner_role='owner_fixture',issuer_role='issuer_fixture',issuer_oid=12)
        self.binding=dict(policy=POLICY,registration_digest='a'*64,database_oid=10,owner_oid=11,
            provisioner_oid=20,provisioner_role='restore_fixture',credential_file=str(self.path))
        self.database=dict(NAME='source_fixture',USER='issuer_fixture',HOST='owned',PORT='5432')
        self.restore=OwnedRestore(self.binding,self.namespace,self.database)
        self.role=(20,'restore_fixture',True,False,True,False,False,False,False,True)

    def admin(self,role=None,membership=None,source=None):
        admin=MagicMock()
        admin.execute.side_effect=[MagicMock(fetchone=MagicMock(return_value=self.role if role is None else role)),
            MagicMock(fetchone=MagicMock(return_value=membership)),
            MagicMock(fetchone=MagicMock(return_value=(10,11,False) if source is None else source))]
        return admin

    def test_minimum_provisioner_and_exact_source(self):
        self.restore.authorize(self.admin(),'fresh_cohort2_restore_fixture','source_fixture')

    def test_role_identity_privileges_memberships_and_source_access_deny(self):
        for index,value in ((0,99),(1,'other'),(2,False),(3,True),(4,False),(5,True),(6,True),(7,True),(8,True),(9,False)):
            role=list(self.role);role[index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):
                self.restore.authorize(self.admin(role=tuple(role)),'fresh_cohort2_restore_fixture','source_fixture')
        for options in (dict(membership=(1,)),dict(source=(10,11,True)),dict(source=(99,11,False)),dict(source=(10,99,False))):
            with self.subTest(options=options),self.assertRaises(ValueError):
                self.restore.authorize(self.admin(**options),'fresh_cohort2_restore_fixture','source_fixture')

    def test_binding_shape_provenance_and_credential_identity_deny(self):
        for name,value in (('registration_digest','b'*64),('database_oid',99),('owner_oid',99),('policy','other'),('extra',True)):
            changed={**self.binding,name:value}
            with self.subTest(name=name),self.assertRaises(ValueError):OwnedRestore(changed,self.namespace,self.database)
        self.path.write_text(json.dumps(dict(user='issuer_fixture',password='fixture')))
        with self.assertRaises(ValueError):OwnedRestore(self.binding,self.namespace,self.database)

    def test_source_and_target_session_identity(self):
        connection=MagicMock()
        connection.execute.return_value.fetchone.return_value=(10,11,'source_fixture','owner_fixture','issuer_fixture')
        self.restore.verify_source(connection)
        connection.execute.return_value.fetchone.return_value=(10,11,'source_fixture','owner_fixture','admin')
        with self.assertRaises(ValueError):self.restore.verify_source(connection)
        self.restore.target_oid=30
        connection.execute.return_value.fetchone.return_value=(30,20,'target','restore_fixture','restore_fixture')
        self.restore.verify_target(connection,'target')
        connection.execute.return_value.fetchone.return_value=(31,20,'target','restore_fixture','restore_fixture')
        with self.assertRaises(ValueError):self.restore.verify_target(connection,'target')

    def test_source_namespace_verification_precedes_credential_use(self):
        receipt={'owned_namespace':self.namespace}
        with patch('mta.mdm.owned_namespace.verify_binding') as verified:
            result=bind_restore(self.binding,'source_fixture',receipt,self.database)
            verified.assert_called_once_with(receipt)
            self.assertEqual(result.params['user'],'restore_fixture')
            with self.assertRaises(ValueError):
                bind_restore(self.binding,'source_fixture',receipt,{**self.database,'USER':'admin'})

    def test_public_acl_is_checked_before_enabling_target(self):
        admin=MagicMock()
        admin.execute.side_effect=[MagicMock(fetchone=MagicMock(return_value=(30,20))),MagicMock(),MagicMock(fetchone=MagicMock(return_value=None)),MagicMock()]
        self.restore.created(admin,'target')
        self.assertEqual(self.restore.receipt('target')['target_owner_oid'],20)
        self.assertIn('REVOKE ALL',str(admin.execute.call_args_list[1]))
        self.assertIn('ALLOW_CONNECTIONS true',str(admin.execute.call_args_list[-1]))
        admin=self.admin();admin.execute.side_effect=[MagicMock(fetchone=MagicMock(return_value=(30,20))),MagicMock(),MagicMock(fetchone=MagicMock(return_value=(1,)))]
        with self.assertRaises(ValueError):self.restore.created(admin,'target')
        self.assertEqual(admin.execute.call_count,3)

    def test_restore_failure_retains_failed_receipt_in_both_paths(self):
        from mta.runtime import operational_backup as backup
        for opt_in in (False,True):
            with self.subTest(owned=opt_in),ExitStack() as stack:
                owner=SimpleNamespace(pk=uuid.uuid4(),run=SimpleNamespace(
                    mdm_input_capture=SimpleNamespace(source=SimpleNamespace(receipt={}))),
                    configuration=object(),status='RUNNING',run_output_digest='o',
                    action_digest='a',source_digest='s',root='/fixture')
                options=dict(source_database='fresh_complete',pg_dump_path='/dump',pg_dump_sha256='d',
                    pg_restore_path='/restore',pg_restore_sha256='r',qualification=None)
                if opt_in:options['owned_restore']=self.binding
                config=dict(bindings=dict(postgres_backup=options,operation_roster=[dict(group='O8',**backup.BACKUP_OPERATION)]),settings=[dict(name=n,value='1') for n in ('DoPostBkpImporter','DoPostBkpDBM','DoPostBkpBPR','DoPostBkpBTR','DBBkpCompress')])
                stack.enter_context(patch.object(backup.OperationalAttempt.objects,'select_related')).return_value.get.return_value=owner
                stack.enter_context(patch.object(backup,'configuration_value',return_value=config))
                stack.enter_context(patch.object(backup,'_identity',return_value=dict(output_digest='o',action_digest='a',source_digest='s')))
                stack.enter_context(patch.object(backup,'connection',settings_dict=dict(NAME='fresh_complete',HOST='host',PORT='5432',USER='issuer',PASSWORD='secret')))
                stack.enter_context(patch('mta.runtime.owned_restore.bind_restore',return_value=self.restore))
                context=stack.enter_context(patch.object(backup,'operation'));context.return_value.__enter__.return_value=object()
                stack.enter_context(patch.object(backup,'dump_database',return_value=dict(file={'relative_path':'backup/post.dump'},logical_image={},snapshot='snapshot',logical_digest='l')))
                stack.enter_context(patch.object(backup,'record_file'))
                stack.enter_context(patch.object(backup,'_write_image'))
                save=stack.enter_context(patch.object(backup,'_save_backup'))
                restore=stack.enter_context(patch.object(backup,'restore_database',side_effect=RuntimeError('injected restore failure')))
                with self.assertRaisesRegex(RuntimeError,'injected restore failure'):backup.materialize_backup(owner.pk)
                self.assertEqual(save.call_args.kwargs,{'restore_status':'FAILED'})
                self.assertEqual('ownership' in restore.call_args.kwargs,opt_in)
