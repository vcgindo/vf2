"""Recognize the exact released recovery of an accepted stage producer."""
from importlib import import_module
from django.db import migrations

_original = import_module('mta.runtime.migrations.0191_scoped_action_ownership')
OLD = _original.SQL.split('FUNCTION mta.actionable_scope_phase(target uuid, accepted uuid)', 1)[1].split('AS $body$', 1)[1].split('$body$;', 1)[0]
BODY = """
 WITH RECURSIVE latest AS (
  SELECT * FROM mta.fresh_mta_runscopeattempt WHERE run_id=target
  ORDER BY created_at DESC,id DESC LIMIT 1
 ), recovery AS (
  SELECT L.id,L.recovery_of_id,L.attempt_no,L.created_at,ARRAY[L.id] AS path
  FROM latest L WHERE L.status='RELEASED'
  UNION ALL
  SELECT A.id,A.recovery_of_id,A.attempt_no,A.created_at,C.path||A.id
  FROM recovery C JOIN mta.fresh_mta_runscopeattempt A ON A.id=C.recovery_of_id
  CROSS JOIN latest L
  WHERE A.status='FAILED' AND A.run_id=L.run_id AND A.scope=L.scope
   AND A.command_key=L.command_key AND A.compatibility_digest=L.compatibility_digest
   AND A.input_digest=L.input_digest AND A.input_manifest_digest=L.input_manifest_digest
   AND A.attempt_no=C.attempt_no-1 AND (A.created_at,A.id)<(C.created_at,C.id)
   AND NOT A.id=ANY(C.path)
 )
 SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_runphaseacceptance P
 JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id
 JOIN mta.fresh_mta_runscopeattempt A ON A.id=P.attempt_id
 JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id
 CROSS JOIN latest L CROSS JOIN LATERAL mta.scope_head(R.id) H
 WHERE R.id=target AND P.id=accepted AND P.state_sealed AND R.status='RUNNING'
  AND R.kind='DAILY_CHAIN' AND R.output_digest='' AND C.status='CAPTURED'
  AND P.source_id=C.source_id AND P.capture_digest=C.revision_digest
  AND P.input_digest=R.input_digest AND A.input_manifest_digest=R.input_manifest_digest
  AND A.run_id=R.id AND L.status='RELEASED' AND L.run_id=R.id
  AND (L.scope,L.command_key,L.compatibility_digest,L.input_digest,L.input_manifest_digest)
      =(A.scope,A.command_key,A.compatibility_digest,A.input_digest,A.input_manifest_digest)
  AND ((P.phase='BPR' AND A.scope='UptoBPR') OR (P.phase='DBM' AND A.scope='UptoDBM'))
  AND (H.phase,H.digest)=(P.phase,P.digest)
  AND (L.id=A.id OR (L.expected_phase,L.expected_receipt_digest)=(P.phase,P.digest))
  AND EXISTS(SELECT 1 FROM recovery WHERE id=A.id)
  AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt N WHERE N.run_id=R.id
   AND (N.status='ACTIVE' OR ((N.created_at,N.id)>(A.created_at,A.id)
    AND NOT EXISTS(SELECT 1 FROM recovery WHERE id=N.id)))))
"""


def exact(body):
    # OR REPLACE preserves OID and ACL; reject any unreviewed predecessor body.
    return """DO $pre$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_proc P JOIN pg_language L ON L.oid=P.prolang
  WHERE P.oid=to_regprocedure('mta.actionable_scope_phase(uuid,uuid)')
   AND P.prosrc=$expected$"""+body+"""$expected$ AND NOT P.prosecdef
   AND P.proconfig=ARRAY['search_path=pg_catalog, mta'] AND L.lanname='sql'
   AND P.provolatile='s' AND P.prorettype='boolean'::regtype
   AND P.proowner=(SELECT relowner FROM pg_class WHERE oid='mta.fresh_mta_runscopeattempt'::regclass))
 THEN RAISE EXCEPTION 'Exact actionable scope predecessor required'; END IF;
END $pre$;
"""


def replace(body):
    return ('CREATE OR REPLACE FUNCTION mta.actionable_scope_phase(target uuid, accepted uuid) '
            'RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog,mta AS $body$'+body+'$body$;\n')


SQL = exact(OLD)+replace(BODY)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0221_scoped_action_cache_writer')]
    operations = [migrations.RunSQL(SQL)]
