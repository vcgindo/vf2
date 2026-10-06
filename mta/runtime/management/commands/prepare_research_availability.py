"""Prepare or verify exact per-occurrence Research availability band counts."""
import hashlib
import json
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from mta.presentation import fixture, history_preparation
from mta.presentation.research_availability_preparation import (
    RUN_ID, bands_query, recipe_digest, verify_guards,
)
from mta.runtime.models import (
    HistoryPreparedProjection, ResearchAvailabilityBand,
    ResearchAvailabilityBandProjection,
)
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts


FIELDS = tuple(
    field.name for field in ResearchAvailabilityBand._meta.local_fields
    if field.name not in ('id', 'run')
)


def _hash_rows(cursor):
    count, checksum = 0, hashlib.sha256(b'[')
    while batch := cursor.fetchmany(2000):
        for values in batch:
            row = dict(zip(FIELDS, values))
            if row['ordinal'] != count:
                raise CommandError('Research availability band ordinal population differs')
            if count:
                checksum.update(b',')
            for part in canonical_parts(row):
                checksum.update(part)
            count += 1
    checksum.update(b']')
    return count, checksum.hexdigest()


def source_readback(run):
    sql, params = bands_query(run)
    with connection.chunked_cursor() as cursor:
        cursor.execute(sql, params)
        return _hash_rows(cursor)


def prepared_readback(run):
    with connection.chunked_cursor() as cursor:
        cursor.execute(
            'SELECT ' + ','.join(map(quote, FIELDS)) + ' FROM mta.'
            + quote(ResearchAvailabilityBand._meta.db_table)
            + ' WHERE run_id=%s ORDER BY ordinal',
            [run.pk],
        )
        return _hash_rows(cursor)


def accepted_history_source(run, source):
    """Bind the supplement to the already sealed immutable membership."""
    history_preparation.verify_guards(connection)
    receipt = HistoryPreparedProjection.objects.filter(run=run).first()
    if receipt is None or receipt.status != 'READY' or receipt.source_digest != source \
            or receipt.dimension_digest != history_preparation.source_signatures(run) \
            or receipt.recipe_digest != history_preparation.recipe_digest():
        raise CommandError('Accepted history prepared source is absent or changed')
    return receipt.availability_count, receipt.availability_digest


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true')
        parser.add_argument('--run-id')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('Research availability preparation requires PostgreSQL')
        from mta.presentation.daily_preparation import command_binding, assert_unchanged
        run, source = command_binding(options.get('run_id'))
        if getattr(run, 'kind', None) not in ('LEGACY_UI_FIXTURE','DAILY_CHAIN') or (run.kind == 'LEGACY_UI_FIXTURE' and (str(run.pk) != RUN_ID or str(run.business_date) != '2026-04-07')):
            raise CommandError('Research availability preparation requires the retained April fixture')
        started = time.monotonic()
        with transaction.atomic():
            type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            membership_count, membership_digest = accepted_history_source(run, source)
            assert_unchanged(run, source)
            receipt = ResearchAvailabilityBandProjection.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only']:
                    raise CommandError('Research availability band receipt is absent')
                if ResearchAvailabilityBand.objects.filter(run=run).exists():
                    raise CommandError('Unsealed Research availability band rows exist; no replacement allowed')
                sql, params = bands_query(run)
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('fresh.research_availability_band_build',%s,true)",
                        [str(run.pk)],
                    )
                    cursor.execute(
                        'INSERT INTO mta.' + quote(ResearchAvailabilityBand._meta.db_table)
                        + ' (run_id,' + ','.join(map(quote, FIELDS)) + ') SELECT %s,'
                        + ','.join(map(quote, FIELDS)) + ' FROM (' + sql + ') source',
                        [run.pk, *params],
                    )
                    cursor.execute('ANALYZE mta.' + quote(ResearchAvailabilityBand._meta.db_table))
            source_result = source_readback(run)
            stored_result = prepared_readback(run)
            if source_result != stored_result or source_result[0] != membership_count:
                raise CommandError('Research availability prepared rows differ from full source reconstruction')
            expected = dict(
                status='READY', source_digest=source,
                membership_digest=membership_digest,
                recipe_digest=recipe_digest(), row_count=source_result[0],
                rows_digest=source_result[1],
            )
            if receipt is not None:
                if any(getattr(receipt, name) != value for name, value in expected.items()):
                    raise CommandError('Research availability band receipt differs')
            else:
                ResearchAvailabilityBandProjection.objects.create(run=run, **expected)
            assert_unchanged(run, source)
            final_count, final_digest = accepted_history_source(run, source)
            if (final_count, final_digest) != (membership_count, membership_digest):
                raise CommandError('Accepted history prepared source changed before commit')
            verify_guards(connection)
        self.stdout.write(json.dumps(dict(
            expected, status='PASS', created=receipt is None,
            seconds=time.monotonic() - started,
        ), sort_keys=True))
