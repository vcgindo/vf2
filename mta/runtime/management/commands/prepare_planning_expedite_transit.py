"""Prepare exact parent Expedite nested-transit ingredients once on the retained fixture."""
import hashlib
import json
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from mta.presentation.planning_expedite_transit_preparation import (base_query, match_query,
    production_base_query, production_match_query, pick_binding, recipe_digest,
    production_recipe_digest)
from mta.runtime.models import PlanningExpediteTransitProjection, PlanningExpediteTransitBase, PlanningExpediteTransitMatch
from mta.runtime.planning_expedite_transit_schema import verify_guards
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts

MODELS = (('base',PlanningExpediteTransitBase,base_query),('match',PlanningExpediteTransitMatch,match_query))


def fields_for(model):
    return [f.name for f in model._meta.local_fields if f.name not in ('id','run')]


def readback(run, model):
    count, checksum = 0, hashlib.sha256(b'[')
    fields = fields_for(model)
    with connection.chunked_cursor() as c:
        c.execute('SELECT '+','.join(map(quote,fields))+' FROM mta.'+quote(model._meta.db_table)+
                  ' WHERE run_id=%s ORDER BY ordinal',[run.pk])
        while batch := c.fetchmany(2000):
            for values in batch:
                row = dict(zip(fields,values))
                if row['ordinal'] != count:
                    raise CommandError('Planning Expedite transit ordinal drift')
                if count: checksum.update(b',')
                for part in canonical_parts(row): checksum.update(part)
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
            raise CommandError('Planning Expedite transit requires PostgreSQL')
        from mta.presentation.daily_preparation import command_binding, assert_unchanged
        run, source = command_binding(options.get('run_id'))
        started = time.monotonic()
        with transaction.atomic():
            if not options['verify_only']:
                type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            pick_digest = pick_binding(run, verify_values=True)
            receipt = PlanningExpediteTransitProjection.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only']:
                    raise CommandError('Planning Expedite transit receipt absent')
                if any((model.objects.filter(run=run).exists() for _, model, _ in MODELS)):
                    raise CommandError('Unsealed transit rows exist; no replacement allowed')
                with connection.cursor() as c:
                    c.execute("SELECT set_config('fresh.planning_expedite_transit_build',%s,true)", [str(run.pk)])
                    builders = ((name, model, (production_base_query if name == 'base' else production_match_query) if run.kind == 'DAILY_CHAIN' else builder) for name, model, builder in MODELS)
                    for _, model, builder in builders:
                        query, params = builder(run)
                        fields = ','.join(map(quote, fields_for(model)))
                        c.execute('INSERT INTO mta.' + quote(model._meta.db_table) + ' (run_id,' + fields + ') SELECT %s,' + fields + ' FROM (' + query + ') ingredients', [run.pk, *params])
            values = {}
            for family, model, _ in MODELS:
                values[family + '_count'], values[family + '_digest'] = readback(run, model)
            recipe = production_recipe_digest() if run.kind == 'DAILY_CHAIN' else recipe_digest()
            expected = dict(source_digest=source, recipe_digest=recipe, pick_digest=pick_digest, **values)
            if receipt:
                if any((getattr(receipt, name) != value for name, value in expected.items())):
                    raise CommandError('Planning Expedite transit receipt differs')
            else:
                PlanningExpediteTransitProjection.objects.create(run=run, **expected)
            assert_unchanged(run, source)
        self.stdout.write(json.dumps(dict(status='PASS', created=receipt is None, seconds=time.monotonic() - started, **expected), sort_keys=True))
