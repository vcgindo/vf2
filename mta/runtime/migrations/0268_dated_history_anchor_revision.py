"""Exact position-zero history adoption changes storage, not business epochs."""
from importlib import import_module

from django.db import migrations


OLD = import_module('mta.runtime.migrations.0254_rationing_anchor_revision_ownership').NEW
FAMILIES = ("'closing/dbm/DailyConsumption','closing/dbm/OrderData',"
    "'closing/dbm/OrderDataSummary','closing/dbm/SuggestionsLog',"
    "'closing/dbm/DiscardedSuggestions','closing/dbm/SpikeReport','closing/dbm/SuspendHistory'")
ANCHOR = '''
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_operationalstatecut'
    AND TG_OP IN ('INSERT','UPDATE') THEN
  IF NOT EXISTS(SELECT FROM new_rows N WHERE N.position<>0 OR N.family NOT IN ('''+FAMILIES+'''))
  THEN RETURN NULL; END IF;
 ELSIF TG_TABLE_SCHEMA='mta_state' AND TG_OP='INSERT'
    AND TG_TABLE_NAME IN ('history_dbm_dailyconsumption','history_dbm_orderdata',
      'history_dbm_orderdatasummary','history_dbm_suggestionslog','history_dbm_discardedsuggestions',
      'history_dbm_spikereport','history_dbm_suspendhistory') THEN
  IF NOT EXISTS(SELECT FROM new_rows N LEFT JOIN mta.fresh_mta_operationalstatecut C ON C.id=N.cut_id
      WHERE C.id IS NULL OR C.position<>0 OR C.family NOT IN ('''+FAMILIES+''')
       OR TG_TABLE_NAME<>('history_dbm_'||lower(split_part(C.family,'/',3))))
  THEN RETURN NULL; END IF;
 END IF;
'''
assert OLD.count(" IF kind='immutable' THEN") == 1
NEW = OLD.replace(" IF kind='immutable' THEN", ANCHOR+" IF kind='immutable' THEN", 1)
transition = import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership').transition


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0267_dated_history_pair_access')]
    operations = [migrations.RunSQL(transition(OLD, NEW))]
