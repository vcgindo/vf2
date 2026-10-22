"""Compute report qualification once per distinct statement owner/path.

Only two existing function bodies change; identity, ACLs, settings, locking and
all nonreport revision/immutability behavior remain owned by earlier migrations.
"""
from importlib import import_module
import re
from django.db import migrations

prior=import_module('mta.runtime.migrations.0162_derived_trend_ownership')
OLD_INGESTION=prior.current_body()
OLD_DERIVED=prior.new_guard.split('AS $$',1)[1].rsplit('$$;',1)[0]


def _query(join,filter_sql,keys,resolve,*,derived=False,qualified=False):
    # These strings come only from the frozen migration's schema/table CASE.
    # Inspect each changed row's narrow identity once. Missing/NULL owners are
    # retained by LEFT JOIN, never silently discarded by an inner join.
    export='jsonb_array_elements' in filter_sql
    paths=(",ARRAY(SELECT V.image FROM jsonb_array_elements(R.production_manifest->'reports') S "
        "CROSS JOIN LATERAL (VALUES ('reports/'||(S->>'stage')||'/ReportHeader'),"
        "('reports/'||(S->>'stage')||'/ReportRows')) V(image) WHERE S ? 'deferred') AS images" if export else '')
    path=("EXISTS(SELECT 1 FROM unnest(R.images) V(image) WHERE V.image=N.vf_image)" if export else filter_sql)
    facts=("K.run_key,R.id,R.status,(R.production_manifest->>'version'='3') AS v3" if derived else
        "K.run_key,R.id,(R.id IS NULL OR R.kind<>'DAILY_CHAIN' OR R.status<>'SUCCEEDED' "
        "OR R.production_manifest->>'version' IS DISTINCT FROM '3') AS invalid")
    predicate=("R.id IS DISTINCT FROM $1 OR R.status<>'SUCCEEDED' OR NOT ("+path+")" if qualified else
        "R.v3 AND ("+path+")" if derived else "R.invalid OR NOT ("+path+")")
    # Computed booleans, not raw JSON, cross this materialization boundary.
    return ("WITH owners AS MATERIALIZED(SELECT DISTINCT "+keys+" FROM {changes}),"
        "resolved AS MATERIALIZED(SELECT N.*,"+resolve+" AS run_key FROM owners N "+join+"),"
        "runs AS MATERIALIZED(SELECT DISTINCT run_key FROM resolved),"
        "facts AS MATERIALIZED(SELECT "+facts+paths+" FROM runs K "
        "LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=K.run_key),"
        "checks AS MATERIALIZED(SELECT ("+predicate+") AS verdict FROM resolved N "
        "LEFT JOIN facts R ON R.run_key IS NOT DISTINCT FROM N.run_key) SELECT "+
        ("EXISTS" if derived and not qualified else "NOT EXISTS")+"(SELECT 1 FROM checks WHERE verdict)")


def _case_keys(join):
    if ' P ON ' in join:
        parent,rest=join.split(' LEFT JOIN mta.fresh_mta_calculationrun',1)
        fk=re.search(r'=N\.([a-z_]+)',parent).group(1)
        resolve=re.search(r'R.id=P\.([a-z_]+)',rest).group(1)
        return fk,parent,'P.'+resolve
    if 'N.vf_run_id' in join:return 'vf_run_id,vf_image','','N.vf_run_id'
    return 'run_id','','N.run_id'


