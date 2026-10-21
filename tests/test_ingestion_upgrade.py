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
