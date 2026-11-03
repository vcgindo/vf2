"""Typed Norm-log and sorted importer occurrences under the existing cut guards."""
from importlib import import_module

from django.db import migrations


prior = import_module('mta.runtime.migrations.0274_complete_remark_history_storage')
base = import_module('mta.runtime.migrations.0270_bpr_history_storage')
replace = prior.replace
spec = (
    ('importer', 'RejectedMaster', 'RejectionDate'),
    ('importer', 'RetiredNormsTbl', 'Event_Date'),
    ('dbm', 'NormChangeLogTbl', 'NormChangeDate'),
)
families = ','.join(f"'closing/{section}/{name}'" for section,name,_ in spec)
relations = ','.join(f"'history_{section}_{name.lower()}'" for section,name,_ in spec)
importer_families = "'closing/importer/RejectedMaster','closing/importer/RetiredNormsTbl'"

lookup = replace(prior.lookup, "'closing/complete/InTransitWhereAboutsRemarks')",
    "'closing/complete/InTransitWhereAboutsRemarks',"+families+")")
fields = replace(base.function('dated_history_fields_valid('), "'end_position','closing_cut_id')",
    "'end_position','closing_cut_id','history_sort_key')")
seal = replace(prior.seal, "DECLARE c mta.", "DECLARE transition_cut boolean; c mta.")
seal = replace(seal, " b=c.root_body::jsonb;",
    " b=c.root_body::jsonb;\n transition_cut=c.family IN ("+families+");")
seal = replace(seal, "jsonb_object_keys(b))<>17",
    "jsonb_object_keys(b))<>(CASE WHEN transition_cut THEN 18 ELSE 17 END)")
seal = replace(seal, "b->>'format' IS DISTINCT FROM 'dated-history-occurrences-v1'",
    "b->>'format' IS DISTINCT FROM (CASE WHEN transition_cut THEN 'dated-history-occurrences-v2'"
    " ELSE 'dated-history-occurrences-v1' END)")
seal = replace(seal, " IF c.position=0 THEN", f"""
 IF transition_cut THEN
  IF c.family IN ({importer_families}) AND c.position>0 THEN
   IF removed<>0 OR jsonb_typeof(b->'sorted_prefix') IS DISTINCT FROM 'number'
     OR coalesce(b->>'sorted_prefix','') !~ '^(0|[1-9][0-9]*)$'
     OR (b->>'sorted_prefix')::bigint>facts
     OR c.family='closing/importer/RetiredNormsTbl' AND (
       (b->>'sorted_prefix')::bigint<>facts OR (b->>'count')::bigint>0
       AND NOT (b->'fields' @> '[["Event_Type","Event_Type","int"]]'::jsonb))
   THEN RAISE EXCEPTION 'Importer history sort boundary differs'; END IF;
  ELSIF b->'sorted_prefix' IS DISTINCT FROM 'null'::jsonb THEN
   RAISE EXCEPTION 'History cut does not use a sorted prefix';
  END IF;
 END IF;
 IF c.position=0 THEN""")
seal = replace(seal, "image->>'storage_format' IS DISTINCT FROM 'dated-history-occurrences-v1'",
    "image->>'storage_format' IS DISTINCT FROM b->>'format'")
seal = replace(seal, "ELSE upper(split_part(c.family",
    "WHEN c.family IN ("+importer_families+") THEN 'Importer/'||split_part(c.family,'/',3) "
    "ELSE upper(split_part(c.family")

tables = ''
for section,name,date_field in spec:
    relation = f'{section}_{name.lower()}'
    sql = base.table.replace('history_bpr_dailyconsumption','history_'+relation)
    sql = sql.replace('mta_state.bpr_dailyconsumption','mta_state.'+relation).replace('ReportDate',date_field)
    if section == 'importer':
        sql = replace(sql, ' ADD COLUMN end_position bigint,',
            ' ADD COLUMN history_sort_key text COLLATE "C" NOT NULL,\n ADD COLUMN end_position bigint,')
    tables += sql

OLD = prior.NEW
NEW = replace(OLD,"'closing/complete/InTransitWhereAboutsRemarks')",
    "'closing/complete/InTransitWhereAboutsRemarks',"+families+")",2)
NEW = replace(NEW,"'history_complete_bpr_intransitwhereaboutsremarks')",
    "'history_complete_bpr_intransitwhereaboutsremarks',"+relations+")")
SQL = lookup+fields+seal+tables+prior.transition(OLD,NEW)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0280_producer_history_families')]
    # Accepted typed occurrences remain available only with a forward codec.
    operations = [migrations.RunSQL(SQL)]
