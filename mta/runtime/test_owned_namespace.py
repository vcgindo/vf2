"""Focused catalogue and receipt checks for the fresh owned namespace guard."""
from copy import deepcopy
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mta.mdm import owned_namespace as owned


def role(oid, name, *, login=False):
    return dict(oid=oid,name=name,can_login=login,superuser=False,create_db=False,
                create_role=False,replication=False,bypass_rls=False)


class OwnedNamespaceTests(SimpleTestCase):
    def setUp(self):
        self.owner=role(10,'fresh_c6_owner')
        self.issuer=role(11,'fresh_c6_issuer',login=True)
        self.consumer=role(12,'fresh_c6_reader',login=True)
        self.acceptor=role(13,owned.ACCEPTOR_ROLE)
        self.registrar=role(14,owned.REGISTRAR_ROLE)
        self.database=dict(oid=20,name='fresh_c6_exact',owner=self.owner,
                           current_user_oid=10,session_user_oid=11)
        self.registration=dict(registration_id='11111111-1111-1111-1111-111111111111',
            policy=owned.POLICY,database_oid=20,database_name='fresh_c6_exact',
            owner_oid=10,issuer_oid=11,consumer_oid=12,acceptor_oid=13,
            artifact_sha256='a'*64,adapter_sha256='b'*64,
            owner=self.owner,issuer=self.issuer,consumer=self.consumer,
            acceptor=self.acceptor,registrar=self.registrar)
        self.evidence=dict(owner_members=[11],acceptor_members=[11],registrar_members=[],
            owner_roles=[],issuer_roles=[10,13],consumer_roles=[],acceptor_roles=[],
            registrar_roles=[],acl=dict(count=0,issuer_connect=True,consumer_connect=True))

    def test_exact_catalogue_and_actor_produce_bound_receipt(self):
        result=owned._validate(self.database,self.registration,self.evidence,
            artifact_sha256='a'*64,adapter_sha256='b'*64,installer=True)
        self.assertEqual(result['database_oid'],20)
        self.assertEqual(result['owner_role'],'fresh_c6_owner')
        self.assertEqual(result['acceptor_role'],owned.ACCEPTOR_ROLE)
        self.assertEqual(result['registrar_role'],owned.REGISTRAR_ROLE)
        self.assertEqual(len(result['registration_digest']),64)

    def test_database_role_actor_membership_and_grant_drift_deny(self):
        changes=(
            ('database',lambda db,reg,proof:db.update(oid=21)),
            ('login_owner',lambda db,reg,proof:reg['owner'].update(can_login=True)),
            ('issuer_actor',lambda db,reg,proof:db.update(session_user_oid=12)),
            ('extra_owner_member',lambda db,reg,proof:proof.update(owner_members=[11,13])),
            ('consumer_membership',lambda db,reg,proof:proof.update(consumer_roles=[13])),
            ('missing_acceptor_membership',lambda db,reg,proof:proof.update(acceptor_members=[])),
            ('acceptor_login',lambda db,reg,proof:reg['acceptor'].update(can_login=True)),
            ('acceptor_name',lambda db,reg,proof:reg['acceptor'].update(name='forged_acceptor')),
            ('registrar_member',lambda db,reg,proof:proof.update(registrar_members=[11])),
            ('forged_registry_owner',lambda db,reg,proof:reg.update(registrar=deepcopy(reg['owner']))),
            ('public_or_extra_acl',lambda db,reg,proof:proof['acl'].update(count=1)),
            ('missing_connect',lambda db,reg,proof:proof['acl'].update(consumer_connect=False)),
            ('artifact',lambda db,reg,proof:reg.update(artifact_sha256='c'*64)),
        )
        for name,change in changes:
            database=deepcopy(self.database);registration=deepcopy(self.registration)
            evidence=deepcopy(self.evidence);change(database,registration,evidence)
            with self.subTest(name=name),self.assertRaises(ValueError):
                owned._validate(database,registration,evidence,
                    artifact_sha256='a'*64,adapter_sha256='b'*64,installer=True)

    def test_only_exact_legacy_names_bypass_registration(self):
        for name in ('daily_3006','test_freshvcf'):
            database={**self.database,'name':name}
            cursor=MagicMock()
            context=MagicMock();context.__enter__.return_value=cursor
            database_connection=MagicMock(in_atomic_block=True);database_connection.cursor.return_value=context
            with self.subTest(name=name),patch.object(owned,'connection',database_connection),\
                    patch.object(owned,'_database_identity',return_value=database),\
                    patch.object(owned,'_registered_identity') as registered:
                self.assertEqual(owned.authorize_install('a'*64,'b'*64),
                                 dict(database_name=name,registration=None))
                registered.assert_not_called()
                cursor.execute.assert_not_called()
        self.assertNotIn('daily_3006_copy',owned.LEGACY_DATABASES)

    def test_install_guard_requires_transaction(self):
        database_connection=MagicMock(in_atomic_block=False)
        with patch.object(owned,'connection',database_connection),\
                self.assertRaisesRegex(ValueError,'requires one transaction'):
            owned.authorize_install('a'*64,'b'*64)
        database_connection.cursor.assert_not_called()

    def test_fresh_installer_derives_and_quotes_catalogue_owner(self):
        hostile={**self.database,'owner':{**self.owner,'name':'owner"quoted'}}
        live={**hostile,'current_user_oid':10,'session_user_oid':11}
        registration={**self.registration,'owner':hostile['owner']}
        cursor=MagicMock();context=MagicMock();context.__enter__.return_value=cursor
        database_connection=MagicMock(in_atomic_block=True);database_connection.cursor.return_value=context
        with patch.object(owned,'connection',database_connection),\
                patch.object(owned,'_database_identity',side_effect=[hostile,live]),\
                patch.object(owned,'_registered_identity',return_value=registration),\
                patch.object(owned,'_catalogue_evidence',return_value=self.evidence):
            result=owned.authorize_install('a'*64,'b'*64)
        self.assertEqual(result['registration']['owner_role'],'owner"quoted')
        cursor.execute.assert_called_once_with('SET LOCAL ROLE "owner""quoted"')

    def test_runtime_binding_rechecks_live_identity_without_owner_actor(self):
        expected=owned._receipt_identity(self.registration)
        reader={**self.database,'current_user_oid':12,'session_user_oid':12}
        cursor=MagicMock();context=MagicMock();context.__enter__.return_value=cursor
        database_connection=MagicMock(in_atomic_block=True);database_connection.cursor.return_value=context
        receipt={'owned_namespace':expected}
        with patch.object(owned,'connection',database_connection),\
                patch.object(owned,'_database_identity',return_value=reader),\
                patch.object(owned,'_registered_identity',return_value=self.registration),\
                patch.object(owned,'_catalogue_evidence',return_value=self.evidence):
            self.assertIs(owned.verify_binding(receipt),receipt)
            changed=deepcopy(receipt);changed['owned_namespace']['database_name']='copied'
            with self.assertRaisesRegex(ValueError,'receipt registration differs'):
                owned.verify_binding(changed)

    def test_missing_runtime_binding_denies(self):
        for receipt in ({},{'owned_namespace':None}):
            with self.assertRaisesRegex(ValueError,'receipt binding is absent'):
                owned.verify_binding(receipt)
