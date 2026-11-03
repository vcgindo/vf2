"""An exact storage anchor adds representation, not a business revision.

The existing pending-cut, immutable-source, typed-row and deferred commitment
guards still own every write. This predicate changes only revision accounting
for position-zero anchors; ordinary cut/delta writes retain their watches.
"""
from importlib import import_module

from django.db import migrations


prior = import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership')
OLD = import_module('mta.runtime.migrations.0246_btr_scope_dimension_ingestion_ownership').NEW
ANCHOR = r'''
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_operationalstatecut'
    AND TG_OP IN ('INSERT','UPDATE') THEN
  IF NOT EXISTS(SELECT 1 FROM new_rows N WHERE N.position<>0 OR N.family<>'rationing_history')
  THEN RETURN NULL; END IF;
 ELSIF TG_TABLE_SCHEMA='mta_state' AND TG_OP='INSERT'
    AND TG_TABLE_NAME IN ('rationing_fact','rationing_lifetime') THEN
  IF TG_TABLE_NAME='rationing_fact' THEN
   IF NOT EXISTS(SELECT 1 FROM new_rows N LEFT JOIN mta.fresh_mta_operationalstatecut C ON C.id=N.cut_id
       WHERE C.id IS NULL OR C.position<>0 OR C.family<>'rationing_history')
   THEN RETURN NULL; END IF;
  ELSE
   IF NOT EXISTS(SELECT 1 FROM new_rows N LEFT JOIN mta.fresh_mta_operationalstatecut C ON C.id=N.fact_cut_id
       WHERE C.id IS NULL OR C.position<>0 OR C.family<>'rationing_history')
   THEN RETURN NULL; END IF;
  END IF;
 END IF;
'''
assert OLD.count(" IF kind='immutable' THEN") == 1
NEW = OLD.replace(" IF kind='immutable' THEN", ANCHOR+" IF kind='immutable' THEN", 1)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0253_anchor_final_initialization')]
    operations = [migrations.RunSQL(prior.transition(OLD, NEW))]
