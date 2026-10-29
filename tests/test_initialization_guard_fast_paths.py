"""Pin the exact unchanged predicate tails and predecessor guard identities."""
from importlib import import_module
from unittest import TestCase


class InitializationGuardFastPathTests(TestCase):
    def test_capture_denial_precedes_every_non_scoped_return(self):
        migration = import_module('mta.runtime.migrations.0243_initialization_guard_fast_paths')
        sql = migration.NEW_EFFECT
        denial = sql.index("Scoped capture effect evidence requires its owned transaction")
        early_return = sql.index(' IF consuming_id IS NULL OR NOT EXISTS')
        self.assertLess(denial, early_return)
        self.assertIn("IF TG_ARGV[0] IS DISTINCT FROM 'capture' THEN", sql)
        # Ownership, phase, worker, source reassignment and partition checks
        # after selecting the effective owner remain byte-for-byte unchanged.
        anchor = " IF TG_ARGV[0]='capture' THEN\n  SELECT C.source_id"
        self.assertEqual(sql.split(anchor)[1], migration.OLD_EFFECT.split(anchor)[1])
        self.assertEqual(sql.count('to_jsonb(NEW)'), migration.OLD_EFFECT.count('to_jsonb(NEW)') + 1)

    def test_current_fast_path_only_wraps_proven_null_helper(self):
        migration = import_module('mta.runtime.migrations.0243_initialization_guard_fast_paths')
        expected = migration.OLD_CURRENT.replace(migration.SCOPED,
            " IF nullif(current_setting('fresh.mdm_current_run',true),'') IS NOT NULL THEN\n" +
            migration.SCOPED + '\n END IF;', 1)
        self.assertEqual(migration.NEW_CURRENT, expected)
        pending = import_module('mta.runtime.migrations.0190_day_final_current_copies')._pending
        self.assertEqual(pending.count("R.id::text=current_setting('fresh.mdm_current_run',true)"), 2)
