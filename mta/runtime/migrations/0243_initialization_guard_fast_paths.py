"""Equivalent guard fast paths; retain every trigger and ownership predicate."""
from importlib import import_module

from django.db import migrations

effects = import_module('mta.runtime.migrations.0179_prepared_effect_ownership')
current = import_module('mta.runtime.migrations.0186_scoped_current_copies')

OLD_EFFECT = ('CREATE OR REPLACE FUNCTION mta.guard_prepared_effect()' +
              effects.SQL.split('CREATE FUNCTION mta.guard_prepared_effect()', 1)[1]
              .split('$guard$;', 1)[0] + '$guard$;')
ANCHOR = " row_value=CASE WHEN TG_OP='DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;"
CAPTURE_END = "  RAISE EXCEPTION 'Scoped capture effect evidence requires its owned transaction'; END IF;"
NEXT = " IF TG_ARGV[0]='capture' THEN\n  SELECT C.source_id"
assert OLD_EFFECT.count(ANCHOR) == OLD_EFFECT.count(CAPTURE_END) == OLD_EFFECT.count(NEXT) == 1
NEW_EFFECT = OLD_EFFECT.replace(ANCHOR, " IF TG_ARGV[0]='capture' THEN\n" + ANCHOR, 1)
NEW_EFFECT = NEW_EFFECT.replace(CAPTURE_END, CAPTURE_END + '\n END IF;', 1)
NEW_EFFECT = NEW_EFFECT.replace(NEXT,
    " IF TG_ARGV[0] IS DISTINCT FROM 'capture' THEN\n" + ANCHOR + '\n END IF;\n' + NEXT, 1)

OLD_CURRENT = 'CREATE OR REPLACE FUNCTION mta.guard_active_mdm_current()' + current._current
SCOPED = ''' IF mta.pending_scoped_current(owner) IS NOT NULL THEN
  -- The separate scoped-current row guard validates the exact phase partition,
  -- even for sources outside this original protected-source predicate.
  IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
 END IF;'''
assert OLD_CURRENT.count(SCOPED) == 1
NEW_CURRENT = OLD_CURRENT.replace(SCOPED,
    " IF nullif(current_setting('fresh.mdm_current_run',true),'') IS NOT NULL THEN\n" +
    SCOPED + '\n END IF;', 1)


def replace(editor, old_effect, new_effect, old_current, new_current):
    with editor.connection.cursor() as cursor:
        cursor.execute("SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_initializationcertification)")
        if cursor.fetchone()[0]:
            raise ValueError('Initialization guard transport release requires a fresh uncertified installation')
        for name, old, new, delimiter in (
                ('guard_prepared_effect', old_effect, new_effect, '$guard$'),
                ('guard_active_mdm_current', old_current, new_current, '$$')):
            cursor.execute("SELECT prosrc FROM pg_proc WHERE oid=%s::regprocedure", ['mta.' + name + '()'])
            if cursor.fetchone() != (old.split(delimiter)[1],):
                raise ValueError('Initialization guard predecessor differs: ' + name)
            cursor.execute(new)


def forward(apps, editor):
    replace(editor, OLD_EFFECT, NEW_EFFECT, OLD_CURRENT, NEW_CURRENT)


def reverse(apps, editor):
    replace(editor, NEW_EFFECT, OLD_EFFECT, NEW_CURRENT, OLD_CURRENT)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0242_generic_read_sql_aliases')]
    operations = [migrations.RunPython(forward, reverse)]
