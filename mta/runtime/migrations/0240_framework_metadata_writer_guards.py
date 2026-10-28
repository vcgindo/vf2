"""Cover framework metadata created after the original dynamic guard install.

Keep the established operational classification and every existing guard.
Reversal would remove coverage required by the earlier ingestion contract.
"""
from django.db import migrations


SPECS = (
    ('insert', 'INSERT', 'NEW TABLE AS new_rows', 4, None, 'new_rows'),
    ('update', 'UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows', 16, 'old_rows', 'new_rows'),
    ('delete', 'DELETE', 'OLD TABLE AS old_rows', 8, 'old_rows', None),
    ('truncate', 'TRUNCATE', '', 32, None, None),
)


def install(apps, editor):
    if editor.connection.vendor != 'postgresql':
        raise RuntimeError('Framework writer guards require PostgreSQL')
    with editor.connection.cursor() as cursor:
        cursor.execute("SELECT relkind FROM pg_class WHERE oid=to_regclass('mta.django_content_type')")
        if cursor.fetchone() != ('r',):
            raise ValueError('Existing migrated content-type table required')
        cursor.execute("SELECT t.tgname,t.tgenabled,n.nspname,p.proname,"
            "encode(t.tgargs,'escape'),t.tgtype,t.tgnargs,t.tgqual::text,"
            "t.tgattr::text,t.tgoldtable,t.tgnewtable FROM pg_trigger t "
            "JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE t.tgrelid='mta.django_content_type'::regclass "
            "AND t.tgname LIKE 'ingestion_watch_%' ORDER BY t.tgname")
        actual = cursor.fetchall()
        expected = sorted((
            'ingestion_watch_' + suffix, 'O', 'mta', 'ingestion_watch',
            'operational\\000', kind, 1, None, '', old, new,
        ) for suffix, _op, _ref, kind, old, new in SPECS)
        if actual:
            if actual != expected:
                raise ValueError('Existing framework writer guards differ; no replacement')
            return
        for suffix, operation, reference, _kind, _old, _new in SPECS:
            cursor.execute('CREATE TRIGGER ' + editor.quote_name('ingestion_watch_' + suffix)
                + ' AFTER ' + operation + ' ON mta.django_content_type'
                + (' REFERENCING ' + reference if reference else '')
                + " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational')")


class Migration(migrations.Migration):
    dependencies = [
        ('fresh_mta', '0239_production_generic_scope_read'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]
    operations = [migrations.RunPython(install)]
