"""Give compact BTR dimensions the existing presentation-row revision owner."""
from importlib import import_module
from django.db import migrations


TABLES = ('fresh_mta_btrscopedimension',)
OLD = import_module('mta.runtime.migrations.0237_intake_diagnostic_guards').NEW
owner_sets = import_module('mta.runtime.migrations.0168_report_guard_owner_sets')
transition = import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership').transition


def classification(table):
    parent = 'LEFT JOIN mta.fresh_mta_btrreportinggeneration P ON P.id=N.generation_id'
    join = parent + ' LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id'
    query = owner_sets._query(parent, 'TRUE', 'generation_id', 'P.run_id')
    return ("WHEN TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='" + table +
        "' THEN report_join='" + join + "'; report_filter='TRUE'; report_check='" +
        query.replace("'", "''") + "';")


# Clone the exact existing child-to-generation-to-run classification, retaining
# its missing-owner LEFT JOIN and successful DAILY_CHAIN/v3 qualification.
PRESENTATION_CASE = classification('fresh_mta_btrpresentationrow')
SCOPE_CASE = classification(TABLES[0])
assert OLD.count(PRESENTATION_CASE) == 1
assert TABLES[0] not in OLD
NEW = OLD.replace(PRESENTATION_CASE, PRESENTATION_CASE + '\n' + SCOPE_CASE, 1)

SQL = transition(OLD, NEW)
REVERSE = ''
for operation, referencing in (
        ('INSERT', 'NEW TABLE AS new_rows'),
        ('UPDATE', 'OLD TABLE AS old_rows NEW TABLE AS new_rows'),
        ('DELETE', 'OLD TABLE AS old_rows'), ('TRUNCATE', '')):
    SQL += ('CREATE TRIGGER ingestion_watch_' + operation.lower() + ' AFTER ' + operation +
        ' ON mta.' + TABLES[0] + (' REFERENCING ' + referencing if referencing else '') +
        " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational');\n")
    REVERSE += 'DROP TRIGGER ingestion_watch_' + operation.lower() + ' ON mta.' + TABLES[0] + ';\n'
REVERSE += transition(NEW, OLD)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0245_btr_scope_dimensions')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
