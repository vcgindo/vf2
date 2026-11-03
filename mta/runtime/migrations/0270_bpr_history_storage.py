"""Independent BPR consumption occurrences; no DBM or accepted-image rewrite.

Reuse the immutable seven-family guard bodies, extending only the exact BPR
family/table and source binding. Required on fresh and upgraded databases.
Accepted occurrence storage cannot be discarded by a schema downgrade.
"""
from importlib import import_module

from django.db import migrations


prior = import_module('mta.runtime.migrations.0266_dated_history_storage')


def function(name):
    start = prior.SQL.index('CREATE FUNCTION mta.'+name)
    end = prior.SQL.index('REVOKE ALL ON FUNCTION mta.'+name, start)
    return prior.SQL[start:end].replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)


lookup = function('dated_history_table(')
lookup = lookup.replace("'closing/dbm/SuspendHistory')", "'closing/dbm/SuspendHistory','closing/bpr/DailyConsumption')")
lookup = lookup.replace("'history_dbm_'||lower", "'history_'||split_part(family,'/',2)||'_'||lower")
seal = function('require_dated_history_seal(')
seal = seal.replace("'input/opening/state/dbm/'||split_part(c.family,'/',3)",
                    "'input/opening/state/'||split_part(c.family,'/',2)||'/'||split_part(c.family,'/',3)")
seal = seal.replace("('DBM/'||split_part(c.family,'/',3))",
                    "(upper(split_part(c.family,'/',2))||'/'||split_part(c.family,'/',3))")
assert 'state/dbm/' not in seal and "('DBM/'" not in seal

start = prior.SQL.index('CREATE TABLE mta_state.history_dbm_dailyconsumption ')
end = prior.SQL.index('CREATE TABLE mta_state.history_dbm_orderdata ', start)
table = prior.SQL[start:end].replace('history_dbm_dailyconsumption','history_bpr_dailyconsumption')
table = table.replace('mta_state.dbm_dailyconsumption','mta_state.bpr_dailyconsumption')

OLD = import_module('mta.runtime.migrations.0268_dated_history_anchor_revision').NEW
NEW = OLD.replace("'closing/dbm/SuspendHistory')", "'closing/dbm/SuspendHistory','closing/bpr/DailyConsumption')")
NEW = NEW.replace("'history_dbm_spikereport','history_dbm_suspendhistory')",
                  "'history_dbm_spikereport','history_dbm_suspendhistory','history_bpr_dailyconsumption')")
NEW = NEW.replace("('history_dbm_'||lower(split_part(C.family,'/',3)))",
                  "('history_'||split_part(C.family,'/',2)||'_'||lower(split_part(C.family,'/',3)))")
assert NEW.count("'closing/bpr/DailyConsumption'") == 2
transition = import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership').transition
SQL = lookup+seal+table+transition(OLD,NEW)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0269_bpr_history_family')]
    operations = [migrations.RunSQL(SQL)]
