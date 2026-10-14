"""Durable ownership, immutability and exact-retention guards for native audit."""
from django.db import migrations


BINDINGS = (
    ('nativeauditadd', 'mdmskulocadduploadlog', False),
    ('nativeauditmodify', 'mdmskulocmodifyuploadlog', False),
    ('nativeauditremove', 'mdmskulocremoveuploadlog', False),
    ('nativeauditlocation', 'mdmlocationuploadlog', False),
    ('nativeauditsku', 'mdmskuuploadlog', False),
    ('nativeauditsob', 'mdmsobuploadlog', False),
    ('nativeauditmoq', 'mdmmoquploadlog', False),
    ('nativeauditforce', 'mdmforceuploadlog', True),
)


FORWARD = r'''
CREATE FUNCTION mta.typed_input_node(root jsonb, path text[]) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE node jsonb:=root; key text; selected jsonb;
BEGIN
 FOREACH key IN ARRAY path LOOP
  selected=NULL;
  SELECT item->1 INTO selected FROM jsonb_array_elements(node->'object') item
   WHERE item->>0=key;
  IF selected IS NULL THEN RETURN NULL; END IF;
  node=selected;
 END LOOP;
 RETURN node;
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END $$;

CREATE FUNCTION mta.native_audit_policy_matches(
 payload jsonb, horizon integer, timezone text, client_folder text) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE policy jsonb; keys text[];
BEGIN
 policy=mta.typed_input_node(payload->'tree',ARRAY['profile','native_upload_audit']);
 IF policy IS NULL OR jsonb_typeof(policy->'object')<>'array'
  OR jsonb_array_length(policy->'object')<>3 THEN RETURN false; END IF;
 SELECT array_agg(item->>0 ORDER BY item->>0) INTO keys
  FROM jsonb_array_elements(policy->'object') item;
 RETURN keys=ARRAY['client_folder','horizon','timezone']::text[]
  AND mta.typed_input_node(payload->'tree',ARRAY['profile','native_upload_audit','horizon'])
      =jsonb_build_object('scalar',to_jsonb(horizon))
  AND mta.typed_input_node(payload->'tree',ARRAY['profile','native_upload_audit','timezone'])
      =jsonb_build_object('scalar',to_jsonb(timezone))
  AND mta.typed_input_node(payload->'tree',ARRAY['profile','native_upload_audit','client_folder'])
      =jsonb_build_object('scalar',to_jsonb(client_folder));
END $$;

CREATE FUNCTION mta.native_audit_source_table(audit_table text) RETURNS text
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE audit_table
  WHEN 'fresh_mta_nativeauditadd' THEN 'fresh_mta_mdmskulocadduploadlog'
  WHEN 'fresh_mta_nativeauditmodify' THEN 'fresh_mta_mdmskulocmodifyuploadlog'
  WHEN 'fresh_mta_nativeauditremove' THEN 'fresh_mta_mdmskulocremoveuploadlog'
  WHEN 'fresh_mta_nativeauditlocation' THEN 'fresh_mta_mdmlocationuploadlog'
  WHEN 'fresh_mta_nativeauditsku' THEN 'fresh_mta_mdmskuuploadlog'
  WHEN 'fresh_mta_nativeauditsob' THEN 'fresh_mta_mdmsobuploadlog'
  WHEN 'fresh_mta_nativeauditmoq' THEN 'fresh_mta_mdmmoquploadlog'
  WHEN 'fresh_mta_nativeauditforce' THEN 'fresh_mta_mdmforceuploadlog'
 END
$$;

CREATE FUNCTION mta.native_audit_table_complete(
 capture uuid, audit_table text, source_table text, force_log boolean) RETURNS boolean
LANGUAGE plpgsql STABLE AS $$
DECLARE frozen_count bigint; final_count bigint; invalid boolean; compare_frozen text;
BEGIN
 compare_frozen=CASE WHEN force_log
  THEN '(to_jsonb(F)-ARRAY[''id'',''capture_id'',''stage'',''source_pk'',''ordinal'',''retained'',''OldNorm'']) '
       'IS DISTINCT FROM (to_jsonb(Z)-ARRAY[''id'',''capture_id'',''stage'',''source_pk'',''ordinal'',''retained'',''OldNorm''])'
  ELSE '(to_jsonb(F)-ARRAY[''id'',''capture_id'',''stage'',''source_pk'',''ordinal'',''retained'']) '
       'IS DISTINCT FROM (to_jsonb(Z)-ARRAY[''id'',''capture_id'',''stage'',''source_pk'',''ordinal'',''retained''])' END;
 EXECUTE format('SELECT count(*) FILTER(WHERE stage=''FROZEN''),count(*) FILTER(WHERE stage=''FINAL'') FROM mta.%I WHERE capture_id=$1',audit_table)
  INTO frozen_count,final_count USING capture;
 IF frozen_count<>final_count THEN RETURN false; END IF;
 EXECUTE format('SELECT EXISTS(SELECT 1 FROM mta.%I F LEFT JOIN mta.%I Z '
   'ON Z.capture_id=F.capture_id AND Z.stage=''FROZEN'' AND Z.source_pk=F.source_pk '
   'WHERE F.capture_id=$1 AND F.stage=''FINAL'' AND (Z.id IS NULL OR Z.ordinal<>F.ordinal OR %s))',
   audit_table,audit_table,compare_frozen) INTO invalid USING capture;
 IF invalid THEN RETURN false; END IF;
 EXECUTE format('SELECT EXISTS(SELECT 1 FROM mta.%I F LEFT JOIN mta.%I S '
   'ON S.id=F.source_pk AND S.source_id=(SELECT source_id FROM mta.fresh_mta_nativeuploadaudit WHERE run_id=$1) '
   'WHERE F.capture_id=$1 AND F.stage=''FINAL'' AND '
   '((F.retained IS TRUE AND (S.id IS NULL OR (to_jsonb(S)-ARRAY[''id'',''source_id'']) '
     'IS DISTINCT FROM (to_jsonb(F)-ARRAY[''id'',''capture_id'',''stage'',''source_pk'',''ordinal'',''retained'']))) '
   'OR (F.retained IS FALSE AND S.id IS NOT NULL)))',audit_table,source_table)
  INTO invalid USING capture;
 RETURN NOT invalid;
END $$;

CREATE FUNCTION mta.guard_native_upload_audit() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE valid_header boolean; complete boolean;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Native upload audit is immutable'; END IF;
 IF TG_OP='INSERT' THEN
  SELECT R.kind='DAILY_CHAIN' AND R.status='RUNNING' AND D.run_id=R.id
    AND D.status='CAPTURED'
    AND D.source_id=NEW.source_id AND I.id=NEW.initialization_id
    AND I.source_id=NEW.source_id AND I.configuration_digest=NEW.configuration_digest
    AND I.input_manifest_digest<>'' AND I.receipt_digest<>''
    AND S.receipt->>'schema'='fresh-production-mdm-source-v1'
    AND R.business_date=NEW.business_date
    AND R.predecessor_id IS NOT DISTINCT FROM NEW.predecessor_id
    AND D.origin_id IS NOT DISTINCT FROM NEW.origin_id
    AND NEW.run_id::text IS NOT DISTINCT FROM current_setting('fresh.native_audit_run',true)
    AND NEW.status='FROZEN' AND NEW.terminal_digest=''
    AND NEW.frozen_digest~'^[0-9a-f]{64}$' AND NEW.configuration_digest~'^[0-9a-f]{64}$'
    AND NEW.horizon>=0 AND EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=NEW.timezone)
    AND (NEW.client_folder IS NULL OR btrim(NEW.client_folder)<>'')
    AND mta.native_audit_policy_matches(I.input_payload,NEW.horizon,NEW.timezone,NEW.client_folder)
    AND mta.native_audit_policy_matches(R.input_payload,NEW.horizon,NEW.timezone,NEW.client_folder)
    AND (NEW.predecessor_id IS NULL OR EXISTS(
      SELECT 1 FROM mta.fresh_mta_nativeuploadaudit P
      JOIN mta.fresh_mta_calculationrun PR ON PR.id=P.run_id
      WHERE P.run_id=NEW.predecessor_id AND P.status='SEALED' AND PR.status='SUCCEEDED'
       AND P.source_id=NEW.source_id AND P.initialization_id=NEW.initialization_id
       AND P.horizon=NEW.horizon AND P.timezone=NEW.timezone
       AND P.client_folder IS NOT DISTINCT FROM NEW.client_folder))
    AND (NEW.origin_id IS NULL OR EXISTS(
      SELECT 1 FROM mta.fresh_mta_nativeuploadaudit O
      JOIN mta.fresh_mta_calculationrun ORR ON ORR.id=O.run_id
      WHERE O.run_id=NEW.origin_id AND O.status='FROZEN' AND ORR.status='FAILED'
       AND O.source_id=NEW.source_id AND O.initialization_id=NEW.initialization_id
       AND O.predecessor_id IS NOT DISTINCT FROM NEW.predecessor_id
       AND O.business_date=NEW.business_date AND O.horizon=NEW.horizon
       AND O.timezone=NEW.timezone AND O.client_folder IS NOT DISTINCT FROM NEW.client_folder))
  INTO valid_header
  FROM mta.fresh_mta_calculationrun R
  JOIN mta.fresh_mta_mdmdailyinputcapture D ON D.run_id=R.id
  JOIN mta.fresh_mta_productioninitialization I ON I.source_id=D.source_id
  JOIN mta.fresh_mta_mdmsource S ON S.id=D.source_id
  WHERE R.id=NEW.run_id;
  IF NOT coalesce(valid_header,false)
   THEN RAISE EXCEPTION 'Native upload audit requires its exact running daily owner and policy'; END IF;
  RETURN NEW;
 END IF;
 IF OLD.status<>'FROZEN' OR NEW.status<>'SEALED'
  OR (to_jsonb(NEW)-ARRAY['status','terminal_digest'])<>(to_jsonb(OLD)-ARRAY['status','terminal_digest'])
  OR NEW.terminal_digest!~'^[0-9a-f]{64}$'
  OR NEW.run_id::text IS DISTINCT FROM current_setting('fresh.native_audit_run',true)
  OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
                WHERE id=NEW.run_id AND kind='DAILY_CHAIN' AND status='RUNNING')
  OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture
                WHERE run_id=NEW.run_id AND status='CONSUMED')
  THEN RAISE EXCEPTION 'Native upload audit may seal exactly once'; END IF;
 complete=
  mta.native_audit_table_complete(NEW.run_id,'fresh_mta_nativeauditadd','fresh_mta_mdmskulocadduploadlog',false)
  AND mta.native_audit_table_complete(NEW.run_id,'fresh_mta_nativeauditmodify','fresh_mta_mdmskulocmodifyuploadlog',false)
  AND mta.native_audit_table_complete(NEW.run_id,'fresh_mta_nativeauditremove','fresh_mta_mdmskulocremoveuploadlog',false)
  AND mta.native_audit_table_complete(NEW.run_id,'fresh_mta_nativeauditlocation','fresh_mta_mdmlocationuploadlog',false)
  AND mta.native_audit_table_complete(NEW.run_id,'fresh_mta_nativeauditsku','fresh_mta_mdmskuuploadlog',false)
  AND mta.native_audit_table_complete(NEW.run_id,'fresh_mta_nativeauditsob','fresh_mta_mdmsobuploadlog',false)
  AND mta.native_audit_table_complete(NEW.run_id,'fresh_mta_nativeauditmoq','fresh_mta_mdmmoquploadlog',false)
  AND mta.native_audit_table_complete(NEW.run_id,'fresh_mta_nativeauditforce','fresh_mta_mdmforceuploadlog',true);
 IF NOT complete THEN RAISE EXCEPTION 'Native upload audit cannot seal incomplete retention'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER native_upload_audit_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_nativeuploadaudit FOR EACH ROW EXECUTE FUNCTION mta.guard_native_upload_audit();

CREATE FUNCTION mta.deny_native_audit_statement() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'Native upload audit rows cannot be deleted or truncated';
END $$;
CREATE TRIGGER native_upload_audit_delete BEFORE DELETE
 ON mta.fresh_mta_nativeuploadaudit FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_native_audit_statement();
CREATE TRIGGER native_upload_audit_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_nativeuploadaudit FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_native_audit_statement();

CREATE FUNCTION mta.guard_native_audit_occurrence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE A mta.fresh_mta_nativeuploadaudit; source_table text; frozen jsonb;
 source_value jsonb; retained_value boolean; compare_frozen jsonb; compare_new jsonb;
 source_ordinal bigint;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Native upload audit occurrences are insert-only'; END IF;
 SELECT * INTO A FROM mta.fresh_mta_nativeuploadaudit WHERE run_id=NEW.capture_id;
 IF NOT FOUND OR A.status<>'FROZEN'
  OR NEW.capture_id::text IS DISTINCT FROM current_setting('fresh.native_audit_run',true)
  OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun
                WHERE id=NEW.capture_id AND kind='DAILY_CHAIN' AND status='RUNNING')
  OR NEW.stage NOT IN ('FROZEN','FINAL')
  THEN RAISE EXCEPTION 'Native upload audit occurrence requires its frozen running owner'; END IF;
 source_table=mta.native_audit_source_table(TG_TABLE_NAME);
 IF NEW.stage='FROZEN' THEN
  IF A.origin_id IS NOT NULL THEN
   EXECUTE format('SELECT to_jsonb(F) FROM mta.%I F '
    'WHERE capture_id=$1 AND stage=''FROZEN'' AND source_pk=$2',TG_TABLE_NAME)
    INTO frozen USING A.origin_id,NEW.source_pk;
   IF frozen IS NULL OR (frozen->>'ordinal')::bigint<>NEW.ordinal
    OR (frozen-ARRAY['id','capture_id','stage','source_pk','ordinal','retained'])
       IS DISTINCT FROM (to_jsonb(NEW)-ARRAY['id','capture_id','stage','source_pk','ordinal','retained'])
    THEN RAISE EXCEPTION 'Native upload audit retry frozen occurrence differs from its origin'; END IF;
  ELSE
   EXECUTE format('SELECT X.value,X.ordinal FROM (SELECT S.id,'
    'to_jsonb(S)-ARRAY[''id'',''source_id''] value,row_number() OVER(ORDER BY S.id) ordinal '
    'FROM mta.%I S WHERE S.source_id=$1) X WHERE X.id=$2',source_table)
    INTO source_value,source_ordinal USING A.source_id,NEW.source_pk;
   IF source_value IS NULL OR source_ordinal<>NEW.ordinal
    OR source_value IS DISTINCT FROM
       (to_jsonb(NEW)-ARRAY['id','capture_id','stage','source_pk','ordinal','retained'])
    THEN RAISE EXCEPTION 'Native upload audit frozen occurrence differs from ordered source'; END IF;
  END IF;
  RETURN NEW;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture
               WHERE run_id=NEW.capture_id AND status='CONSUMED')
  THEN RAISE EXCEPTION 'Native upload audit final occurrence requires consumed daily input'; END IF;
 EXECUTE format('SELECT to_jsonb(F) FROM mta.%I F WHERE capture_id=$1 AND stage=''FROZEN'' AND source_pk=$2',TG_TABLE_NAME)
  INTO frozen USING NEW.capture_id,NEW.source_pk;
 IF frozen IS NULL OR (frozen->>'ordinal')::bigint<>NEW.ordinal
  THEN RAISE EXCEPTION 'Native upload audit final occurrence lacks its frozen identity'; END IF;
 compare_frozen=frozen-ARRAY['id','capture_id','stage','source_pk','ordinal','retained'];
 compare_new=to_jsonb(NEW)-ARRAY['id','capture_id','stage','source_pk','ordinal','retained'];
 IF TG_TABLE_NAME='fresh_mta_nativeauditforce' THEN
  compare_frozen=compare_frozen-'OldNorm'; compare_new=compare_new-'OldNorm';
 END IF;
 IF compare_frozen IS DISTINCT FROM compare_new
  THEN RAISE EXCEPTION 'Native upload audit final occurrence differs from frozen values'; END IF;
 EXECUTE format('SELECT to_jsonb(S)-ARRAY[''id'',''source_id''], '
  '(S."ActionTimeStamp" AT TIME ZONE $3)::date>$4 FROM mta.%I S WHERE S.id=$1 AND S.source_id=$2',source_table)
  INTO source_value,retained_value
  USING NEW.source_pk,A.source_id,A.timezone,A.business_date-(A.horizon+1);
 IF source_value IS NULL
  OR source_value IS DISTINCT FROM (to_jsonb(NEW)-ARRAY['id','capture_id','stage','source_pk','ordinal','retained'])
  OR NEW.retained IS DISTINCT FROM retained_value
  THEN RAISE EXCEPTION 'Native upload audit final occurrence differs from selected source/cutoff'; END IF;
 RETURN NEW;
END $$;
'''

