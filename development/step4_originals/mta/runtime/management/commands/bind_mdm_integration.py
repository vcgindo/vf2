"""Seal existing MDM owners against an explicitly accepted own publication."""
import json
from django.core.management.base import BaseCommand
from mta.mdm.integration_source import bind
from mta.runtime.models import CalculationRun, MdmSource


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--source', required=True, type=int)
        parser.add_argument('--source-digest', required=True)
        parser.add_argument('--run', required=True)
        parser.add_argument('--output-digest', required=True)

    def handle(self, *args, **options):
        source = MdmSource.objects.get(pk=options['source'], digest=options['source_digest'])
        run = CalculationRun.objects.get(pk=options['run'], output_digest=options['output_digest'],
                                         kind='DAILY_CHAIN', status='SUCCEEDED')
        seal = bind(source, run)
        self.stdout.write(json.dumps(dict(source=source.pk, digest=seal.digest,
                                          receipt=seal.receipt)))
