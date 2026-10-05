"""Prepare or verify the exact sealed RRR occurrence membership."""
import hashlib
import json
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from mta.presentation import fixture
from mta.presentation.rrr_preparation import (
    bands_query, membership_query, recipe_digest, source_signatures,
    validate_positions, verify_guards,
)
from mta.runtime.models import RrrPreparedMembership, RrrPreparedProjection
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts


def fields_for(model):
    return [field.name for field in model._meta.local_fields if field.name not in ('id', 'run')]


def readback(run):
    fields = fields_for(RrrPreparedMembership)
    count, checksum = 0, hashlib.sha256(b'[')
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT ' + ','.join(map(quote, fields)) + ' FROM mta.'
                       + quote(RrrPreparedMembership._meta.db_table)
                       + ' WHERE run_id=%s ORDER BY ordinal', [run.pk])
        while batch := cursor.fetchmany(2000):
            for values in batch:
                row = dict(zip(fields, values))
                if row['ordinal'] != count:
                    raise CommandError('RRR prepared ordinal population differs')
                if count:
                    checksum.update(b',')
                for part in canonical_parts(row):
                    checksum.update(part)
                count += 1
    checksum.update(b']')
    return count, checksum.hexdigest()


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true',
                            help='Verify the sealed membership without inserting rows.')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('RRR preparation requires PostgreSQL')
        run, source = fixture.binding()
        if getattr(run, 'kind', None) != 'LEGACY_UI_FIXTURE' or str(run.business_date) != '2026-04-07':
            raise CommandError('RRR preparation requires the retained April fixture')
        started = time.monotonic()
        with transaction.atomic():
            type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            current, current_source = fixture.binding()
            if current.pk != run.pk or current_source != source:
                raise CommandError('RRR admission changed before preparation')
            dimension_digest, pick_digest = source_signatures(run)
            recipe = recipe_digest()
            receipt = RrrPreparedProjection.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only']:
                    raise CommandError('RRR prepared receipt is absent')
                if RrrPreparedMembership.objects.filter(run=run).exists():
                    raise CommandError('Unsealed RRR prepared rows exist; no replacement allowed')
                bands_sql, bands_params = bands_query(run)
                with connection.cursor() as cursor:
                    validate_positions(cursor, run, bands_sql, bands_params)
                    query, params = membership_query(run, bands_sql, bands_params)
                    fields = [name for name in fields_for(RrrPreparedMembership) if name != 'ordinal']
                    order = ('band_ordinal', 'rationed_ordinal', 'standard_ordinal', 'pair_ordinal',
                             'sku_ordinal', 'location_ordinal', 'left_pair_ordinal')
                    cursor.execute("SELECT set_config('fresh.rrr_prepared_build',%s,true)", [str(run.pk)])
                    cursor.execute('INSERT INTO mta.' + quote(RrrPreparedMembership._meta.db_table)
                                   + ' (run_id,ordinal,' + ','.join(map(quote, fields)) + ') SELECT %s,'
                                   + 'row_number() OVER (ORDER BY '
                                   + ','.join(quote(name) + ' NULLS FIRST' for name in order) + ')-1,'
                                   + ','.join(map(quote, fields)) + ' FROM (' + query + ') members',
                                   [run.pk, *params])
                    cursor.execute('ANALYZE mta.' + quote(RrrPreparedMembership._meta.db_table))
            count, rows_digest = readback(run)
            expected = dict(source_digest=source, dimension_digest=dimension_digest,
                            pick_digest=pick_digest, recipe_digest=recipe,
                            row_count=count, rows_digest=rows_digest)
            if receipt is not None:
                if any(getattr(receipt, name) != value for name, value in expected.items()):
                    raise CommandError('RRR prepared receipt differs')
            else:
                RrrPreparedProjection.objects.create(run=run, **expected)
            final, final_source = fixture.binding()
            if final.pk != run.pk or final_source != source:
                raise CommandError('RRR admission changed before commit')
            verify_guards(connection)
        self.stdout.write(json.dumps(dict(status='PASS', created=receipt is None,
                                         seconds=time.monotonic()-started, **expected), sort_keys=True))
