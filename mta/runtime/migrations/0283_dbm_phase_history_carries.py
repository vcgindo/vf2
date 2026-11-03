"""Reuse the accepted opening cuts for four DBM phase images."""
from importlib import import_module

from django.db import migrations


prior = import_module('mta.runtime.migrations.0282_phase_history_transitions')
names = ('DailyConsumption', 'OrderData', 'SuspendHistory', 'SpikeReport')
families = ','.join("'closing/dbm/"+name+"'" for name in names)
sql = prior.SQL.replace("'closing/dbm/NormChangeLogTbl')",
    "'closing/dbm/NormChangeLogTbl',"+families+")")
sql = sql.replace("OR I.key NOT LIKE", """OR I.value->>'family' IN ("""+families+""")
          AND (manifest->>'phase' IS DISTINCT FROM 'DBM'
            OR I.value->>'image' IS DISTINCT FROM 'phase/DBM/dbm/'||split_part(I.value->>'family','/',3))
        OR I.key NOT LIKE""")
assert sql != prior.SQL and families in sql
sql += """
ALTER TABLE mta_state.phase_historychange DROP CONSTRAINT phase_historychange_vf_image_check;
ALTER TABLE mta_state.phase_historychange ADD CONSTRAINT phase_historychange_vf_image_check CHECK (
 vf_image ~ '^phase/(PRE_BPR|BPR|DBM)/history-changes/(importer/(RejectedMaster|RetiredNormsTbl)|dbm/NormChangeLogTbl)$'
 OR vf_image ~ '^phase/DBM/history-changes/dbm/(DailyConsumption|OrderData|SuspendHistory|SpikeReport)$');
"""


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0282_phase_history_transitions')]
    operations = [migrations.RunSQL(sql)]
