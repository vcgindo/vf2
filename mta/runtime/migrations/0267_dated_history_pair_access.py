"""Raw-pair graph access without scanning an entire visible DBM history.

Only the three dated histories consumed by the existing DBM history graph.
The C collation matches its raw, case-sensitive pair predicate. No payload,
visibility, business ordering or accepted image is changed.
"""
from django.db import migrations


FAMILIES = (
    ('dailyconsumption', 'ReportDate'),
    ('suspendhistory', 'ReportDate'),
    ('suggestionslog', 'SuggestionDate'),
)
SQL = '\n'.join(
    f'CREATE INDEX history_dbm_{name}_pair_date ON mta_state.history_dbm_{name} '
    f'(initialization_id,"SKUCode" COLLATE "C","WhCode" COLLATE "C","{stamp}",born_position,vf_ordinal);'
    for name,stamp in FAMILIES)
REVERSE = '\n'.join(f'DROP INDEX mta_state.history_dbm_{name}_pair_date;' for name,_ in FAMILIES)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0266_dated_history_storage')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
