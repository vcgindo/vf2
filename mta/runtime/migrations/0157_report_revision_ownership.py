"""Keep qualified v3 report generations outside operational input revisions.

Every old-v2 and nonqualified write retains the original invalidation behavior.
The catalogue is frozen: new participants require an explicit later migration.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from importlib import import_module
from django.db import migrations

REPORT_TABLES = {'fresh_mta_bprpreparedprojection': None, 'fresh_mta_bprpreparedrow': None, 'fresh_mta_borpreparedreceipt': None, 'fresh_mta_borpreparedrow': None, 'fresh_mta_guideddbmpreparedprojection': None, 'fresh_mta_guideddbmpreparedrow': None, 'fresh_mta_guidedchronicpreparedprojection': None, 'fresh_mta_guidedchronicpreparedrow': None, 'fresh_mta_guidedhistorypreparedprojection': None, 'fresh_mta_guidedavailabilityhistoryrow': None, 'fresh_mta_guidedexcesshistoryrow': None, 'fresh_mta_btrreportinggeneration': None, 'fresh_mta_btrjoinreference': ('generation_id', 'fresh_mta_btrreportinggeneration', 'id', 'run_id'), 'fresh_mta_btrpresentationrow': ('generation_id', 'fresh_mta_btrreportinggeneration', 'id', 'run_id'), 'fresh_mta_rrrpreparedprojection': None, 'fresh_mta_rrrpreparedmembership': None, 'fresh_mta_excessprojection': None, 'fresh_mta_excessinventoryrow': None, 'fresh_mta_fulfillmentprojection': None, 'fresh_mta_fulfillmentsummaryrow': None, 'fresh_mta_fulfillmentdetailrow': None, 'fresh_mta_expediteprojection': None, 'fresh_mta_expediterow': None, 'fresh_mta_pickpostprojection': None, 'fresh_mta_pickpostrow': None, 'fresh_mta_planningsourceprojection': None, 'fresh_mta_planningbprmasterrow': None, 'fresh_mta_planninggitmasterrow': None, 'fresh_mta_planninggridprojection': None, 'fresh_mta_planningexcessgridrow': None, 'fresh_mta_planningfulfillmentgridrow': None, 'fresh_mta_planningchartprojection': None, 'fresh_mta_planningchartmember': None, 'fresh_mta_planningchartdisplay': None, 'fresh_mta_planningcustomprojection': None, 'fresh_mta_planningexcesscustomrow': None, 'fresh_mta_planningfulfillmentcustomrow': None, 'fresh_mta_planninggitprojection': None, 'fresh_mta_planninggitoccurrence': None, 'fresh_mta_planningexpeditegridprojection': None, 'fresh_mta_planningexpeditegridoccurrence': None, 'fresh_mta_planningexpeditetransitprojection': None, 'fresh_mta_planningexpeditetransitbase': None, 'fresh_mta_planningexpeditetransitmatch': None, 'fresh_mta_planningexpeditecustomprojection': None, 'fresh_mta_planningexpeditecustomoccurrence': None, 'fresh_mta_planningexpeditechartprojection': None, 'fresh_mta_planningexpeditechartmember': None, 'fresh_mta_planningexpediteprepostmember': None, 'fresh_mta_historypreparedprojection': None, 'fresh_mta_researchpreparedmasterreference': None, 'fresh_mta_researchpreparedhistoryreference': None, 'fresh_mta_buffergraphpreparedmembership': None, 'fresh_mta_researchavailabilitybandprojection': None, 'fresh_mta_boroapreparedreceipt': None, 'fresh_mta_boroapreparedrow': None, 'fresh_mta_reportaggregatereceipt': None, 'fresh_mta_reportscopemember': None, 'fresh_mta_guidedhistoryaggregate': None, 'fresh_mta_dailyuipublication': None, 'fresh_mta_dailyuipublicationattempt': ('publication_id', 'fresh_mta_dailyuipublication', 'run_id', 'run_id'), 'fresh_mta_planningsummaryreceipt': None, 'fresh_mta_planningsummarycontribution': ('receipt_id', 'fresh_mta_planningsummaryreceipt', 'id', 'run_id'), 'fresh_mta_planningsummaryattempt': None, 'fresh_mta_dailyreportgeneration': None}

# Typed shared tables qualify only the explicit derived image, not the table.
SHARED_IMAGES = {
 'btr_btrsnapshotforui':'closing/btr/BTRSnapshotForUI',
 'btr_buffertrendgraph':'closing/btr/BufferTrendGraph',
 'btr_chronicunavalabilitydata':'closing/btr/ChronicUnavalabilityData',
 'btr_dbmnormsuggestionsdata':'closing/btr/DBMNormSuggestionsData',
 'report_export_cell':None,'report_export_row':None,
}
LIFECYCLE_FIELDS = ('phase','status','candidate_selection_digest','prior_selection_digest','error','updated_at')


def prior_body():
    old=import_module('mta.runtime.migrations.0145_ingestion_revision_guards')
    body=old.SQL.split('CREATE FUNCTION mta.ingestion_watch()',1)[1].split('AS $$',1)[1].split('$$;',1)[0]
    return body.replace('UPDATE mta.fresh_mta_initializationcertification SET',
        'UPDATE mta.fresh_mta_ingestionrevisionstate SET').replace("WHERE status='CERTIFIED';",
        "WHERE initialization_id IN (SELECT initialization_id FROM mta.fresh_mta_initializationcertification WHERE status='CERTIFIED');")


# This is predicate selection, never a caller-set bypass or a new definer.
def classification():
    direct=[name for name,path in REPORT_TABLES.items() if path is None]
    cases=["WHEN TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME=ANY(ARRAY["+
        ','.join("'"+name+"'" for name in direct)+"]) THEN report_join='LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=N.run_id'; report_filter='TRUE';"]
    for table,(fk,parent,pk,owner) in ((n,p) for n,p in REPORT_TABLES.items() if p is not None):
        cases.append("WHEN TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='"+table+"' THEN report_join='LEFT JOIN mta."+
            parent+" P ON P."+pk+"=N."+fk+" LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=P."+owner+"'; report_filter='TRUE';")
    for table,path in SHARED_IMAGES.items():
        condition=("N.vf_image="+"'"+path+"'" if path else
            "EXISTS(SELECT 1 FROM jsonb_array_elements(R.production_manifest->'reports') S WHERE S ? 'deferred' AND N.vf_image IN ('reports/'||(S->>'stage')||'/ReportHeader','reports/'||(S->>'stage')||'/ReportRows'))")
        cases.append("WHEN TG_TABLE_SCHEMA='mta_state' AND TG_TABLE_NAME='"+table+"' THEN report_join='LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=N.vf_run_id'; report_filter="+"'"+condition.replace("'","''")+"';")
    return '\n'.join(cases)


def current_body():
    body=prior_body().replace('static_change boolean:=true;',
        "static_change boolean:=true; report_join text; report_filter text; qualified boolean; changes text;")
    added=r"""
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_dailyfeedattempt' AND TG_OP='UPDATE' THEN
  IF NOT EXISTS(SELECT to_jsonb(N)-ARRAY['phase','status','candidate_selection_digest','prior_selection_digest','error','updated_at'] FROM new_rows N
      EXCEPT ALL SELECT to_jsonb(O)-ARRAY['phase','status','candidate_selection_digest','prior_selection_digest','error','updated_at'] FROM old_rows O)
   AND NOT EXISTS(SELECT 1 FROM new_rows N LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=N.run_id
     WHERE R.id IS NULL OR R.kind<>'DAILY_CHAIN' OR R.status<>'SUCCEEDED' OR R.production_manifest->>'version' IS DISTINCT FROM '3')
   THEN RETURN NULL; END IF;
 END IF;
 CASE
