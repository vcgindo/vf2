"""Prepare the two canonical April Planning masters once, with immutable receipts."""
import hashlib
import json
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from mta.presentation import fixture
from mta.presentation.planning_source_sql import (
    BPR_FIELDS, GIT_FIELDS,
    source_queries, validate_target_lengths, recipe_digest,
)
from mta.presentation.rrr_sql import key
from mta.runtime.models import PlanningBprMasterRow, PlanningGitMasterRow, PlanningSourceProjection
from mta.runtime.planning_source_schema import verify_guards
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts

SOURCES = (
    ('bpr_master', PlanningBprMasterRow, BPR_FIELDS, ('source_ordinal',), 'WHCode'),
    ('git_master', PlanningGitMasterRow, GIT_FIELDS, ('rationed_ordinal', 'standard_ordinal'), 'WhCode'),
)


def rows_receipt(run, model, fields, ordinals):
    fields = (*ordinals, 'sku_key', 'location_key', 'parent_key', *fields)
    checksum = hashlib.sha256(b'[')
    count = 0
    with connection.chunked_cursor() as c:
        c.execute('SELECT ' + ','.join(map(quote, fields)) + ' FROM mta.' + quote(model._meta.db_table)
                  + ' WHERE run_id=%s ORDER BY ' + ','.join(map(quote, ordinals)), [run.pk])
        while batch := c.fetchmany(2000):
            for row in batch:
                values = dict(zip(fields, row))
                validate_target_lengths([values], fields)
                if count:
                    checksum.update(b',')
                for part in canonical_parts(values):
                    checksum.update(part)
                count += 1
    checksum.update(b']')
    return count, checksum.hexdigest()


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true')
        parser.add_argument('--run-id')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('Planning source preparation requires PostgreSQL')
        from mta.presentation.daily_preparation import command_binding, assert_unchanged
        run, initial_source = command_binding(options.get('run_id'))
        start = time.monotonic()
        with transaction.atomic():
            type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            source, queries = source_queries(run)
            if source != initial_source:
                raise CommandError('Planning source admission changed before preparation')
            receipt = PlanningSourceProjection.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only']:
                    raise CommandError('Planning source receipt is absent')
                if any(model.objects.filter(run=run).exists() for _, model, *_ in SOURCES):
                    raise CommandError('Unsealed Planning rows exist; no overwrite allowed')
                with connection.cursor() as c:
                    c.execute("SELECT set_config('fresh.planning_source_build',%s,true)", [str(run.pk)])
                    for name, model, fields, ordinals, location in SOURCES:
                        query, params, _ = queries[name]
                        columns = ('run_id', *ordinals, 'sku_key', 'location_key', 'parent_key', *fields)
                        selected = ['%s', *map(quote, ordinals), key('"SKUCode"'),
                                    key(quote(location)), key('"ParentWhCode"'), *map(quote, fields)]
                        c.execute('INSERT INTO mta.' + quote(model._meta.db_table) + ' ('
                                  + ','.join(map(quote, columns)) + ') SELECT ' + ','.join(selected)
                                  + ' FROM (' + query + ') derived', [run.pk, *params])
            values = {}
            for name, model, fields, ordinals, _ in SOURCES:
                count, checksum = rows_receipt(run, model, fields, ordinals)
                prefix = name.split('_')[0]
                values[prefix + '_count'] = count
                values[prefix + '_digest'] = checksum
            expected = dict(source_digest=source, recipe_digest=recipe_digest(), **values)
            if receipt:
                if any(getattr(receipt, name) != value for name, value in expected.items()):
                    raise CommandError('Planning prepared source receipt differs')
            else:
                PlanningSourceProjection.objects.create(run=run, **expected)
            try:
                assert_unchanged(run, source)
            except Exception as exc:
                raise CommandError('Planning source admission changed before commit') from exc
        self.stdout.write(json.dumps(dict(status='PASS', created=receipt is None,
                                         seconds=time.monotonic()-start, **expected), sort_keys=True))
