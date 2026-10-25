"""Exact migration and receipt pins; real catalogue proof lives with owned evidence."""
from pathlib import Path
import hashlib
import unittest
from mta.runtime import bpr_history_schema_transition as transition


class BprHistoryTransitionTests(unittest.TestCase):
    def test_migration_bytes_match_exact_allowlist(self):
        path = Path(__file__).resolve().parents[1] / 'mta/runtime/migrations' / (transition.MIGRATION_NAME + '.py')
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), transition.MIGRATION_SHA256)

    def test_receipt_rejects_changed_owner_source_catalogue_or_migration(self):
        receipt = dict(initialization_id=transition.INITIALIZATION, migration_pins=transition.migration_pins(),
            previous_release=transition.PREVIOUS_RELEASE, before_schema_digest=transition.BEFORE_SCHEMA,
            before_guard_digest=transition.BEFORE_GUARD, catalogue_delta_digest=transition.DELTA)
        self.assertTrue(transition.approved_receipt(receipt))
        for key in receipt:
            self.assertFalse(transition.approved_receipt(dict(receipt, **{key: 'changed'})))

    def test_arbitrary_delta_is_not_authority(self):
        spec = dict(initialization_id=transition.INITIALIZATION, migration_pins=transition.migration_pins(),
            previous_release=dict(source_commit=transition.PREVIOUS_COMMIT, manifest_sha256=transition.PREVIOUS_RELEASE),
            catalogue_delta={})
        with self.assertRaisesRegex(ValueError, 'exact approved'):
            transition.require_specification(spec)

    def test_authority_only_adds_exact_223_name(self):
        from mta.runtime.ingestion_authority import validate_schema_transition, SCHEMA_FIELDS, SCHEMA_CONTRACT
        value = {key: 'a'*64 for key in SCHEMA_FIELDS}
        value.update(contract=SCHEMA_CONTRACT, initialization_id=transition.INITIALIZATION,
                     target_commit='b'*40, migration_pins=transition.migration_pins())
        self.assertEqual(validate_schema_transition(value), value)
        for name in ('0223_arbitrary', '0224_bpr_history_completion'):
            with self.assertRaises(ValueError):
                validate_schema_transition(dict(value, migration_pins=[[name, 'a'*64]]))