"""+classification()+r"""
 ELSE report_join=NULL;
 END CASE;
 IF report_join IS NOT NULL THEN
  changes=CASE WHEN TG_OP='DELETE' THEN 'old_rows' ELSE 'new_rows' END;
  EXECUTE 'SELECT NOT EXISTS(SELECT 1 FROM '||changes||' N '||report_join||
    ' WHERE R.id IS NULL OR R.kind<>''DAILY_CHAIN'' OR R.status<>''SUCCEEDED'' OR R.production_manifest->>''version'' IS DISTINCT FROM ''3'' OR NOT ('||report_filter||'))'
    INTO qualified;
  IF qualified AND TG_OP='UPDATE' THEN
   EXECUTE 'SELECT NOT EXISTS(SELECT 1 FROM old_rows N '||report_join||
    ' WHERE R.id IS NULL OR R.kind<>''DAILY_CHAIN'' OR R.status<>''SUCCEEDED'' OR R.production_manifest->>''version'' IS DISTINCT FROM ''3'' OR NOT ('||report_filter||'))'
    INTO qualified;
  END IF;
  IF qualified THEN RETURN NULL; END IF;
 END IF;
"""
    return body.replace(" IF kind='immutable' THEN",added+" IF kind='immutable' THEN",1)

FORWARD='CREATE OR REPLACE FUNCTION mta.ingestion_watch() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mta AS $$'+current_body()+'$$;'
REVERSE='CREATE OR REPLACE FUNCTION mta.ingestion_watch() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mta AS $$'+prior_body()+'$$;'


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0156_daily_report_generation_guards')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
