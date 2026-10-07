"""Atomically prepare the native daily Guided DBM occurrence relation."""
import hashlib
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction

from mta.presentation import fixture
from mta.presentation.guided_dbm_fields import SOURCES, FIELDS, field_name, schema_digest
from mta.presentation.selective import image_query, image_metadata, image_field
from mta.runtime.guided_dbm_schema import verify_guards
from mta.runtime.models import (CalculationRun, GuidedDbmPreparedProjection,
                                GuidedDbmPreparedRow)
from mta.runtime.relational_state import CATALOG, quote
from mta.serialization import canonical_parts


ORDINALS = ('a_ordinal', 's_ordinal', 'l_ordinal', 'p_ordinal', 'm_ordinal')
ROW_FIELDS = ('ordinal',) + ORDINALS + tuple(
    field_name(owner, name) for owner, fields in FIELDS.items() for name in fields)


def raw_equal(left, right):
    """Hashable exact Python equality, including the single NULL==NULL case."""
    return ('(' + left + ' IS NULL)=(' + right + ' IS NULL) AND '
            "COALESCE(" + left + ",'')=COALESCE(" + right + ",'')")


def insert_query(run):
    ctes, values = [], []
    for owner, path in SOURCES.items():
        item = image_metadata(run, path)
        published = {name: {'str': 'text', 'int': 'bigint'}[wire]
                     for name, _, wire in item['fields'] if wire in ('str', 'int')}
        for name, kind in FIELDS[owner].items():
            # Operational manifests use str when every value is NULL. Accept
            # that observation only for a native integer column proven NULL;
            # never coerce a populated text value or change the stored image.
            if (getattr(run, 'kind', None) == 'DAILY_CHAIN'
                    and kind == 'bigint' and published.get(name) == 'text'
                    and dict(CATALOG['tables'][item['table']]).get(name) in ('int', 'bigint')
                    and all(value is None for value in image_field(run, path, name))):
                published[name] = kind
            if published.get(name) != kind:
                raise CommandError('Guided DBM prepared source field/type differs: ' + owner + '.' + name)
        sql, params = image_query(run, path)
        ctes.append(owner + ' AS NOT MATERIALIZED (' + sql + ')')
        values.extend(params)
    selected = ['%s', 'row_number() OVER (ORDER BY A.vf_ordinal,S.vf_ordinal,'
                'L.vf_ordinal,P.vf_ordinal NULLS FIRST,M.vf_ordinal)-1']
    selected += [owner + '.vf_ordinal' for owner in SOURCES]
    selected += [owner + '.' + quote(name)
                 for owner, fields in FIELDS.items() for name in fields]
    joins = (' FROM A JOIN S ON ' + raw_equal('A."SKUCode"', 'S."SKUCode"') +
             ' JOIN L ON ' + raw_equal('A."WhCode"', 'L."WHCode"') +
             ' LEFT JOIN P ON ' + raw_equal('A."SKUCode"', 'P."SKUCode"') +
             ' AND ' + raw_equal('A."WhCode"', 'P."LocCode"') +
             ' JOIN M ON ' + raw_equal('A."SKUCode"', 'M."SKUCode"') +
             ' AND ' + raw_equal('A."WhCode"', 'M."WhCode"'))
    columns = ','.join(quote(name) for name in ('run_id',) + ROW_FIELDS)
    query = ('WITH ' + ','.join(ctes) + ' INSERT INTO ' +
             quote(GuidedDbmPreparedRow._meta.db_table) + ' (' + columns +
             ') SELECT ' + ','.join(selected) + joins)
    return query, values + [run.pk]


def rows_receipt(run):
    checksum = hashlib.sha256(b'[')
    count = 0
    columns = ','.join(quote(name) for name in ROW_FIELDS)
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT ' + columns + ' FROM ' +
                       quote(GuidedDbmPreparedRow._meta.db_table) +
                       ' WHERE run_id=%s ORDER BY ordinal', [run.pk])
        while True:
            batch = cursor.fetchmany(1000)
            if not batch:
                break
            for row in batch:
                if row[0] != count:
                    raise CommandError('Guided DBM prepared ordinal population differs')
                if count:
                    checksum.update(b',')
                for part in canonical_parts(dict(zip(ROW_FIELDS, row))):
                    checksum.update(part)
                count += 1
    checksum.update(b']')
    return count, checksum.hexdigest()


