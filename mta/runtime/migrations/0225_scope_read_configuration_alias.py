"""Avoid the existing PL/pgSQL Q record when matching request configuration.

Recognize the two exact observed development states: applied0224, or its prior
guard after a reverse attempt was stopped by append-only migration history.
Never delete/fake migration history or alter any retained reference.
"""
from importlib import import_module
from django.db import migrations

prior = import_module('mta.runtime.migrations.0224_uptodbm_bpr_read_configuration')
assert prior.BODY.count("request_node->'object')) Q") == 1
assert prior.BODY.count('(Q.schema,Q.scope)') == 1
BODY = prior.BODY.replace("request_node->'object')) Q", "request_node->'object')) RequestConfiguration")
BODY = BODY.replace('(Q.schema,Q.scope)', '(RequestConfiguration.schema,RequestConfiguration.scope)')
SQL = prior.replace(prior.BODY,BODY)
expected = 'P.prosrc=$expected$'+prior.BODY+'$expected$'
assert SQL.count(expected) == 1
SQL = SQL.replace(expected,'('+expected+' OR P.prosrc=$prior$'+prior.OLD+'$prior$)')


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0224_uptodbm_bpr_read_configuration')]
    operations = [migrations.RunSQL(SQL)]
