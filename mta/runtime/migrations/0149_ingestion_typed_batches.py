"""Frozen typed daily-feed tables.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import json
from pathlib import Path

from django.db import migrations


DECLARATION = Path(__file__).resolve().parents[2] / 'config/daily_batch_storage_v1.json'
RAW = DECLARATION.read_bytes()
if hashlib.sha256(RAW).hexdigest() != '5cafca5743789b12d190a9702dff863b68eda505a16197e7d1de62c6c2f83ca7':
    raise ValueError('Frozen daily batch storage declaration differs')
TABLES = json.loads(RAW)['feeds']
PG_TYPES = {'int':'bigint','bigint':'bigint','bit':'boolean','date':'date',
    'datetime':'timestamp without time zone','datetimetz':'timestamp with time zone',
    'decimal':'numeric','numeric':'numeric','float':'double precision','real':'double precision',
    'nchar':'text','nvarchar':'text','varchar':'text','xml':'text'}


def q(value):
    return '"' + value.replace('"', '""') + '"'


GUARDS = r"""
CREATE FUNCTION mta.daily_batch_insert_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,mta AS $$
DECLARE expected text; attempt_status text; attempt_phase text; facts jsonb;
BEGIN
 expected=current_setting('fresh.daily_batch',true);
 IF expected IS NULL OR expected='' OR expected::uuid<>NEW.vf_attempt_id THEN
  RAISE EXCEPTION 'Daily batch insert requires transaction-local attempt owner';
 END IF;
 SELECT status,phase,accepted_facts INTO attempt_status,attempt_phase,facts
 FROM mta.fresh_mta_dailyfeedattempt WHERE attempt_id=NEW.vf_attempt_id FOR SHARE;
 IF NOT FOUND OR attempt_status<>'RUNNING' OR attempt_phase<>'VALIDATE' OR facts<>'{}'::jsonb THEN
  RAISE EXCEPTION 'Daily batch insert requires current unsealed validation attempt';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.daily_batch_update_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Daily batch rows are immutable'; END $$;
CREATE FUNCTION mta.daily_batch_delete_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Daily batch rows are immutable'; END $$;
CREATE FUNCTION mta.daily_batch_truncate_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Daily batch rows are immutable'; END $$;
"""


def statements():
    result = [GUARDS]
    for feed in TABLES.values():
        columns = ', '.join(q(name) + ' ' + PG_TYPES[kind] for name, kind in feed['columns'])
        table = 'mta_state.' + q(feed['table'])
        result.append('CREATE TABLE ' + table + ' ('
            'vf_attempt_id uuid NOT NULL REFERENCES mta.fresh_mta_dailyfeedattempt(attempt_id) ON DELETE RESTRICT, '
            'vf_ordinal bigint NOT NULL, ' + columns + ', PRIMARY KEY(vf_attempt_id,vf_ordinal))')
        for operation, timing, event, level in (
                ('insert','BEFORE','INSERT','ROW'), ('update','BEFORE','UPDATE','ROW'),
                ('delete','BEFORE','DELETE','ROW'), ('truncate','BEFORE','TRUNCATE','STATEMENT')):
            result.append('CREATE TRIGGER daily_batch_' + operation + ' ' + timing + ' ' + event +
                ' ON ' + table + ' FOR EACH ' + level +
                ' EXECUTE FUNCTION mta.daily_batch_' + operation + '_guard()')
    return ';\n'.join(result) + ';'


def reverse():
    result = ['DROP TABLE mta_state.' + q(feed['table'])
              for feed in reversed(list(TABLES.values()))]
    result.extend('DROP FUNCTION mta.daily_batch_' + operation + '_guard()'
                  for operation in ('truncate','delete','update','insert'))
    return ';\n'.join(result) + ';'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0148_ingestion_daily_preparation')]
    operations = [migrations.RunSQL(statements(), reverse())]