for audit, _, _ in BINDINGS:
    FORWARD += f'''
CREATE TRIGGER native_audit_occurrence_guard BEFORE INSERT OR UPDATE OR DELETE
 ON mta.fresh_mta_{audit} FOR EACH ROW EXECUTE FUNCTION mta.guard_native_audit_occurrence();
CREATE TRIGGER native_audit_occurrence_delete BEFORE DELETE
 ON mta.fresh_mta_{audit} FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_native_audit_statement();
CREATE TRIGGER native_audit_occurrence_truncate BEFORE TRUNCATE
 ON mta.fresh_mta_{audit} FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_native_audit_statement();
'''

FORWARD += r'''
CREATE FUNCTION mta.native_audit_source_delete_allowed(source_table text, old_row jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE AS $$
DECLARE run_text text; audit_table text; allowed boolean;
BEGIN
 run_text=current_setting('fresh.native_audit_run',true);
 IF coalesce(run_text,'')='' THEN RETURN false; END IF;
 audit_table=CASE source_table
  WHEN 'fresh_mta_mdmskulocadduploadlog' THEN 'fresh_mta_nativeauditadd'
  WHEN 'fresh_mta_mdmskulocmodifyuploadlog' THEN 'fresh_mta_nativeauditmodify'
  WHEN 'fresh_mta_mdmskulocremoveuploadlog' THEN 'fresh_mta_nativeauditremove'
  WHEN 'fresh_mta_mdmlocationuploadlog' THEN 'fresh_mta_nativeauditlocation'
  WHEN 'fresh_mta_mdmskuuploadlog' THEN 'fresh_mta_nativeauditsku'
  WHEN 'fresh_mta_mdmsobuploadlog' THEN 'fresh_mta_nativeauditsob'
  WHEN 'fresh_mta_mdmmoquploadlog' THEN 'fresh_mta_nativeauditmoq'
  WHEN 'fresh_mta_mdmforceuploadlog' THEN 'fresh_mta_nativeauditforce'
 END;
 IF audit_table IS NULL THEN RETURN false; END IF;
 EXECUTE format('SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_nativeuploadaudit A '
  'JOIN mta.fresh_mta_calculationrun R ON R.id=A.run_id JOIN mta.%I F ON F.capture_id=A.run_id '
  'WHERE A.run_id=$1::uuid AND A.status=''FROZEN'' AND R.kind=''DAILY_CHAIN'' AND R.status=''RUNNING'' '
  'AND EXISTS(SELECT 1 FROM mta.fresh_mta_mdmdailyinputcapture D WHERE D.run_id=A.run_id AND D.status=''CONSUMED'') '
  'AND A.source_id=($2->>''source_id'')::bigint AND F.stage=''FINAL'' AND F.retained IS FALSE '
  'AND F.source_pk=($2->>''id'')::bigint AND '
  '(to_jsonb(F)-ARRAY[''id'',''capture_id'',''stage'',''source_pk'',''ordinal'',''retained'']) '
  '=($2-ARRAY[''id'',''source_id'']))',audit_table)
  INTO allowed USING run_text,old_row;
 RETURN coalesce(allowed,false);
END $$;

CREATE FUNCTION mta.guard_native_audit_source_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource
               WHERE id=OLD.source_id AND receipt->>'schema'='fresh-production-mdm-source-v1')
  THEN RETURN OLD; END IF;
 IF NOT mta.native_audit_source_delete_allowed(TG_TABLE_NAME,to_jsonb(OLD))
  THEN RAISE EXCEPTION 'Native upload audit source delete lacks exact final ownership'; END IF;
 RETURN OLD;
END $$;

CREATE FUNCTION mta.guard_native_audit_source_truncate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_mdmsource
           WHERE receipt->>'schema'='fresh-production-mdm-source-v1')
  THEN RAISE EXCEPTION 'Native upload audit sources cannot be truncated'; END IF;
 RETURN NULL;
END $$;
'''

