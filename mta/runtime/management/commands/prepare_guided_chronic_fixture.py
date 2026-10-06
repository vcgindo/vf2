"""Atomically prepare the fixture Chronic grid occurrence relation."""
import hashlib
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction

from mta.presentation import fixture
from mta.presentation.guided_chronic_fields import SOURCES, OUTPUTS, schema_digest
from mta.presentation.selective import image_query
from mta.runtime.guided_chronic_schema import verify_guards
from mta.runtime.models import (CalculationRun, GuidedChronicPreparedProjection,
                                GuidedChronicPreparedRow)
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts


ORDINALS = ('a_ordinal', 'n_ordinal', 'l_ordinal', 's_ordinal', 'p_ordinal')
ROW_FIELDS = ('ordinal',) + ORDINALS + tuple(OUTPUTS)


def raw_equal(left, right):
    return ('((' + left + ' IS NULL)=(' + right + ' IS NULL) AND COALESCE(' +
            left + ",'')=COALESCE(" + right + ",''))")


def insert_query(run):
    ctes, values = [], []
    expected_outputs = {
        'skucode': 'text', 'skudesc': 'text', 'location': 'text', 'parentloc': 'text',
        'RLT': 'bigint', 'BlackRedAgeing': 'bigint', 'PhysicalInventoryPen': 'text',
        'Techcolor': 'text', 'PipelineInventoryPen': 'text', 'ecocolor': 'text',
        'RationedStockatparent': 'bigint'}
    if OUTPUTS != expected_outputs:
        raise CommandError('Guided Chronic prepared output wire contract differs')
    required = {
        'A': {'SKUCode': 'str', 'WhCode': 'str', 'ParentWhCode': 'str', 'RLT': 'int',
              'BRAge': 'int', 'PhysicalInventoryPen': 'str', 'PhysicalInventoryColor': 'str',
              'PipelineInventoryPen': 'str', 'PipelineInventoryColor': 'str', 'RationedQty': 'int'},
        'N': {'SKUCode': 'str', 'WhCode': 'str', 'SKUDescription': 'str'},
        'L': {'WHCode': 'str'}, 'S': {'SKUCode': 'str'},
        'P': {'SKUCode': 'str', 'LocCode': 'str'},
    }
    for owner, path in SOURCES.items():
        item = fixture.image_metadata(run, path)
        published = {name: wire for name, _, wire in item['fields']}
        if any(published.get(name) != wire for name, wire in required[owner].items()):
            raise CommandError('Guided Chronic prepared source field/wire differs: ' + owner)
        query, params = image_query(run, path)
        ctes.append(owner + ' AS NOT MATERIALIZED (' + query + ')')
        values.extend(params)
    selected = ['%s', 'row_number() OVER (ORDER BY A.vf_ordinal,N.vf_ordinal NULLS FIRST,'
                'L.vf_ordinal NULLS FIRST,S.vf_ordinal NULLS FIRST,P.vf_ordinal NULLS FIRST)-1']
    selected += [owner + '.vf_ordinal' for owner in SOURCES]
    selected += ['A."SKUCode"', 'N."SKUDescription"', 'A."WhCode"', 'A."ParentWhCode"',
                 'A."RLT"', 'A."BRAge"', 'A."PhysicalInventoryPen"::text',
                 'A."PhysicalInventoryColor"', 'A."PipelineInventoryPen"::text',
                 'A."PipelineInventoryColor"', 'A."RationedQty"']
    joins = (' FROM A LEFT JOIN N ON ' + raw_equal('A."SKUCode"', 'N."SKUCode"') +
             ' AND ' + raw_equal('A."WhCode"', 'N."WhCode"') +
             ' LEFT JOIN L ON ' + raw_equal('A."WhCode"', 'L."WHCode"') +
             ' LEFT JOIN S ON ' + raw_equal('A."SKUCode"', 'S."SKUCode"') +
             ' LEFT JOIN P ON ' + raw_equal('A."SKUCode"', 'P."SKUCode"') +
             ' AND ' + raw_equal('A."WhCode"', 'P."LocCode"'))
    columns = ','.join(quote(name) for name in ('run_id',) + ROW_FIELDS)
    return ('WITH ' + ','.join(ctes) + ' INSERT INTO ' +
            quote(GuidedChronicPreparedRow._meta.db_table) + ' (' + columns +
            ') SELECT ' + ','.join(selected) + joins), values + [run.pk]


def rows_receipt(run):
    checksum = hashlib.sha256(b'['); count = 0
    columns = ','.join(quote(name) for name in ROW_FIELDS)
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT ' + columns + ' FROM ' + quote(GuidedChronicPreparedRow._meta.db_table) +
                       ' WHERE run_id=%s ORDER BY ordinal', [run.pk])
        while True:
            batch = cursor.fetchmany(1000)
            if not batch: break
            for row in batch:
                if row[0] != count: raise CommandError('Guided Chronic prepared ordinal population differs')
                if count: checksum.update(b',')
                for part in canonical_parts(dict(zip(ROW_FIELDS, row))): checksum.update(part)
                count += 1
    checksum.update(b']')
    return count, checksum.hexdigest()


