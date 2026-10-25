"""The live-reference upgrade is pinned to one approved retained namespace."""
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
from mta.runtime import scoped_read_transition as upgrade


class ScopedReadTransitionTests(unittest.TestCase):
    def test_packaged_lf_migration_bytes_are_exact(self):
        root=Path(__file__).resolve().parents[1]/'mta/runtime/migrations'
        for name,checksum in upgrade.PINS:
            self.assertEqual(hashlib.sha256((root/(name+'.py')).read_bytes()).hexdigest(),checksum)

    def specification(self):
        return dict(initialization_id=upgrade.INITIALIZATION,migration_pins=upgrade.migration_pins(),
            previous_release=dict(source_commit=upgrade.PREVIOUS_COMMIT,manifest_sha256=upgrade.PREVIOUS_RELEASE),
            catalogue_delta={})

    def test_unqualified_delta_and_other_source_or_owner_are_denied(self):
        spec=self.specification()
        with self.assertRaises(ValueError):upgrade.require_specification(spec)
        with patch.object(upgrade,'DELTA',upgrade.digest({})):
            upgrade.require_specification(spec)
            for key in ('initialization_id','migration_pins'):
                with self.subTest(key=key),self.assertRaises(ValueError):
                    upgrade.require_specification(dict(spec,**{key:'other'}))
            with self.assertRaises(ValueError):upgrade.require_specification(dict(spec,
                previous_release=dict(spec['previous_release'],source_commit='0'*40)))
            with self.assertRaises(ValueError):upgrade.require_specification(dict(spec,catalogue_delta={'extra':'grant'}))

    def test_receipt_binds_both_catalogues_and_original_authority(self):
        receipt=dict(initialization_id=upgrade.INITIALIZATION,migration_pins=upgrade.migration_pins(),
            previous_release=upgrade.PREVIOUS_RELEASE,before_schema_digest=upgrade.BEFORE_SCHEMA,
            before_guard_digest=upgrade.BEFORE_GUARD,schema_digest=upgrade.AFTER_SCHEMA,
            catalogue_delta_digest=upgrade.DELTA)
        self.assertTrue(upgrade.approved_receipt(receipt))
        for key in receipt:
            with self.subTest(key=key):self.assertFalse(upgrade.approved_receipt(dict(receipt,**{key:'changed'})))

    def test_authority_accepts_only_the_two_named_additional_migrations(self):
        from mta.runtime.ingestion_authority import validate_schema_transition,SCHEMA_FIELDS,SCHEMA_CONTRACT
        value={key:'a'*64 for key in SCHEMA_FIELDS}
        value.update(contract=SCHEMA_CONTRACT,initialization_id=upgrade.INITIALIZATION,
            target_commit='b'*40,migration_pins=upgrade.migration_pins())
        self.assertEqual(validate_schema_transition(value),value)
        for name in ('0227_arbitrary','0228_other','0229_scope_read_action_ownership'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                validate_schema_transition(dict(value,migration_pins=[[name,'c'*64]]))


if __name__=='__main__':unittest.main()