def ingestion_body():
    body=OLD_INGESTION.replace('report_join text;','report_join text; report_check text;')
    pattern=r"report_join='([^']*)'; report_filter='((?:''|[^'])*)';"
    def case(match):
        join,filter_sql=match.group(1),match.group(2).replace("''", "'")
        keys,parent,resolve=_case_keys(join)
        query=_query(parent,filter_sql,keys,resolve)
        return match.group(0)+" report_check='"+query.replace("'","''")+"';"
    body,count=re.subn(pattern,case,body)
    if count!=21:raise ValueError('Frozen report classification cases differ')
    start=body.index("  EXECUTE 'SELECT NOT EXISTS(SELECT 1 FROM '||changes")
    end=body.index('  IF qualified THEN RETURN NULL; END IF;',start)
    body=body[:start]+"""  EXECUTE replace(report_check,'{changes}',changes) INTO qualified;
  IF qualified AND TG_OP='UPDATE' THEN
   EXECUTE replace(report_check,'{changes}','old_rows') INTO qualified;
  END IF;
"""+body[end:]
    return body


def derived_body():
    body=OLD_DERIVED.replace('join_sql text;','join_sql text; touch_query text; qualify_query text;')
    pattern=r"join_sql='([^']*)'; filter_sql='((?:''|[^'])*)';"
    def case(match):
        join,filter_sql=match.group(1),match.group(2).replace("''", "'")
        keys,parent,resolve=_case_keys('LEFT JOIN mta.fresh_mta_calculationrun R ON '+join)
        touch=_query(parent,filter_sql,keys,resolve,derived=True)
        qualify=_query(parent,filter_sql,keys,resolve,derived=True,qualified=True)
        return match.group(0)+" touch_query='"+touch.replace("'","''")+"'; qualify_query='"+qualify.replace("'","''")+"';"
    body,count=re.subn(pattern,case,body)
    if count!=15:raise ValueError('Frozen derived classification cases differ')
    start=body.index(" EXECUTE 'SELECT EXISTS(SELECT 1 FROM '||changes")
    end=body.index(' IF NOT touches THEN RETURN NULL; END IF;',start)
    body=body[:start]+""" EXECUTE replace(touch_query,'{changes}',changes) INTO touches;
 IF TG_OP='UPDATE' AND NOT touches THEN
  EXECUTE replace(touch_query,'{changes}','old_rows') INTO touches;
 END IF;
"""+body[end:]
    start=body.index(" EXECUTE 'SELECT NOT EXISTS(SELECT 1 FROM new_rows N")
    end=body.index(' IF NOT qualified THEN',start)
    body=body[:start]+" EXECUTE replace(qualify_query,'{changes}','new_rows') INTO qualified USING owner;\n"+body[end:]
    return body


NEW_INGESTION=ingestion_body()
NEW_DERIVED=derived_body()
FUNCTIONS=(('ingestion_watch',OLD_INGESTION,NEW_INGESTION,True,['search_path=pg_catalog, mta']),
           ('guard_v3_derived_report_rows',OLD_DERIVED,NEW_DERIVED,False,None))


def sql_transition(reverse=False):
    result=''
    for name,old,new,definer,config in FUNCTIONS:
        before,after=(new,old) if reverse else (old,new)
        # Compare exact predecessor body/attributes and refuse drift. CREATE OR
        # REPLACE preserves OID/owner/ACL/attachments; no new grants or triggers.
        escaped=before.replace("'","''")
        settings="ARRAY['search_path=pg_catalog, mta']::text[]" if config else 'NULL::text[]'
        result+=("DO $pre$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "WHERE N.nspname='mta' AND P.proname='"+name+"' AND P.pronargs=0 "
            "AND P.prorettype='trigger'::regtype AND P.prosrc='"+escaped+"' AND P.prosecdef="+
            str(definer).lower()+" AND P.proconfig IS NOT DISTINCT FROM "+settings+") THEN "
            "RAISE EXCEPTION 'Exact predecessor report guard required: "+name+"'; END IF; END $pre$;\n")
        result+='CREATE OR REPLACE FUNCTION mta.'+name+'() RETURNS trigger LANGUAGE plpgsql'
        if definer:result+=' SECURITY DEFINER SET search_path=pg_catalog,mta'
        result+=' AS $guard$'+after+'$guard$;\n'
    return result


FORWARD=sql_transition()
REVERSE=sql_transition(reverse=True)


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0167_final_attempt_admission')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
