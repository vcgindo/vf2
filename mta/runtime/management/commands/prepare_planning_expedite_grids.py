"""Persist the qualified normal-grid grains once; never build request bags."""
import hashlib
import json
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from mta.presentation import fixture
from mta.presentation.planning_expedite_preparation import grid_occurrences, recipe_digest
from mta.runtime.models import PlanningExpediteGridProjection, PlanningExpediteGridOccurrence
from mta.runtime.planning_expedite_grid_schema import verify_guards
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts

MODELS = (('row', PlanningExpediteGridOccurrence),)


def fields_for(model):
    return [f.name for f in model._meta.local_fields if f.name not in ('id', 'run')]


def readback(run, model):
    fields = fields_for(model)
    count = 0
    ordinals = {}
    checksum = hashlib.sha256(b'[')
    with connection.chunked_cursor() as c:
        c.execute('SELECT ' + ','.join(map(quote, fields)) + ' FROM mta.' + quote(model._meta.db_table)
                  + ' WHERE run_id=%s ORDER BY direction,branch,ordinal', [run.pk])
        while batch := c.fetchmany(2000):
            for values in batch:
                row = dict(zip(fields, values))
                group = (row['direction'],row['branch'])
                if row['ordinal'] != ordinals.get(group,0):
                    raise CommandError('Planning Expedite grid ordinal drift')
                ordinals[group] = ordinals.get(group,0)+1
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

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('Planning Expedite grid preparation requires PostgreSQL')
        run, source = fixture.binding()
        if str(run.business_date) != '2026-04-07':
            raise CommandError('Planning Expedite grids require retained April input')
        started = time.monotonic()
        with transaction.atomic():
            type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            if fixture.binding()[1] != source:
                raise CommandError('Planning admission changed before grid preparation')
            receipt = PlanningExpediteGridProjection.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only']:
                    raise CommandError('Planning Expedite grid receipt absent')
                if any(model.objects.filter(run=run).exists() for _, model in MODELS):
                    raise CommandError('Unsealed Planning Expedite grid rows exist; no replacement allowed')
                with connection.cursor() as c:
                    c.execute("SELECT set_config('fresh.planning_expedite_grid_build',%s,true)", [str(run.pk)])
                    model = PlanningExpediteGridOccurrence
                    for direction in ('parent','child'):
                        for branch in ('dispatch','availability'):
                            query, params = grid_occurrences(run,direction,branch)
                            fields = [f for f in fields_for(model) if f not in ('ordinal','direction','branch')]
                            order = ['fact_ordinal','standard_ordinal','sku_description_ordinal','location_description_ordinal',
                                     'parent_description_ordinal','sku_ordinal','location_ordinal','pair_ordinal','master_ordinal']
                            c.execute('INSERT INTO mta.'+quote(model._meta.db_table)+' (run_id,direction,branch,ordinal,'
                                      +','.join(map(quote,fields))+') SELECT %s,%s,%s,row_number() OVER (ORDER BY '
                                      +','.join(quote(f)+' NULLS FIRST' for f in order)+')-1,'+','.join(map(quote,fields))
                                      +' FROM ('+query+') occurrences',[run.pk,direction,branch,*params])
            values = {}
            for family, model in MODELS:
                count, checksum = readback(run, model)
                values[family + '_count'] = count
                values['rows_digest'] = checksum
            expected = dict(source_digest=source, recipe_digest=recipe_digest(), **values)
            if receipt:
                if any(getattr(receipt, name) != value for name, value in expected.items()):
                    raise CommandError('Planning Expedite grid receipt differs')
            else:
                PlanningExpediteGridProjection.objects.create(run=run, **expected)
            if fixture.binding()[1] != source:
                raise CommandError('Planning admission changed before commit')
        self.stdout.write(json.dumps(dict(status='PASS', created=receipt is None,
                                         seconds=time.monotonic()-started, **expected), sort_keys=True))
