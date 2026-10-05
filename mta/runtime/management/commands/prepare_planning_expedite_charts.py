"""Prepare exact Expedite chart membership once on the retained fixture."""
import hashlib
import json
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from mta.presentation import fixture
from mta.presentation.planning_expedite_chart_preparation import members, prepost_members, recipe_digest
from mta.presentation.planning_expedite_transit_preparation import pick_source
from mta.runtime.models import PlanningExpediteChartProjection, PlanningExpediteChartMember, PlanningExpeditePrepostMember
from mta.runtime.planning_expedite_chart_schema import verify_guards
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts

MODELS = (('member',PlanningExpediteChartMember),('prepost',PlanningExpeditePrepostMember))
GRAINS = [('parent',f) for f in ('critical','receiving','nil_stock','chronic')]+[('child',f) for f in ('critical','receiving')]


def fields_for(model):
    return [f.name for f in model._meta.local_fields if f.name not in ('id','run')]


def readback(run, model):
    count, checksum = 0, hashlib.sha256(b'[')
    fields = fields_for(model)
    groups = {}
    order = 'direction,family,ordinal' if model == PlanningExpediteChartMember else 'ordinal'
    with connection.chunked_cursor() as c:
        c.execute('SELECT '+','.join(map(quote,fields))+' FROM mta.'+quote(model._meta.db_table)+
                  ' WHERE run_id=%s ORDER BY '+order,[run.pk])
        while batch := c.fetchmany(2000):
            for values in batch:
                row = dict(zip(fields,values))
                group = (row.get('direction'),row.get('family'))
                if row['ordinal'] != groups.get(group,0):
                    raise CommandError('Planning Expedite chart ordinal drift')
                if count: checksum.update(b',')
                for part in canonical_parts(row): checksum.update(part)
                count += 1
                groups[group] = groups.get(group,0)+1
    checksum.update(b']')
    return count, checksum.hexdigest()


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('Planning Expedite chart requires PostgreSQL')
        run, source = fixture.binding()
        if str(run.business_date) != '2026-04-07':
            raise CommandError('Planning Expedite chart requires retained April input')
        started = time.monotonic()
        with transaction.atomic():
            type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            pick_digest = pick_source(verify_values=True)
            receipt = PlanningExpediteChartProjection.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only']:
                    raise CommandError('Planning Expedite chart receipt absent')
                if any(model.objects.filter(run=run).exists() for _,model in MODELS):
                    raise CommandError('Unsealed chart rows exist; no replacement allowed')
                with connection.cursor() as c:
                    c.execute("SELECT set_config('fresh.planning_expedite_chart_build',%s,true)",[str(run.pk)])
                    for family,model in MODELS:
                        grains = GRAINS if family=='member' else [(None,None)]
                        for direction,grain in grains:
                            query,params = members(run,direction,grain) if family=='member' else prepost_members(run)
                            fields=[f for f in fields_for(model) if f not in ('ordinal','direction','family')]
                            order=['scope_ordinal','fact_ordinal','master_ordinal','description_ordinal','location_ordinal'] if family=='member' else ['scope_ordinal','fact_ordinal']
                            extra_columns='direction,family,' if family=='member' else ''
                            extra_values='%s,%s,' if family=='member' else ''
                            extra_params=[direction,grain] if family=='member' else []
                            c.execute('INSERT INTO mta.'+quote(model._meta.db_table)+' (run_id,'+extra_columns+'ordinal,'+','.join(map(quote,fields))+') SELECT %s,'+extra_values+
                                'row_number() OVER (ORDER BY '+','.join(quote(f)+' NULLS FIRST' for f in order)+')-1,'+','.join(map(quote,fields))+' FROM ('+query+') ingredients',[run.pk,*extra_params,*params])
            values = {}
            for family,model in MODELS:
                values[family+'_count'],values[family+'_digest'] = readback(run,model)
            expected = dict(source_digest=source,recipe_digest=recipe_digest(),pick_digest=pick_digest,**values)
            if receipt:
                if any(getattr(receipt,name) != value for name,value in expected.items()):
                    raise CommandError('Planning Expedite chart receipt differs')
            else:
                PlanningExpediteChartProjection.objects.create(run=run,**expected)
            if fixture.binding()[1] != source:
                raise CommandError('Planning source admission changed; preparation rolled back')
        self.stdout.write(json.dumps(dict(status='PASS',created=receipt is None,
                                         seconds=time.monotonic()-started,**expected),sort_keys=True))
