"""One final child of the failed v5; retain the original ten-owner contract."""
from importlib import import_module
from django.db import migrations

previous = import_module('mta.runtime.migrations.0166_failed_terminal_retry')
prefix, rest = previous.SQL.split('CREATE FUNCTION mta.retry_capture_admit', 1)
admit, guard = ('CREATE FUNCTION mta.retry_capture_admit'+rest).split(
    'CREATE OR REPLACE FUNCTION mta.finite_capture_attempt_guard()', 1)
guard = 'CREATE OR REPLACE FUNCTION mta.finite_capture_attempt_guard()'+guard

# Derive one explicitly sized ten-record variant. The v3-v5 functions and
# dispatches remain byte-for-byte represented in the installed catalogue.
final_prefix = (prefix.replace('retry_capture_prefix_digest', 'final_capture_prefix_digest')
    .replace('P.depth<8', 'P.depth<9').replace('depth=8', 'depth=9')
    .replace('row_count<>9 OR distinct_runs<>9', 'row_count<>10 OR distinct_runs<>10')
    .replace('nine complete', 'ten complete'))
final_admit = (admit.replace('retry_capture_admit', 'final_capture_admit')
    .replace('fresh-captured-input-reference-v5', 'fresh-captured-input-reference-v6')
    .replace("'native-terminal-retry-'", "'native-final-attempt-'")
    .replace('mta.terminal_capture_prefix_digest(P.run_id)', 'mta.retry_capture_prefix_digest(P.run_id)')
    .replace('FOR i IN 0..8 LOOP', 'FOR i IN 0..9 LOOP')
    .replace("CASE WHEN i=0 THEN 'fresh-captured-input-reference-v4' WHEN i=1 THEN 'fresh-captured-input-reference-v3'\n      WHEN i<7 THEN 'fresh-captured-input-reference-v2' WHEN i=7 THEN 'fresh-captured-input-reference-v1'",
             "CASE WHEN i=0 THEN 'fresh-captured-input-reference-v5' WHEN i=1 THEN 'fresh-captured-input-reference-v4' WHEN i=2 THEN 'fresh-captured-input-reference-v3'\n      WHEN i<8 THEN 'fresh-captured-input-reference-v2' WHEN i=8 THEN 'fresh-captured-input-reference-v1'")
    .replace("CASE WHEN i IN (1,2) THEN 'RUNNING' ELSE 'FAILED' END",
             "CASE WHEN i IN (2,3) THEN 'RUNNING' ELSE 'FAILED' END")
    .replace('(i=1 AND owner.recovery_origin_id IS DISTINCT FROM (SELECT id FROM mta.fresh_mta_dailyfeedattempt WHERE run_id=cap.origin_id))',
             '(i IN (1,2) AND owner.recovery_origin_id IS DISTINCT FROM (SELECT id FROM mta.fresh_mta_dailyfeedattempt WHERE run_id=cap.origin_id))')
    .replace('(i>1 AND owner.recovery_origin_id IS NOT NULL)',
             '(i>2 AND owner.recovery_origin_id IS NOT NULL)')
    .replace('(i<3 AND (owner.phase', '(i<4 AND (owner.phase')
    .replace('IF i=8 THEN', 'IF i=9 THEN')
    .replace('mta.retry_capture_prefix_digest(parent.run_id)', 'mta.final_capture_prefix_digest(parent.run_id)'))
dispatch = """ IF child.input_payload->>'schema'='fresh-captured-input-reference-v6' THEN
  RETURN mta.final_capture_admit(NEW);
 END IF;
"""
old_dispatch = " IF child.input_payload->>'schema'='fresh-captured-input-reference-v5' THEN"
assert guard.count(old_dispatch) == 1
assert "WHEN i=1 THEN 'fresh-captured-input-reference-v4'" in final_admit
assert "WHEN i=2 THEN 'fresh-captured-input-reference-v3'" in final_admit
SQL = final_prefix+final_admit+guard.replace(old_dispatch, dispatch+old_dispatch).replace('P.depth<8', 'P.depth<9')
REVERSE = """DO $$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
 WHERE input_payload->>'schema'='fresh-captured-input-reference-v6') THEN
 RAISE EXCEPTION 'Final admitted attempt cannot be downgraded after use'; END IF; END $$;
"""+guard+"""
DROP FUNCTION mta.final_capture_admit(mta.fresh_mta_dailyfeedattempt);
DROP FUNCTION mta.final_capture_prefix_digest(uuid);
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0166_failed_terminal_retry')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
