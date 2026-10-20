"""Ownership/compatibility contract tests. No engine or database execution."""
import os
import unittest
from dataclasses import replace
from uuid import uuid4
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'ingestion-contract-tests')
import django
django.setup()
from mta.runtime.ingestion_context import (DataOwner, RevisionCut, PopulationReference,
    PreparedRunInputs, master_field_owner, CONTRACT)
from mta.runtime.ingestion_ownership import domain
from mta.runtime import ingestion_authority as authority
from mta.runtime import ingestion_admission as admission


class OwnershipContractTests(unittest.TestCase):
    def setUp(self):
        self.ref = PopulationReference(DataOwner.MASTER, 'INITIALIZATION', str(uuid4()),
            'input/opening/state/MasterData', 'typed-v1', 10, 'a'*64)
        self.context = PreparedRunInputs(str(uuid4()), 'a'*64, 'b'*64, str(uuid4()), 'c'*64,
            str(uuid4()), 'd'*64, None, None, 'e'*64, RevisionCut(0,0,0,0,0), (self.ref,))

    def test_explicit_ownership_keeps_norm_out_of_static_masters(self):
        for name, owner in (('Norm', DataOwner.OPERATIONAL), ('MinNorm', DataOwner.CONFIGURATION),
                            ('RLT', DataOwner.CONFIGURATION), ('Weight', DataOwner.MASTER)):
            self.assertEqual(master_field_owner(name), owner)
        with self.assertRaises(ValueError): master_field_owner('future_field')
        self.assertEqual(domain('mta', 'fresh_mta_mdmskuloccurrent'), 'mixed')
        self.assertEqual(domain('mta_state', 'input_any_feed'), 'fact')
        self.assertEqual(domain('mta_opening', 'any_population'), 'immutable')
        for table in ('mdmsobraw','mdmmoqraw1','mdmmoqraw2','mdmpairexclusionsource','mdmpairexclusion'):
            self.assertEqual(domain('mta','fresh_mta_'+table),'configuration')
        for table in ('mdmskuapproved','mdmmoqwithdestinationapproved','mdmskulocremoveapproved'):
            self.assertEqual(domain('mta','fresh_mta_'+table),'action')
        with self.assertRaises(ValueError): domain('other_project', 'anything')
        from django.apps import apps
        from mta.runtime.ingestion_ownership import MASTER
        for model in apps.get_models():
            if model._meta.db_table in MASTER:
                for field in model._meta.fields:
                    master_field_owner(field.name)

    def test_frozen_context_and_complete_predecessor_binding(self):
        with self.assertRaises(Exception): self.context.batch_digest = 'x'
        with self.assertRaises(ValueError): replace(self.context, predecessor_id=str(uuid4()))
        with self.assertRaises(ValueError): replace(self.context, populations=(self.ref,self.ref))
        with self.assertRaises(ValueError): replace(self.context, batch_digest='wrong')
        with self.assertRaises(ValueError): RevisionCut(True,0,0,0,0)
        with self.assertRaises(ValueError): RevisionCut(-1,0,0,0,0)
        with self.assertRaises(ValueError): replace(self.ref, owner=DataOwner.OPERATIONAL, path='MasterData')
        with self.assertRaises(ValueError): replace(self.ref, path='../other')
        with self.assertRaises(ValueError): replace(self.ref, owner_id=uuid4())

    def test_release_authority_requires_exact_independent_identities(self):
        body = {key: 'a'*64 for key in authority.FIELDS}
        body.update(contract=CONTRACT, initialization_id=str(uuid4()), namespace=str(uuid4()),
            database_name='owned_test', database_oid=123, original_commit='b'*40, target_commit='c'*40)
        self.assertEqual(authority.validate(body), body)
        for change in ({'extra': True}, {'target_commit': 'short'}, {'database_oid': True},
                       {'contract': 'unknown'}, {'original_release': ''}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                authority.validate({**body, **change})
        from unittest.mock import MagicMock
        from mta.serialization import digest
        cursor=MagicMock()
        cursor.fetchone.return_value=(body,digest(body))
        self.assertEqual(authority.read(cursor,body['initialization_id'],body['target_release']),body)
        for initialization_id,target in ((str(uuid4()),body['target_release']),
                                         (body['initialization_id'],'0'*64)):
            with self.assertRaises(ValueError): authority.read(cursor,initialization_id,target)

    def test_process_release_verification_once_per_exact_pin_pair(self):
        admission._process_release.cache_clear()
        self.addCleanup(admission._process_release.cache_clear)
        actual = dict(source_commit='a'*40, manifest_sha256='b'*64)
        with patch('release.native_identity.require_current', return_value=actual) as verify:
            for _ in range(3): admission._process_release('a'*40, 'b'*64)
            self.assertEqual(verify.call_count, 1)
            with self.assertRaises(ValueError): admission._process_release('c'*40, 'b'*64)
            self.assertEqual(verify.call_count, 2)

    def test_uncertified_installation_keeps_full_verifier(self):
        from mta.mdm import source
        from django.test import override_settings
        from types import SimpleNamespace
        record = SimpleNamespace(receipt={'schema': 'fresh-production-mdm-source-v1'})
        with override_settings(VF_MDM_SOURCE_DIGEST='a'*64), \
                patch('mta.runtime.ingestion_admission.certified_source', return_value=None), \
                patch.object(source.MdmSource.objects, 'filter') as query, \
                patch('mta.mdm.native_source.require_base') as base, \
                patch('mta.mdm.integration_source.require_read_binding') as binding:
            query.return_value.first.return_value = record
            self.assertIs(source.source(read_only=True), record)
            self.assertEqual(base.call_count, 3)
            binding.assert_called_once_with(record, read_only=True)

    def test_certified_serving_does_not_call_old_full_opening_path(self):
        from mta.mdm import source
        from django.test import override_settings
        record = object()
        with override_settings(VF_MDM_SOURCE_DIGEST='a'*64), \
                patch('mta.runtime.ingestion_admission.certified_source', return_value=record), \
                patch('mta.mdm.native_source.require_base', side_effect=AssertionError('Opening scan')):
            self.assertIs(source.source(read_only=True), record)
        with override_settings(VF_MDM_SOURCE_DIGEST='a'*64), \
                patch('mta.runtime.ingestion_admission.certified_source', side_effect=ValueError('Corrupt cert')), \
                patch('mta.mdm.native_source.require_base', side_effect=AssertionError('Unsafe fallback')):
            with self.assertRaisesRegex(ValueError, 'Corrupt cert'): source.source(read_only=True)

    def test_certification_is_explicit_and_cannot_join_an_existing_writer(self):
        from mta.runtime.ingestion_certification import certify_current
        with patch.object(admission.connection, 'in_atomic_block', True):
            with self.assertRaisesRegex(ValueError, 'owns its complete audit'): certify_current(uuid4())

    def test_original_capability_requires_complete_producer_registration_chain(self):
        from mta.mdm import owned_namespace as owned
        from mta.serialization import digest
        from unittest.mock import MagicMock
        original={'adapter_sha256':'a'*64}
        original_receipt={'fixture':'original namespace'}
        release=dict(schema='vectorflow-native-release-source-v1',source_commit='b'*40,
            manifest_sha256='c'*64,source_files_digest='d'*64,migrations_digest='e'*64,
            implementation_sha256='a'*64)
        capability=dict(policy=owned.PRODUCTION_APPLICATION_POLICY,original_registration=original_receipt,
            original_implementation_sha256='a'*64,implementation_sha256='a'*64,release_identity=release,
            profile_digest='f'*64,objects_digest='1'*64,grants_digest='2'*64,schema_digest='3'*64)
        def validate(changes):
            body={**capability,**changes}
            body['receipt_digest']=digest(body)
            cursor=MagicMock()
            cursor.fetchone.return_value=(body,)
            return admission.registration(cursor)
        with patch.object(owned,'_registered_identity',return_value=original), \
                patch.object(owned,'_receipt_identity',return_value=original_receipt):
            self.assertEqual(validate({})[0],original)
            for change in ({'policy':'unsupported'}, {'original_registration':{}},
                    {'original_implementation_sha256':'4'*64}, {'implementation_sha256':'4'*64},
                    {'release_identity':{**release,'implementation_sha256':'4'*64}},
                    {'extra':'unsupported'}):
                with self.subTest(change=change),self.assertRaises(ValueError): validate(change)


class ReportGuardCompatibilityTests(unittest.TestCase):
    def test_only_independently_verified_revision_triggers_are_separated(self):
        from unittest.mock import MagicMock
        from importlib import import_module
        from mta.runtime.ingestion_ownership import business_trigger_rows
        rows=[('bor_original_guard','table','O'),('ingestion_watch_insert','table','O')]
        cursor=MagicMock()
        body=import_module('mta.runtime.migrations.0145_ingestion_revision_guards').SQL
        body=body.split('CREATE FUNCTION mta.ingestion_watch()',1)[1].split('AS $$',1)[1].split('$$;',1)[0]
        body=body.replace('UPDATE mta.fresh_mta_initializationcertification SET',
            'UPDATE mta.fresh_mta_ingestionrevisionstate SET').replace("WHERE status='CERTIFIED';",
            "WHERE initialization_id IN (SELECT initialization_id FROM mta.fresh_mta_initializationcertification WHERE status='CERTIFIED');")
        cursor.fetchall.return_value=[(body,True,['search_path=pg_catalog, mta'],'trigger')]
        with patch('mta.runtime.ingestion_ownership.require_guard_coverage') as verify:
            self.assertEqual(business_trigger_rows(cursor,rows),rows[:1])
            verify.assert_called_once_with(cursor)
        with patch('mta.runtime.ingestion_ownership.require_guard_coverage',side_effect=ValueError('wrong binding')):
            with self.assertRaisesRegex(ValueError,'wrong binding'):business_trigger_rows(cursor,rows)
        cursor.fetchall.return_value=[('replaced',True,['search_path=pg_catalog, mta'],'trigger')]
        with patch('mta.runtime.ingestion_ownership.require_guard_coverage'):
            with self.assertRaisesRegex(ValueError,'function contract'):business_trigger_rows(cursor,rows)
        untouched=[('unexpected_business_guard','table','O')]
        self.assertEqual(business_trigger_rows(cursor,untouched),untouched)
