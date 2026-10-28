"""Finite SQL change and safe migration transition contract."""
from importlib import import_module
import unittest
from unittest.mock import MagicMock


class TransitSettingsGuardMigrationTests(unittest.TestCase):
    def setUp(self):
        self.migration = import_module('mta.runtime.migrations.0241_scope_transit_settings_owners')

    def test_only_owner_predicate_changes(self):
        m = self.migration
        self.assertEqual(m.SQL.replace(m.OWNERS, m.MARKER), m.prior.SQL)
        self.assertIn("AND R.predecessor_id IS NULL", m.OWNERS)
        self.assertIn("A.id=R.predecessor_id", m.OWNERS)
        self.assertIn("C.source_id=P.source_id AND C.status='CONSUMED'", m.OWNERS)
        self.assertTrue(m.OWNERS.endswith(') IS NOT TRUE'))

    def test_install_requires_exact_prior_body(self):
        m = self.migration
        editor = MagicMock()
        cursor = editor.connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [('altered',)]
        with self.assertRaisesRegex(ValueError, 'no replacement'):
            m.install(None, editor)
        self.assertEqual(cursor.execute.call_count, 1)
        cursor.fetchall.return_value = [(m.body(m.prior.SQL),)]
        m.install(None, editor)
        self.assertTrue(cursor.execute.call_args.args[0].startswith('CREATE OR REPLACE FUNCTION'))

    def test_reverse_retains_accepted_native_owners(self):
        editor = MagicMock()
        editor.connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
        with self.assertRaisesRegex(ValueError, 'forward release'):
            self.migration.reverse(None, editor)

    def test_transition_requires_exact_predecessor_migration_and_delta(self):
        from copy import deepcopy
        from mta.runtime import transit_settings_schema_transition as transition
        from mta.serialization import digest
        spec = dict(previous_release=dict(source_commit=transition.PREVIOUS_COMMIT,
            manifest_sha256=transition.PREVIOUS_RELEASE), migration_pins=transition.migration_pins(),
            catalogue_delta=transition.catalogue_delta())
        transition.require_specification(spec)
        receipt = dict(migration_pins=spec['migration_pins'], previous_release=transition.PREVIOUS_RELEASE,
                       catalogue_delta_digest=digest(spec['catalogue_delta']))
        self.assertTrue(transition.approved_receipt(receipt))
        for key in ('migration_pins','previous_release','catalogue_delta_digest'):
            changed=deepcopy(receipt);changed[key]=[] if key=='migration_pins' else '0'*64
            self.assertFalse(transition.approved_receipt(changed))
        changed=deepcopy(spec);changed['catalogue_delta']={}
        with self.assertRaises(ValueError):transition.require_specification(changed)

    def test_schema_authority_accepts_only_exact_new_migration_name(self):
        from uuid import uuid4
        from mta.runtime import ingestion_authority as authority
        from mta.runtime import transit_settings_schema_transition as transition
        body={key:'a'*64 for key in authority.SCHEMA_FIELDS}
        body.update(contract=authority.SCHEMA_CONTRACT,initialization_id=str(uuid4()),
            target_commit='b'*40,migration_pins=transition.migration_pins())
        self.assertEqual(authority.validate_schema_transition(body),body)
        body['migration_pins']=[['0241_arbitrary','a'*64]]
        with self.assertRaises(ValueError):authority.validate_schema_transition(body)

    def test_effective_schema_checks_new_receipt_and_ancestry(self):
        from uuid import uuid4
        from unittest.mock import patch
        from mta.runtime import ingestion_authority as authority,ingestion_admission as admission
        from mta.runtime import transit_settings_schema_transition as transition
        from mta.serialization import digest
        cert=dict(schema_digest='s0',guard_digest='g0',receipt_digest='r',release_digest=transition.PREVIOUS_RELEASE)
        origin={key:'fixed' for key in authority.FIELDS}
        origin.update(initialization_id=str(uuid4()),target_commit=transition.PREVIOUS_COMMIT,
                      target_release=transition.PREVIOUS_RELEASE)
        target=dict(origin,target_commit='1'*40,target_release='1'*64)
        link=dict(contract=authority.SCHEMA_CONTRACT,previous_release=origin['target_release'],
            previous_authority_digest=digest(origin),certification_digest='r',target_commit=target['target_commit'],
            migration_pins=transition.migration_pins(),catalogue_delta_digest=digest(transition.catalogue_delta(bootstrap=True)),
            before_schema_digest='s0',before_guard_digest='g0',schema_digest='s1',guard_digest='g1')
        with patch.object(admission,'_activation_metadata',return_value=cert), \
                patch.object(authority,'read',return_value=origin), \
                patch.object(authority,'read_schema_transition',side_effect=lambda c,b:link if b==target else None):
            self.assertEqual(admission.effective_schema(None,target)[2:4],('s1','g1'))
            link['catalogue_delta_digest']='tampered'
            with self.assertRaisesRegex(ValueError,'transit-owner'):
                admission.effective_schema(None,target)
