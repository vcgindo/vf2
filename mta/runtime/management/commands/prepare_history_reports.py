"""Prepare or verify exact Research and Buffer Trends history memberships."""
import hashlib
import json
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from mta.presentation.history_preparation import (
    RUN_ID, availability_query, graph_query, recipe_digest, research_history_query,
    research_master_query, source_signatures, verify_guards,
)
from mta.runtime.models import (
    BufferGraphPreparedMembership, HistoryPreparedProjection,
    ResearchAvailabilityMembership, ResearchPreparedHistoryReference,
    ResearchPreparedMasterReference,
)
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts


POPULATIONS = (
    ('research_master', ResearchPreparedMasterReference, research_master_query,
     ('owner_sku_key','owner_location_key','rationed_ordinal')),
    ('research_history', ResearchPreparedHistoryReference, research_history_query,
     ('owner_sku_key','owner_location_key','family','history_ordinal')),
    ('availability', ResearchAvailabilityMembership, availability_query,
     ('history_ordinal','sku_ordinal','location_ordinal')),
    ('graph', BufferGraphPreparedMembership, graph_query,
     ('family','history_ordinal','sku_ordinal','location_ordinal','pair_ordinal')),
)


def fields_for(model):
    return [field.name for field in model._meta.local_fields if field.name not in ('id','run')]


def readback(run, model):
    fields = fields_for(model)
    count, checksum = 0, hashlib.sha256(b'[')
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT ' + ','.join(map(quote, fields)) + ' FROM mta.'
                       + quote(model._meta.db_table) + ' WHERE run_id=%s ORDER BY ordinal', [run.pk])
        while batch := cursor.fetchmany(2000):
            for values in batch:
                row = dict(zip(fields, values))
                if row['ordinal'] != count:
                    raise CommandError('History prepared ordinal population differs')
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
        parser.add_argument('--verify-only', action='store_true')
        parser.add_argument('--run-id')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('History report preparation requires PostgreSQL')
        from mta.presentation.daily_preparation import command_binding, assert_unchanged
        run, source = command_binding(options.get('run_id'))
        if getattr(run, 'kind', None) not in ('LEGACY_UI_FIXTURE', 'DAILY_CHAIN'):
            raise CommandError('History preparation requires the retained April fixture')
        started = time.monotonic()
        with transaction.atomic():
            if not options['verify_only']:
                type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            assert_unchanged(run, source)
            dimension_digest, recipe = (source_signatures(run), recipe_digest())
            receipt = HistoryPreparedProjection.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only']:
                    raise CommandError('History prepared receipt is absent')
                if any((model.objects.filter(run=run).exists() for _, model, _, _ in POPULATIONS)):
                    raise CommandError('Unsealed history prepared rows exist; no replacement allowed')
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('fresh.history_prepared_build',%s,true)", [str(run.pk)])
                    for _, model, builder, order in POPULATIONS:
                        query, params = builder(run)
                        fields = [name for name in fields_for(model) if name != 'ordinal']
                        cursor.execute('INSERT INTO mta.' + quote(model._meta.db_table) + ' (run_id,ordinal,' + ','.join(map(quote, fields)) + ') SELECT %s,' + 'row_number() OVER (ORDER BY ' + ','.join((quote(name) + ' NULLS FIRST' for name in order)) + ')-1,' + ','.join(map(quote, fields)) + ' FROM (' + query + ') members', [run.pk, *params])
                        cursor.execute('ANALYZE mta.' + quote(model._meta.db_table))
            results = {name: readback(run, model) for name, model, _, _ in POPULATIONS}
            expected = dict(status='READY', source_digest=source, dimension_digest=dimension_digest, recipe_digest=recipe, **{name + '_count': value[0] for name, value in results.items()}, **{name + '_digest': value[1] for name, value in results.items()})
            if receipt is not None:
                if any((getattr(receipt, name) != value for name, value in expected.items())):
                    raise CommandError('History prepared receipt differs')
            else:
                HistoryPreparedProjection.objects.create(run=run, **expected)
            assert_unchanged(run, source)
            verify_guards(connection)
        self.stdout.write(json.dumps(dict(expected, status='PASS', created=receipt is None, seconds=time.monotonic() - started), sort_keys=True))
