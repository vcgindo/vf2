"""Persist the qualified normal-grid grains once; never build request bags."""
import hashlib
import json
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from mta.presentation import fixture
from mta.presentation.planning_grid_preparation import grid_occurrences, production_grid_occurrences, recipe_digest, production_recipe_digest
from mta.runtime.models import PlanningGridProjection, PlanningExcessGridRow, PlanningFulfillmentGridRow
from mta.runtime.planning_grid_schema import verify_guards
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts

MODELS = (('excess', PlanningExcessGridRow), ('fulfillment', PlanningFulfillmentGridRow))


def fields_for(model):
    return [f.name for f in model._meta.local_fields if f.name not in ('id', 'run')]


def readback(run, model):
    fields = fields_for(model)
    count = 0
    checksum = hashlib.sha256(b'[')
    with connection.chunked_cursor() as c:
        c.execute('SELECT ' + ','.join(map(quote, fields)) + ' FROM mta.' + quote(model._meta.db_table)
                  + ' WHERE run_id=%s ORDER BY ordinal', [run.pk])
        while batch := c.fetchmany(2000):
            for values in batch:
                row = dict(zip(fields, values))
                if row['ordinal'] != count:
                    raise CommandError('Planning grid ordinal drift')
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
            raise CommandError('Planning grid preparation requires PostgreSQL')
        from mta.presentation.daily_preparation import command_binding, assert_unchanged
        run, source = command_binding(options.get('run_id'))
        if run.kind == 'LEGACY_UI_FIXTURE' and str(run.business_date) != '2026-04-07':
            raise CommandError('Planning grids require retained April input')
        started = time.monotonic()
        with transaction.atomic():
            if not options['verify_only']:
                type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            assert_unchanged(run, source)
            receipt = PlanningGridProjection.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only']:
                    raise CommandError('Planning grid receipt absent')
                if any(model.objects.filter(run=run).exists() for _, model in MODELS):
                    raise CommandError('Unsealed Planning grid rows exist; no replacement allowed')
                with connection.cursor() as c:
                    c.execute("SELECT set_config('fresh.planning_grid_build',%s,true)", [str(run.pk)])
                    for family, model in MODELS:
                        builder = production_grid_occurrences if run.kind == 'DAILY_CHAIN' else grid_occurrences
                        query, params = builder(run, family)
                        fields = [name for name in fields_for(model) if name != 'ordinal']
                        order = ['fact_ordinal', 'sku_description_ordinal', 'location_description_ordinal']
                        if family == 'excess':
                            order.append('parent_description_ordinal')
                        order += ['sku_ordinal', 'location_ordinal', 'pair_ordinal']
                        c.execute('INSERT INTO mta.' + quote(model._meta.db_table)
                                  + ' (run_id,ordinal,' + ','.join(map(quote, fields)) + ') '
                                  'SELECT %s,row_number() OVER (ORDER BY '
                                  + ','.join(quote(name) + ' NULLS FIRST' for name in order)
                                  + ')-1,' + ','.join(map(quote, fields))
                                  + ' FROM (' + query + ') occurrences', [run.pk, *params])
            values = {}
            for family, model in MODELS:
                count, checksum = readback(run, model)
                values[family + '_count'] = count
                values[family + '_digest'] = checksum
            recipe = production_recipe_digest() if run.kind == 'DAILY_CHAIN' else recipe_digest()
            expected = dict(source_digest=source, recipe_digest=recipe, **values)
            if receipt:
                if any(getattr(receipt, name) != value for name, value in expected.items()):
                    raise CommandError('Planning grid receipt differs')
            else:
                PlanningGridProjection.objects.create(run=run, **expected)
            assert_unchanged(run, source)
        self.stdout.write(json.dumps(dict(status='PASS', created=receipt is None,
                                         seconds=time.monotonic()-started, **expected), sort_keys=True))