def verify_mutation_guards(run):
    """Exercise every sealed-table mutation class inside rolled-back savepoints."""
    before = rows_receipt(run)
    row_table = quote(GuidedDbmPreparedRow._meta.db_table)
    receipt_table = quote(GuidedDbmPreparedProjection._meta.db_table)
    immutable = 'Guided DBM prepared rows and receipts are immutable'
    statements = (
        ('row_insert', 'INSERT INTO ' + row_table +
         ' (run_id,ordinal,a_ordinal,s_ordinal,l_ordinal,m_ordinal) VALUES (%s,-1,-1,-1,-1,-1)',
         [run.pk], 'Sealed Guided DBM prepared rows are immutable'),
        ('row_update', 'UPDATE ' + row_table + ' SET ordinal=ordinal WHERE run_id=%s', [run.pk], immutable),
        ('row_delete', 'DELETE FROM ' + row_table + ' WHERE run_id=%s', [run.pk], immutable),
        ('row_truncate', 'TRUNCATE ' + row_table, [], immutable),
        ('receipt_update', 'UPDATE ' + receipt_table + ' SET row_count=row_count WHERE run_id=%s', [run.pk], immutable),
        ('receipt_delete', 'DELETE FROM ' + receipt_table + ' WHERE run_id=%s', [run.pk], immutable),
        ('receipt_truncate', 'TRUNCATE ' + receipt_table, [], immutable),
    )
    normal = CalculationRun.objects.exclude(kind='LEGACY_UI_FIXTURE').order_by('created_at').first()
    normal_status = 'UNAVAILABLE_NO_NORMAL_RUN'
    if normal is not None:
        statements += (('normal_run_insert', 'INSERT INTO ' + row_table +
            ' (run_id,ordinal,a_ordinal,s_ordinal,l_ordinal,m_ordinal) VALUES (%s,-1,-1,-1,-1,-1)',
            [normal.pk], 'Guided DBM prepared rows require the isolated fixture run'),)
        normal_status = 'TESTED_DENIED'
    rejected = []
    for name, sql, params, expected in statements:
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
        except DatabaseError as exc:
            if expected not in str(exc):
                raise CommandError('Guided DBM guard returned an unexpected error for ' + name) from exc
            rejected.append(name)
        else:
            raise CommandError('Guided DBM mutation guard did not reject ' + name)
    if rows_receipt(run) != before:
        raise CommandError('Guided DBM rows changed during mutation-guard proof')
    return dict(rejected=rejected, normal_owner_guard=normal_status)


def prepare(*, run=None, verify_only=False, verify_mutations=False):
    if connection.vendor != 'postgresql':
        raise CommandError('Guided DBM prepared relation requires PostgreSQL')
    from mta.presentation.daily_preparation import production_branch
    if not production_branch(run) and not getattr(settings, 'VF_GUIDED_PREPARED', False):
        raise CommandError('Guided prepared trial switch is disabled')
    from mta.presentation.daily_activation import native_verification_with_access
    if (getattr(settings, 'VF_MTA_HIERARCHY_FILE', '') or getattr(settings, 'VF_MTA_HIERARCHY_SHA256', '')) and not native_verification_with_access(run, verify_only):
        raise CommandError('Guided DBM preparation requires native fixture hierarchy')
    with transaction.atomic():
        verify_guards(connection)
        fixture_run = run is None
        if fixture_run:
            run, source = fixture.binding()
        else:
            from mta.presentation.daily_preparation import source_digest
            source = source_digest(run)
        CalculationRun.objects.select_for_update().get(pk=run.pk)
        if fixture_run:
            run_after_lock, source_after_lock = fixture.binding()
            if run.pk != run_after_lock.pk or source != source_after_lock:
                raise CommandError('Guided DBM source changed before preparation')
        schema = schema_digest()
        receipt = GuidedDbmPreparedProjection.objects.filter(run=run).first()
        if receipt:
            if (receipt.source_digest, receipt.schema_digest) != (source, schema):
                raise CommandError('Existing Guided DBM binding/schema differs; no replacement allowed')
            count, rows_digest = rows_receipt(run)
            if (receipt.row_count, receipt.rows_digest) != (count, rows_digest):
                raise CommandError('Existing Guided DBM complete row receipt differs')
            created = False
        else:
            if verify_only:
                raise CommandError('Guided DBM prepared receipt does not exist')
            if GuidedDbmPreparedRow.objects.filter(run=run).exists():
                raise CommandError('Unsealed Guided DBM rows exist; no replacement allowed')
            query, params = insert_query(run)
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                inserted = cursor.rowcount
            count, rows_digest = rows_receipt(run)
            if inserted != count:
                raise CommandError('Guided DBM insert/readback population differs')
            receipt = GuidedDbmPreparedProjection.objects.create(
                run=run, source_digest=source, schema_digest=schema,
                rows_digest=rows_digest, row_count=count)
            created = True
        if fixture_run:
            final_run, final_source = fixture.binding()
            if final_run.pk != run.pk or final_source != source:
                raise CommandError('Guided DBM source changed before commit')
        else:
            from mta.presentation.daily_preparation import assert_unchanged
            assert_unchanged(run, source)
        verify_guards(connection)
        mutations = verify_mutation_guards(run) if verify_mutations else []
        return dict(run_id=str(run.pk), source_digest=source, schema_digest=schema,
                    rows_digest=receipt.rows_digest, row_count=receipt.row_count,
                    created=created, mutation_guards=mutations, status='PASS')


class Command(BaseCommand):
    help = 'Prepare or verify the selected isolated fixture Guided DBM occurrence relation.'

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true')
        parser.add_argument('--verify-mutation-guards', action='store_true')
        parser.add_argument('--run-id')

    def handle(self, *args, **options):
        run = CalculationRun.objects.get(pk=options['run_id']) if options.get('run_id') else None
        self.stdout.write(json.dumps(prepare(run=run, verify_only=options['verify_only'],
            verify_mutations=options['verify_mutation_guards']), sort_keys=True))
