"""Require a completed parent on the fresh-source SQL activation branch."""
from importlib import import_module
from django.db import migrations
previous=import_module('mta.runtime.migrations.0134_native_closing_projection_guards')
a=previous.FORWARD.index('CREATE FUNCTION mta.valid_closing_projection')
b=previous.FORWARD.index('CREATE FUNCTION mta.guard_closing_projection')
REVERSE=previous.FORWARD[a:b].replace('CREATE FUNCTION','CREATE OR REPLACE FUNCTION',1)
anchor="JOIN mta.fresh_mta_mdmdailyinputcapture D ON D.run_id=Q.run_id\n    WHERE Q.run_id=R.predecessor_id"
assert REVERSE.count(anchor)==1
FORWARD=REVERSE.replace(anchor,"JOIN mta.fresh_mta_mdmdailyinputcapture D ON D.run_id=Q.run_id\n    JOIN mta.fresh_mta_calculationrun B ON B.id=Q.run_id\n    WHERE B.status='SUCCEEDED' AND Q.run_id=R.predecessor_id")
class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0134_native_closing_projection_guards')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
