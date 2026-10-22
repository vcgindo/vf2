"""One child of the failed v4; retain the original eight-owner SQL contract."""
from importlib import import_module
from django.db import migrations

previous = import_module('mta.runtime.migrations.0165_terminal_capture_admission')
prefix, rest = previous.SQL.split('CREATE FUNCTION mta.terminal_capture_admit', 1)
admit, guard = ('CREATE FUNCTION mta.terminal_capture_admit'+rest).split(
    'CREATE OR REPLACE FUNCTION mta.finite_capture_attempt_guard()', 1)
guard = 'CREATE OR REPLACE FUNCTION mta.finite_capture_attempt_guard()'+guard

# The frozen predecessor remains unchanged. Derive only this explicitly sized
# nine-record variant; old v3/v4 admission and lifecycle branches stay intact.
retry_prefix = (prefix.replace('terminal_capture_prefix_digest', 'retry_capture_prefix_digest')
    .replace('P.depth<7', 'P.depth<8').replace('depth=7', 'depth=8')
    .replace('row_count<>8 OR distinct_runs<>8', 'row_count<>9 OR distinct_runs<>9')
    .replace('eight complete', 'nine complete'))
retry_admit = (admit.replace('terminal_capture_admit', 'retry_capture_admit')
    .replace("parent.status<>'RUNNING'", "parent.status<>'FAILED'")
    .replace('fresh-captured-input-reference-v4', 'fresh-captured-input-reference-v5')
    .replace("'native-terminal-'", "'native-terminal-retry-'")
    .replace('mta.finite_capture_prefix_digest(P.run_id)', 'mta.terminal_capture_prefix_digest(P.run_id)')
    .replace('FOR i IN 0..7 LOOP', 'FOR i IN 0..8 LOOP')
    .replace("CASE WHEN i=0 THEN 'fresh-captured-input-reference-v3'\n      WHEN i<6 THEN 'fresh-captured-input-reference-v2' WHEN i=6 THEN 'fresh-captured-input-reference-v1'",
             "CASE WHEN i=0 THEN 'fresh-captured-input-reference-v4' WHEN i=1 THEN 'fresh-captured-input-reference-v3'\n      WHEN i<7 THEN 'fresh-captured-input-reference-v2' WHEN i=7 THEN 'fresh-captured-input-reference-v1'")
    .replace("CASE WHEN i<2 THEN 'RUNNING' ELSE 'FAILED' END", "CASE WHEN i IN (1,2) THEN 'RUNNING' ELSE 'FAILED' END")
    .replace('(i>0 AND owner.recovery_origin_id IS NOT NULL)',
             "(i=1 AND owner.recovery_origin_id IS DISTINCT FROM (SELECT id FROM mta.fresh_mta_dailyfeedattempt WHERE run_id=cap.origin_id))\n    OR (i>1 AND owner.recovery_origin_id IS NOT NULL)")
    .replace('(i<2 AND (owner.phase', '(i<3 AND (owner.phase')
    .replace('IF i=7 THEN', 'IF i=8 THEN')
    .replace('mta.terminal_capture_prefix_digest(parent.run_id)', 'mta.retry_capture_prefix_digest(parent.run_id)'))
dispatch = """ IF child.input_payload->>'schema'='fresh-captured-input-reference-v5' THEN
  RETURN mta.retry_capture_admit(NEW);
 END IF;
"""
old_dispatch = " IF child.input_payload->>'schema'='fresh-captured-input-reference-v4' THEN"
assert guard.count(old_dispatch) == 1
assert "WHEN i=1 THEN 'fresh-captured-input-reference-v3'" in retry_admit
SQL = retry_prefix+retry_admit+guard.replace(old_dispatch, dispatch+old_dispatch).replace('P.depth<7', 'P.depth<8')
REVERSE = """DO $$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
 WHERE input_payload->>'schema'='fresh-captured-input-reference-v5') THEN
 RAISE EXCEPTION 'Failed-terminal retry cannot be downgraded after an attempt'; END IF; END $$;
"""+guard+"""
DROP FUNCTION mta.retry_capture_admit(mta.fresh_mta_dailyfeedattempt);
DROP FUNCTION mta.retry_capture_prefix_digest(uuid);
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0165_terminal_capture_admission')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
