"""Bind approved access to an unchanged READY publication; never select it."""
import json
from django.core.management.base import BaseCommand
from mta.runtime.models import CalculationRun
from mta.presentation.daily_activation import activate


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--run-id', required=True)
        parser.add_argument('--output-digest', required=True)
        parser.add_argument('--publication-seal', required=True)

    def handle(self, *args, **options):
        from mta.presentation.native_publication import require_mode
        require_mode()
        run = CalculationRun.objects.get(pk=options['run_id'])
        result = activate(run, expected_output_digest=options['output_digest'],
            expected_seal=options['publication_seal'])
        self.stdout.write(json.dumps(dict(run_id=str(run.pk),
            publication_seal=result.publication_seal, activation_digest=result.activation_digest,
            configuration_digest=result.configuration_digest, selected=False), sort_keys=True))
