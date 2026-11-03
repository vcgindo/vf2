"""Append-only order closure occurrences, retaining the BPR physical owner.

Old cut descriptors retain their integer wire flags; successors authenticate
the original producer's boolean projection. No accepted payload is rewritten.
"""
from importlib import import_module

from django.db import migrations


prior = import_module('mta.runtime.migrations.0270_bpr_history_storage')


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


family = 'closing/orders/SpikeOrderClosureHistory'
lookup = replace_once(prior.lookup, "'closing/bpr/DailyConsumption')",
                      "'closing/bpr/DailyConsumption','"+family+"')")
lookup = replace_once(lookup, "'history_'||split_part(family,'/',2)||'_'||lower(split_part(family,'/',3))",
    "CASE WHEN family='"+family+"' THEN 'history_bpr_spikeorderclosurehistory' "
    "ELSE 'history_'||split_part(family,'/',2)||'_'||lower(split_part(family,'/',3)) END")
seal = replace_once(prior.seal,
    "(upper(split_part(c.family,'/',2))||'/'||split_part(c.family,'/',3))",
    "(CASE WHEN c.family='"+family+"' THEN 'BPR/SpikeOrderClosureHistory' "
    "ELSE upper(split_part(c.family,'/',2))||'/'||split_part(c.family,'/',3) END)")
table = prior.table.replace('history_bpr_dailyconsumption','history_bpr_spikeorderclosurehistory')
table = table.replace('mta_state.bpr_dailyconsumption','mta_state.bpr_spikeorderclosurehistory')
table = table.replace('ReportDate','ClosureDate')

OLD = prior.NEW
assert OLD.count("'closing/bpr/DailyConsumption')") == 2
NEW = OLD.replace("'closing/bpr/DailyConsumption')", "'closing/bpr/DailyConsumption','"+family+"')")
NEW = replace_once(NEW, "'history_bpr_dailyconsumption')",
                   "'history_bpr_dailyconsumption','history_bpr_spikeorderclosurehistory')")
NEW = replace_once(NEW, "('history_'||split_part(C.family,'/',2)||'_'||lower(split_part(C.family,'/',3)))",
    "(CASE WHEN C.family='"+family+"' THEN 'history_bpr_spikeorderclosurehistory' "
    "ELSE 'history_'||split_part(C.family,'/',2)||'_'||lower(split_part(C.family,'/',3)) END)")
SQL = lookup+seal+table+prior.transition(OLD,NEW)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0271_order_closure_history_family')]
    operations = [migrations.RunSQL(SQL)]
