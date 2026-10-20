"""Preserve exact accepted timestamp text beside typed PostgreSQL authority.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from django.db import migrations


FIELDS = (
    ('batch_consumer_requests', 'RequestDate', 'timestamp without time zone'),
    ('batch_consumer_requests', 'ActionDate', 'timestamp without time zone'),
    ('batch_consumer_requests', 'ETA', 'timestamp without time zone'),
    ('batch_consumer_remarks_bpr', 'RemarkDate', 'timestamp with time zone'),
    ('batch_consumer_remarks_bor', 'RemarkDate', 'timestamp with time zone'),
    ('batch_consumer_remarks_boroa', 'RemarkDate', 'timestamp with time zone'),
)


def q(value):
    return '"' + value.replace('"', '""') + '"'


def forward():
    statements = []
    for table, field, pg_type in FIELDS:
        target = 'mta_state.' + q(table)
        wire = 'vf_wire_' + field
        constraint = table + '_' + field.lower() + '_wire_match'
        statements.append('ALTER TABLE ' + target + ' ADD COLUMN ' + q(wire) + ' text')
        statements.append('ALTER TABLE ' + target + ' ADD CONSTRAINT ' + q(constraint) +
            ' CHECK (((' + q(field) + ' IS NULL) = (' + q(wire) + ' IS NULL)) AND (' +
            q(field) + ' IS NULL OR ' + q(wire) + '::' + pg_type +
            ' IS NOT DISTINCT FROM ' + q(field) + '))')
    return ';\n'.join(statements) + ';'


def reverse():
    return ';\n'.join('ALTER TABLE mta_state.' + q(table) +
        ' DROP COLUMN ' + q('vf_wire_' + field) for table, field, _ in reversed(FIELDS)) + ';'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0151_accepted_daily_seal')]
    operations = [migrations.RunSQL(forward(), reverse())]
