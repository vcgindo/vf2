"""Register the fixed typed daily batch tables in fact revision coverage.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from django.db import migrations


TABLES = (
    'batch_dailydataraw', 'batch_masterdatarawnonnms', 'batch_nonormmasterraw',
    'batch_acceptednorms', 'batch_orderdata', 'batch_orderfeed',
    'batch_distributortransactions', 'batch_vendortransactions', 'batch_intransitraw',
    'batch_transporters', 'batch_masterdataraw', 'batch_sobdataraw',
    'batch_moqdataraw1', 'batch_moqdataraw2', 'batch_additionaldatastockforreqcalc',
    'batch_consumer_requests', 'batch_consumer_remarks_bpr',
    'batch_consumer_remarks_bor', 'batch_consumer_remarks_boroa',
)


def install(apps, editor):
    if editor.connection.vendor != 'postgresql':
        raise RuntimeError('Ingestion guards require PostgreSQL')
    q = editor.quote_name
    with editor.connection.cursor() as cursor:
        for table in TABLES:
            target = q('mta_state') + '.' + q(table)
            for operation, references in (
                    ('INSERT', 'NEW TABLE AS new_rows'),
                    ('UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows'),
                    ('DELETE', 'OLD TABLE AS old_rows'), ('TRUNCATE', '')):
                cursor.execute('CREATE TRIGGER ingestion_watch_' + operation.lower() +
                    ' AFTER ' + operation + ' ON ' + target +
                    (' REFERENCING ' + references if references else '') +
                    " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('fact')")


def uninstall(apps, editor):
    q = editor.quote_name
    with editor.connection.cursor() as cursor:
        for table in TABLES:
            target = q('mta_state') + '.' + q(table)
            for operation in ('insert', 'update', 'delete', 'truncate'):
                cursor.execute('DROP TRIGGER ingestion_watch_' + operation + ' ON ' + target)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0149_ingestion_typed_batches')]
    operations = [migrations.RunPython(install, uninstall)]
