"""Exact normalized BTR join indexes on the owned, immutable VM fixture only."""
import os

from tools.stage2_vm_load import DATA, DB, IDENTITY
from tools.stage2_vm_contract import atomic, sealed


TABLES = (
    ('btr_bpptrendphysicalinv', 'WhCode'),
    ('btr_bpptrenddispatch', 'WhCode'),
    ('btr_buffertrendphysicalinv', 'WhCode'),
    ('btr_buffertrenddispatch', 'WhCode'),
    ('btr_skulocattributedata', 'LocCode'),
    ('importer_skulocstandardattributes', 'WhCode'),
    ('bpr_vf_rationedreqreport', 'WhCode'),
)


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
    import django
    django.setup()
    from django.db import connection
    from mta.presentation.fixture import freeze_state
    from mta.presentation.rrr_sql import key
    from mta.serialization import digest
    if connection.settings_dict['NAME'] != DB:
        raise ValueError('Wrong isolated database')
    _, manifest_sha = sealed(DATA)
    before = digest(freeze_state())
    receipts = []
    with connection.cursor() as cursor:
        cursor.execute('SELECT manifest_sha256 FROM stage2_owner.manifest')
        if cursor.fetchall() != [(manifest_sha,)]:
            raise ValueError('Wrong source identity')
        cursor.execute("SET maintenance_work_mem='64MB'")
        cursor.execute('SET max_parallel_maintenance_workers=0')
        for table, location in TABLES:
            name = 'stage2_btr_join_' + table
            columns = ['vf_run_id', 'vf_image', key('"SKUCode"'), key('"' + location + '"')]
            # Compare PostgreSQL's own canonical definition, including expression
            # casts, using a transactional reference index on an empty temp table.
            with connection.cursor() as check:
                check.execute('CREATE TEMP TABLE btr_index_shape (LIKE mta_state."' + table + '")')
                check.execute('CREATE INDEX btr_index_shape_check ON btr_index_shape (' + ','.join(columns) + ')')
                check.execute("SELECT pg_get_indexdef('btr_index_shape_check'::regclass)")
                expected = 'CREATE INDEX ' + name + ' ON mta_state.' + table + ' USING ' + check.fetchone()[0].split(' USING ', 1)[1]
                check.execute('DROP TABLE btr_index_shape')
            cursor.execute('SELECT pg_get_indexdef(indexrelid),indisvalid,indisready FROM pg_index WHERE indexrelid=to_regclass(%s)', ['mta_state.' + name])
            prior = cursor.fetchone()
            if not prior:
                cursor.execute('CREATE INDEX "' + name + '" ON mta_state."' + table + '" (' + ','.join(columns) + ')')
            cursor.execute('SELECT pg_get_indexdef(indexrelid),indisvalid,indisready FROM pg_index WHERE indexrelid=to_regclass(%s)', ['mta_state.' + name])
            actual = cursor.fetchone()
            if actual != (expected, True, True):
                raise ValueError('BTR index definition/validity differs: ' + str(actual))
            cursor.execute('ANALYZE mta_state."' + table + '"')
            receipts.append(dict(index=name, definition=actual[0], valid=True))
            print('Verified', name, flush=True)
    if digest(freeze_state()) != before:
        raise ValueError('Fixture freeze identity changed')
    atomic(DATA / 'btr-indexes.json', dict(status='PASS', identity=IDENTITY,
        manifest_sha256=manifest_sha, freeze_digest=before, indexes=receipts,
        row_mutations=0, reason='Retained BTR concurrent count/grid timeout and full-scan plan'))


if __name__ == '__main__':
    main()