for _, source, force in BINDINGS:
    if not force:
        FORWARD += f'''
CREATE TRIGGER native_audit_source_delete BEFORE DELETE ON mta.fresh_mta_{source}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_native_audit_source_delete();
CREATE TRIGGER native_audit_source_truncate BEFORE TRUNCATE ON mta.fresh_mta_{source}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_native_audit_source_truncate();
'''

FORWARD += r'''
CREATE OR REPLACE FUNCTION mta.guard_force_upload_log() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 IF TG_OP='DELETE' THEN
  IF NOT mta.native_audit_source_delete_allowed(TG_TABLE_NAME,to_jsonb(OLD))
   THEN RAISE EXCEPTION 'Force upload log is retained'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='INSERT' THEN
  IF NOT (COALESCE(mta.supplier_decision_owned(owner),false) OR mta.native_mdm_family_bootstrap(owner))
   THEN RAISE EXCEPTION 'Force upload log insert requires owned decision'; END IF;
 ELSE
  IF NOT mta.force_consumption_owned(owner) OR NEW.source_id<>OLD.source_id
    OR (to_jsonb(NEW)-'OldNorm')<>(to_jsonb(OLD)-'OldNorm')
   THEN RAISE EXCEPTION 'Force upload log update requires owned OldNorm consumption'; END IF;
 END IF;
 RETURN NEW;
END $$;
'''


