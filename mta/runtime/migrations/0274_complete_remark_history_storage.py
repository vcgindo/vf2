"""Prune-only retained complete remarks; live remarks keep separate owners."""
from importlib import import_module

from django.db import migrations


prior=import_module('mta.runtime.migrations.0272_order_closure_history_storage')
base=import_module('mta.runtime.migrations.0270_bpr_history_storage')
spec=(('BPRReport_RemarkDetails','RemarkDate'),
      ('OpenExpeditRequestRemarksHistory','RemarkDate'),
      ('InTransitWhereAboutsRemarks','RemarksDate'))
families=','.join("'closing/complete/"+name+"'" for name,_ in spec)
relations=','.join("'history_complete_bpr_"+name.lower()+"'" for name,_ in spec)


def replace(text,old,new,count=1):
    assert text.count(old)==count,old
    return text.replace(old,new)


lookup=replace(prior.lookup,"'closing/orders/SpikeOrderClosureHistory')",
               "'closing/orders/SpikeOrderClosureHistory',"+families+")")
lookup=replace(lookup,"ELSE 'history_'",
    ''.join("WHEN family='closing/complete/"+name+"' THEN 'history_complete_bpr_"+name.lower()+"' " for name,_ in spec)+
    "ELSE 'history_'")
seal=replace(prior.seal,"ELSE upper(split_part(c.family",
    ''.join("WHEN c.family='closing/complete/"+name+"' THEN 'complete/BPR/"+name+"' " for name,_ in spec)+
    "ELSE upper(split_part(c.family")
insert=base.function('dated_history_insert(')
insert=replace(insert,' IF c.position>0 AND EXISTS(',
    " IF c.position>0 AND c.family IN ("+families+") THEN\n"
    " RAISE EXCEPTION 'Complete remark history cannot append business rows'; END IF;\n"
    ' IF c.position>0 AND EXISTS(')
tables=''
for name,field in spec:
    table=base.table.replace('history_bpr_dailyconsumption','history_complete_bpr_'+name.lower())
    table=table.replace('mta_state.bpr_dailyconsumption','mta_state.complete_bpr_'+name.lower())
    tables+=table.replace('ReportDate',field)

OLD=prior.NEW
NEW=replace(OLD,"'closing/orders/SpikeOrderClosureHistory')",
            "'closing/orders/SpikeOrderClosureHistory',"+families+")",2)
NEW=replace(NEW,"'history_bpr_spikeorderclosurehistory')",
            "'history_bpr_spikeorderclosurehistory',"+relations+")")
NEW=replace(NEW,"ELSE 'history_'",
    ''.join("WHEN C.family='closing/complete/"+name+"' THEN 'history_complete_bpr_"+name.lower()+"' " for name,_ in spec)+
    "ELSE 'history_'")
transition=import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership').transition
SQL=lookup+seal+insert+tables+transition(OLD,NEW)


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0273_complete_remark_history_families')]
    operations=[migrations.RunSQL(SQL)]
