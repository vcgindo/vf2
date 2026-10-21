"""Wide trend matrices rebuild from atomic BPR/norm facts after business closure.

Typed histories and scalar category/expedite effects stay operational and atomic.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from importlib import import_module
from django.db import migrations

revision=import_module('mta.runtime.migrations.0160_report_consumer_source_ownership')
guard=import_module('mta.runtime.migrations.0161_report_generation_insert_serialization')
TRENDS=('BufferTrendReport','BufferTrendReportEcon','BufferTrendDispatch',
    'BufferTrendPhysicalInv','BPPTrendTech','BPPTrendEcon','BPPTrendDispatch','BPPTrendPhysicalInv')


def trend_cases():
    return '\n'.join("WHEN TG_TABLE_SCHEMA='mta_state' AND TG_TABLE_NAME='btr_"+name.lower()+"' THEN report_join='LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=N.vf_run_id'; report_filter='N.vf_image=''closing/btr/"+name+"''';" for name in TRENDS)


def current_body():
    return revision.current_body().replace(' ELSE report_join=NULL;',trend_cases()+'\n ELSE report_join=NULL;',1)


new_guard=guard.new_rows.replace("ELSE join_sql='R.id=N.run_id'; filter_sql='TRUE';",'\n'.join(
    "WHEN TG_TABLE_SCHEMA='mta_state' AND TG_TABLE_NAME='btr_"+name.lower()+"' THEN join_sql='R.id=N.vf_run_id'; filter_sql='N.vf_image=''closing/btr/"+name+"''';" for name in TRENDS)+"\nELSE join_sql='R.id=N.run_id'; filter_sql='TRUE';",1)
FORWARD=revision.function(current_body())+new_guard
REVERSE=''
for name in TRENDS:
    table='mta_state.btr_'+name.lower()
    for op,ref in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),('DELETE','OLD TABLE AS old_rows')):
        trigger='v3_report_'+op.lower()
        FORWARD+='CREATE TRIGGER '+trigger+' AFTER '+op+' ON '+table+' REFERENCING '+ref+' FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_v3_derived_report_rows();\n'
        REVERSE+='DROP TRIGGER '+trigger+' ON '+table+';\n'
REVERSE+=revision.function(revision.current_body())+guard.new_rows


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0161_report_generation_insert_serialization')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
