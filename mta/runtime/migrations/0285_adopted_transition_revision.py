"""Use the existing storage-adoption revision rule for sealed transitions."""
from importlib import import_module

from django.db import migrations


prior = import_module('mta.runtime.migrations.0281_producer_history_storage')
replace_watch = import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership').transition
adoption = r"""
 IF (TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_operationalstatecut'
      OR TG_TABLE_SCHEMA='mta_state' AND TG_TABLE_NAME IN (RELATIONS))
    AND TG_OP IN ('INSERT','UPDATE')
    AND EXISTS(SELECT FROM pg_roles WHERE rolname=session_user AND rolsuper) THEN
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_operationalstatecut'
    AND TG_OP IN ('INSERT','UPDATE') THEN
  IF NOT EXISTS(SELECT FROM new_rows N JOIN mta.fresh_mta_operationalstatecut C ON C.id=N.id
     WHERE mta.history_transition_adoption(C) IS NULL)
  THEN RETURN NULL; END IF;
 ELSIF TG_TABLE_SCHEMA='mta_state' AND TG_TABLE_NAME IN (RELATIONS)
    AND TG_OP IN ('INSERT','UPDATE') THEN
  IF TG_OP='INSERT' THEN
   IF NOT EXISTS(SELECT FROM (SELECT DISTINCT cut_id FROM new_rows) N
     JOIN mta.fresh_mta_operationalstatecut C ON C.id=N.cut_id
     WHERE mta.history_transition_adoption(C) IS NULL)
   THEN RETURN NULL; END IF;
  ELSE
   IF NOT EXISTS(SELECT FROM (SELECT DISTINCT closing_cut_id FROM new_rows) N
     JOIN mta.fresh_mta_operationalstatecut C ON C.id=N.closing_cut_id
     WHERE mta.history_transition_adoption(C) IS NULL)
   THEN RETURN NULL; END IF;
  END IF;
 END IF;
 END IF;
""".replace('RELATIONS', prior.relations)
sql = replace_watch(prior.NEW, prior.replace(prior.NEW,
    " IF kind='immutable' THEN", adoption+" IF kind='immutable' THEN"))


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0284_adopt_sealed_history_transition')]
    operations = [migrations.RunSQL(sql)]