REVERSE = r'''
CREATE OR REPLACE FUNCTION mta.guard_force_upload_log() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner bigint;
BEGIN
 owner=CASE WHEN TG_OP='DELETE' THEN OLD.source_id ELSE NEW.source_id END;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Force upload log is retained'; END IF;
 IF TG_OP='INSERT' THEN IF NOT (COALESCE(mta.supplier_decision_owned(owner),false) OR mta.native_mdm_family_bootstrap(owner)) THEN RAISE EXCEPTION 'Force upload log insert requires owned decision'; END IF;
 ELSE IF NOT mta.force_consumption_owned(owner) OR NEW.source_id<>OLD.source_id OR (to_jsonb(NEW)-'OldNorm')<>(to_jsonb(OLD)-'OldNorm') THEN RAISE EXCEPTION 'Force upload log update requires owned OldNorm consumption'; END IF; END IF;
 RETURN NEW;
END $$;
'''

for _, source, force in reversed(BINDINGS):
    if not force:
        REVERSE += f'''
DROP TRIGGER native_audit_source_truncate ON mta.fresh_mta_{source};
DROP TRIGGER native_audit_source_delete ON mta.fresh_mta_{source};
'''

REVERSE += r'''
DROP FUNCTION mta.guard_native_audit_source_truncate();
DROP FUNCTION mta.guard_native_audit_source_delete();
DROP FUNCTION mta.native_audit_source_delete_allowed(text,jsonb);
'''

for audit, _, _ in reversed(BINDINGS):
    REVERSE += f'''
DROP TRIGGER native_audit_occurrence_truncate ON mta.fresh_mta_{audit};
DROP TRIGGER native_audit_occurrence_delete ON mta.fresh_mta_{audit};
DROP TRIGGER native_audit_occurrence_guard ON mta.fresh_mta_{audit};
'''

REVERSE += r'''
DROP FUNCTION mta.guard_native_audit_occurrence();
DROP TRIGGER native_upload_audit_truncate ON mta.fresh_mta_nativeuploadaudit;
DROP TRIGGER native_upload_audit_delete ON mta.fresh_mta_nativeuploadaudit;
DROP FUNCTION mta.deny_native_audit_statement();
DROP TRIGGER native_upload_audit_guard ON mta.fresh_mta_nativeuploadaudit;
DROP FUNCTION mta.guard_native_upload_audit();
DROP FUNCTION mta.native_audit_table_complete(uuid,text,text,boolean);
DROP FUNCTION mta.native_audit_source_table(text);
DROP FUNCTION mta.native_audit_policy_matches(jsonb,integer,text,text);
DROP FUNCTION mta.typed_input_node(jsonb,text[]);
'''


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0136_native_upload_audit')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
