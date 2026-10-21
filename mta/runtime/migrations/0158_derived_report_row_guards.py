"""V3 derived rows can be appended only by their unsealed generation.

Old v2 rows retain their existing guard contracts and identities.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from importlib import import_module
from django.db import migrations

OWNED_TABLES=('fresh_mta_excessprojection','fresh_mta_excessinventoryrow',
 'fresh_mta_fulfillmentprojection','fresh_mta_fulfillmentsummaryrow','fresh_mta_fulfillmentdetailrow',
 'fresh_mta_expediteprojection','fresh_mta_expediterow','fresh_mta_pickpostprojection','fresh_mta_pickpostrow')

SQL=r"""
CREATE FUNCTION mta.guard_v3_derived_report_rows() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid; changes text; join_sql text; filter_sql text; touches boolean; qualified boolean;
BEGIN
 changes=CASE WHEN TG_OP='DELETE' THEN 'old_rows' ELSE 'new_rows' END;
 CASE
"""
classification=import_module('mta.runtime.migrations.0157_report_revision_ownership')
for table,path in classification.SHARED_IMAGES.items():
 condition=("N.vf_image='"+path+"'" if path else
   "EXISTS(SELECT 1 FROM jsonb_array_elements(R.production_manifest->'reports') S WHERE S ? 'deferred' AND N.vf_image IN ('reports/'||(S->>'stage')||'/ReportHeader','reports/'||(S->>'stage')||'/ReportRows'))")
 SQL+=("WHEN TG_TABLE_SCHEMA='mta_state' AND TG_TABLE_NAME='"+table+"' THEN join_sql='R.id=N.vf_run_id'; filter_sql='"+condition.replace("'","''")+"';\n")
SQL+="""ELSE join_sql='R.id=N.run_id'; filter_sql='TRUE';
 END CASE;
 EXECUTE 'SELECT EXISTS(SELECT 1 FROM '||changes||' N JOIN mta.fresh_mta_calculationrun R ON '||join_sql||
   ' WHERE R.production_manifest->>''version''=''3'' AND ('||filter_sql||'))' INTO touches;
 IF NOT touches THEN RETURN NULL; END IF;
 owner=nullif(current_setting('fresh.report_generation',true),'')::uuid;
 IF TG_OP<>'INSERT' OR owner IS NULL THEN RAISE EXCEPTION 'Derived v3 rows require owning append generation'; END IF;
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_dailyreportgeneration G
  JOIN mta.fresh_mta_calculationrun R ON R.id=G.run_id
  WHERE G.run_id=owner AND G.status='INCOMPLETE' AND R.status='SUCCEEDED'
   AND G.source_digest=R.production_digest AND R.production_manifest->>'version'='3') THEN
  RAISE EXCEPTION 'Derived v3 generation is absent, drifted or sealed'; END IF;
 EXECUTE 'SELECT NOT EXISTS(SELECT 1 FROM new_rows N LEFT JOIN mta.fresh_mta_calculationrun R ON '||join_sql||
   ' WHERE R.id IS DISTINCT FROM $1 OR R.status<>''SUCCEEDED'' OR NOT ('||filter_sql||'))' INTO qualified USING owner;
 IF NOT qualified THEN RAISE EXCEPTION 'Derived v3 row owner/path differs'; END IF;
 RETURN NULL;
END $$;
"""
REVERSE=''
for schema,table in [('mta',name) for name in OWNED_TABLES]+[('mta_state',name) for name in classification.SHARED_IMAGES]:
 for op,ref in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
  name='v3_report_'+op.lower()
  SQL+='CREATE TRIGGER '+name+' AFTER '+op+' ON '+schema+'.'+table+' REFERENCING '+ref+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_v3_derived_report_rows();\n'
  REVERSE+='DROP TRIGGER '+name+' ON '+schema+'.'+table+';\n'
REVERSE+='DROP FUNCTION mta.guard_v3_derived_report_rows();'


class Migration(migrations.Migration):
 dependencies=[('fresh_mta','0157_report_revision_ownership')]
 operations=[migrations.RunSQL(SQL,REVERSE)]
