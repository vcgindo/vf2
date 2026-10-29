"""Owner-only transaction dispatch for admitted current-master production.

Every original body remains the default diagnostic/unadmitted path. No trigger,
grant, revision producer or receipt writer is removed or disabled.
"""
from importlib import import_module
from django.db import migrations

fast = import_module('mta.runtime.migrations.0243_initialization_guard_fast_paths')
scoped = import_module('mta.runtime.migrations.0190_day_final_current_copies')
copies = import_module('mta.runtime.migrations.0186_scoped_current_copies')

ORIGINALS = (
    ('guard_active_mdm_current', fast.NEW_CURRENT, '$$', 'row'),
    ('guard_prepared_effect', fast.NEW_EFFECT, '$guard$', 'current'),
    ('guard_scoped_current_copy',
     'CREATE OR REPLACE FUNCTION mta.guard_scoped_current_copy()' + scoped._guard + '$guard$;',
     '$guard$', 'row'),
    ('guard_location_projection_statement',
     'CREATE OR REPLACE FUNCTION mta.guard_location_projection_statement()' + copies._projection,
     '$$', 'statement'),
)


def admitted_definition(original, delimiter, kind, owner):
    """Inline the unchanged original body after one private-context dispatch."""
    literal = "'" + owner.replace("'", "''") + "'"
    condition = ("CURRENT_USER=" + literal +
        " AND pg_catalog.current_setting('fresh.accepted_current_xid',true)="
        "pg_catalog.txid_current()::text"
        " AND nullif(pg_catalog.current_setting('fresh.accepted_current_run',true),'')="
        "nullif(pg_catalog.current_setting('fresh.mdm_current_run',true),'')")
    if kind == 'current':
        condition += " AND TG_ARGV[0]='current'"
    elif kind == 'row':
        condition += " AND TG_OP<>'TRUNCATE'"
    returned = ('RETURN NULL;' if kind == 'statement' else
                "IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;")
    dispatch = '\n IF ' + condition + ' THEN ' + returned + ' END IF;'
    parts = original.split(delimiter)
    assert len(parts) == 3 and parts[1].count('\nBEGIN\n') == 1
    parts[1] = parts[1].replace('\nBEGIN\n', '\nBEGIN' + dispatch + '\n', 1)
    return delimiter.join(parts)


def replace(editor, *, reverse=False):
    with editor.connection.cursor() as cursor:
        for name, original, delimiter, kind in ORIGINALS:
            cursor.execute('SELECT P.prosrc,pg_catalog.pg_get_userbyid(P.proowner) '
                'FROM pg_catalog.pg_proc P WHERE P.oid=%s::regprocedure', ['mta.' + name + '()'])
            current = cursor.fetchone()
            if current is None:
                raise ValueError('Accepted current guard predecessor missing: ' + name)
            body, owner = current
            admitted = admitted_definition(original, delimiter, kind, owner)
            before, after = (admitted, original) if reverse else (original, admitted)
            if body != before.split(delimiter)[1]:
                raise ValueError('Accepted current guard predecessor differs: ' + name)
            cursor.execute(after)


def forward(apps, editor):
    replace(editor)


def reverse(apps, editor):
    replace(editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0243_initialization_guard_fast_paths')]
    operations = [migrations.RunPython(forward, reverse)]