def verify_mutation_guards(run):
    before = rows_receipt(run)
    row_table = quote(GuidedChronicPreparedRow._meta.db_table)
    receipt_table = quote(GuidedChronicPreparedProjection._meta.db_table)
    immutable = 'Guided Chronic prepared rows and receipts are immutable'
    statements = (
        ('row_insert', 'INSERT INTO ' + row_table +
         ' (run_id,ordinal,a_ordinal) VALUES (%s,-1,-1)', [run.pk],
         'Sealed Guided Chronic prepared rows are immutable'),
        ('row_update', 'UPDATE ' + row_table + ' SET ordinal=ordinal WHERE run_id=%s', [run.pk], immutable),
        ('row_delete', 'DELETE FROM ' + row_table + ' WHERE run_id=%s', [run.pk], immutable),
        ('row_truncate', 'TRUNCATE ' + row_table, [], immutable),
        ('receipt_update', 'UPDATE ' + receipt_table + ' SET row_count=row_count WHERE run_id=%s', [run.pk], immutable),
        ('receipt_delete', 'DELETE FROM ' + receipt_table + ' WHERE run_id=%s', [run.pk], immutable),
        ('receipt_truncate', 'TRUNCATE ' + receipt_table, [], immutable),
    )
    rejected = []
    for name, sql, params, expected in statements:
        try:
            with transaction.atomic(), connection.cursor() as cursor: cursor.execute(sql, params)
        except DatabaseError as exc:
            if expected not in str(exc): raise CommandError('Unexpected Chronic guard error: ' + name) from exc
            rejected.append(name)
        else: raise CommandError('Chronic mutation guard did not reject ' + name)
    if rows_receipt(run) != before: raise CommandError('Chronic rows changed during guard proof')
    return rejected


def prepare(*, run=None, verify_only=False, verify_mutations=False):
    if connection.vendor != 'postgresql': raise CommandError('Guided Chronic preparation requires PostgreSQL')
    if not getattr(settings, 'VF_GUIDED_PREPARED', False): raise CommandError('Guided prepared trial switch is disabled')
    if getattr(settings, 'VF_MTA_HIERARCHY_FILE', '') or getattr(settings, 'VF_MTA_HIERARCHY_SHA256', ''):
        raise CommandError('Guided Chronic preparation requires native fixture hierarchy')
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
            locked_run, locked_source = fixture.binding()
            if (locked_run.pk, locked_source) != (run.pk, source): raise CommandError('Chronic source changed before preparation')
        schema = schema_digest(); receipt = GuidedChronicPreparedProjection.objects.filter(run=run).first()
        if receipt:
            if (receipt.source_digest, receipt.schema_digest) != (source, schema):
                raise CommandError('Existing Chronic binding/schema differs; no replacement allowed')
            count, rows_digest = rows_receipt(run)
            if (receipt.row_count, receipt.rows_digest) != (count, rows_digest):
                raise CommandError('Existing Chronic complete row receipt differs')
            created = False
        else:
            if verify_only: raise CommandError('Guided Chronic prepared receipt does not exist')
            if GuidedChronicPreparedRow.objects.filter(run=run).exists():
                raise CommandError('Unsealed Chronic rows exist; no replacement allowed')
            query, params = insert_query(run)
            with connection.cursor() as cursor: cursor.execute(query, params); inserted = cursor.rowcount
            count, rows_digest = rows_receipt(run)
            if inserted != count: raise CommandError('Chronic insert/readback population differs')
            receipt = GuidedChronicPreparedProjection.objects.create(run=run, source_digest=source,
                schema_digest=schema, rows_digest=rows_digest, row_count=count)
            created = True
        if fixture_run:
            final_run, final_source = fixture.binding()
            if (final_run.pk, final_source) != (run.pk, source): raise CommandError('Chronic source changed before commit')
        else:
            from mta.presentation.daily_preparation import assert_unchanged
            assert_unchanged(run, source)
        verify_guards(connection)
        guards = verify_mutation_guards(run) if verify_mutations else []
        return dict(status='PASS', run_id=str(run.pk), source_digest=source, schema_digest=schema,
                    rows_digest=receipt.rows_digest, row_count=receipt.row_count,
                    created=created, mutation_guards=guards)


class Command(BaseCommand):
    help = 'Prepare or verify the selected isolated fixture Chronic grid relation.'
    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true')
        parser.add_argument('--verify-mutation-guards', action='store_true')
        parser.add_argument('--run-id')
    def handle(self, *args, **options):
        run = CalculationRun.objects.get(pk=options['run_id']) if options.get('run_id') else None
        self.stdout.write(json.dumps(prepare(run=run, verify_only=options['verify_only'],
            verify_mutations=options['verify_mutation_guards']), sort_keys=True))
