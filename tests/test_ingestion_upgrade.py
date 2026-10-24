"""Focused baseline-origin and immutable-authority compatibility checks.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import os
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
os.environ.setdefault('VF_SECRET_KEY','ingestion-upgrade-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.runtime import ingestion_upgrade as upgrade
from mta.serialization import digest


class UpgradeOriginTests(unittest.TestCase):
    def capability(self):
        return dict(release_identity=deepcopy(upgrade.BASELINE_IDENTITY),
            profile_digest=upgrade.BASELINE_PROFILE,
            implementation_sha256=upgrade.BASELINE_IDENTITY['implementation_sha256'])

    def test_only_exact_baseline_origin_is_supported(self):
        capability=self.capability()
        self.assertEqual(upgrade.baseline(capability),capability)
        for key in upgrade.BASELINE_IDENTITY:
            altered=deepcopy(capability);altered['release_identity'][key]='x'
            with self.assertRaises(ValueError):upgrade.baseline(altered)
        for key in ('profile_digest','implementation_sha256'):
            altered=deepcopy(capability);altered[key]='0'*64
            with self.assertRaises(ValueError):upgrade.baseline(altered)

    def test_audit_scope_cannot_leak_or_borrow_another_source(self):
        capability=self.capability()
        source=SimpleNamespace(receipt={'opening':'original'})
        source.digest=digest(source.receipt)
        owner=SimpleNamespace(source=source)
        self.assertFalse(upgrade.audited_capability(capability))
        with upgrade.auditing(owner,{'namespace':'original'},capability):
            self.assertTrue(upgrade.audited_capability(capability))
            self.assertEqual(upgrade.implementation_for(source),capability['implementation_sha256'])
            foreign=SimpleNamespace(receipt={'opening':'foreign'},digest='f'*64)
            with self.assertRaisesRegex(ValueError,'source differs'):upgrade.implementation_for(foreign)
            seal=SimpleNamespace(receipt=deepcopy(upgrade.BASELINE_EXECUTION))
            seal.digest=digest(seal.receipt)
            self.assertEqual(upgrade.execution_for(source,seal),upgrade.BASELINE_EXECUTION)
            seal.receipt['adapter_digest']='0'*64;seal.digest=digest(seal.receipt)
            with self.assertRaisesRegex(ValueError,'producer differs'):upgrade.execution_for(source,seal)
        self.assertFalse(upgrade.audited_capability(capability))

    def test_older_origin_requires_live_joined_activation(self):
        source=SimpleNamespace(implementation_digest=upgrade.BASELINE_IDENTITY['implementation_sha256'])
        with patch('mta.mdm.initialization.current_implementation_digest',return_value='a'*64), \
             patch('mta.runtime.ingestion_admission._process_release',side_effect=ValueError('No release authority')):
            with self.assertRaisesRegex(ValueError,'No release authority'):
                upgrade.implementation_for(source)

    def test_current_release_keeps_original_strict_path(self):
        source=SimpleNamespace(implementation_digest='a'*64)
        with patch('mta.mdm.initialization.current_implementation_digest',return_value='a'*64), \
             patch('mta.mdm.initialization.implementation_digest',return_value='a'*64) as strict:
            self.assertEqual(upgrade.implementation_for(source),'a'*64)
            strict.assert_called_once()


class CertifiedFreshOriginTests(unittest.TestCase):
    def test_fresh_certified_origin_transition_keeps_pinned_old_bridge_and_manifest_denial(self):
        from mta.runtime.ingestion_admission import _origin_transition,BASELINE_RELEASE,BASELINE_MANIFEST
        body=dict(original_commit='1'*40,target_commit='2'*40,original_release='a'*64,target_release='b'*64)
        _origin_transition(body,dict(release_digest='a'*64))
        with self.assertRaisesRegex(ValueError,'Unreviewed'):
            _origin_transition(body,dict(release_digest='c'*64))
        with self.assertRaisesRegex(ValueError,'Same-commit'):
            _origin_transition(dict(body,target_commit='1'*40),dict(release_digest='a'*64))
        _origin_transition(dict(body,original_commit=BASELINE_RELEASE,original_release=BASELINE_MANIFEST),
                           dict(release_digest='c'*64))

    def fixture(self):
        from uuid import UUID
        owner=SimpleNamespace(pk=UUID('179dbb4c-77d9-40bf-8c84-d5f05858dd07'))
        namespace=UUID('7b225ea3-d47a-447e-be5c-1a34df9e2a4a')
        original=dict(registration_id=str(namespace),database_name='owned',database_oid=42,
                      adapter_sha256='a'*64,artifact_sha256='b'*64)
        old=dict(source_commit='1'*40,manifest_sha256='c'*64,implementation_sha256='a'*64)
        capability=dict(release_identity=old,implementation_sha256='a'*64,receipt_digest='d'*64)
        source=SimpleNamespace(pk=9,implementation_digest='a'*64,
            receipt=dict(owned_namespace={**capability,'artifact_sha256':'b'*64}))
        source.digest=digest(source.receipt)
        release=dict(source_commit='2'*40,manifest_sha256='e'*64)
        cert=dict(initialization_id=owner.pk,namespace=namespace,database_name='owned',database_oid=42,
            source_digest=source.digest,release_digest='c'*64,receipt_digest='f'*64,
            populations=dict(integration='3'*64))
        authority=dict(initialization_id=str(owner.pk),namespace=str(namespace),database_name='owned',database_oid=42,source_digest=source.digest,
            original_commit='1'*40,original_release='c'*64,target_commit='2'*40,target_release='e'*64,
            original_registration_digest=digest(original),original_capability_digest='d'*64,certification_digest='f'*64)
        return source,owner,release,original,capability,cert,authority

    def resolve(self,values):
        source,owner,release,original,capability,cert,authority=values
        with patch('mta.runtime.ingestion_admission._certificate',return_value=cert), \
                patch('mta.runtime.ingestion_authority.read',return_value=authority):
            return upgrade._certified_origin(None,source,owner,release,original,capability)

    def test_exact_original_source_and_live_target_authority_required(self):
        values=self.fixture()
        self.assertEqual(self.resolve(values)['integration_digest'],'3'*64)
        for key in values[-1]:
            changed=deepcopy(values);changed[-1][key]='foreign'
            with self.subTest(key=key),self.assertRaises(ValueError):self.resolve(changed)
        for key in ('initialization_id','namespace','database_name','database_oid','source_digest','release_digest','receipt_digest'):
            changed=deepcopy(values);changed[-2][key]='foreign'
            with self.subTest(certificate=key),self.assertRaises(ValueError):self.resolve(changed)
        for index,key in ((0,'implementation_digest'),(3,'adapter_sha256'),(4,'implementation_sha256')):
            changed=deepcopy(values)
            if index==0:setattr(changed[0],key,'0'*64)
            else:changed[index][key]='0'*64
            with self.assertRaises(ValueError):self.resolve(changed)

    def test_original_integration_must_match_certificate_source_and_corrected_version(self):
        from mta.mdm.location_projection import VERSION
        source=SimpleNamespace(pk=9)
        seal=SimpleNamespace(source_id=9,receipt=dict(adapter_digest='a'*64,source_manifest_digest='b'*64,
                                                     closing_projection_version=VERSION))
        seal.digest=digest(seal.receipt)
        origin=dict(integration_digest=seal.digest)
        with patch.object(upgrade,'_origin',return_value=origin):
            self.assertEqual(upgrade.execution_for(source,seal),seal.receipt)
            seal.source_id=10
            with self.assertRaises(ValueError):upgrade.execution_for(source,seal)
            seal.source_id=9;seal.receipt['adapter_digest']='c'*64
            with self.assertRaises(ValueError):upgrade.execution_for(source,seal)
            seal.digest=digest(seal.receipt)
            with self.assertRaises(ValueError):upgrade.execution_for(source,seal)
