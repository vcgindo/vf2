"""Prepare the immutable native InputData.zip for one completed run.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
from django.core.management.base import BaseCommand, CommandError
from mta.application.native_input_archive import prepare
from mta.runtime.models import CalculationRun


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--run-id', required=True)
        parser.add_argument('--output-digest', required=True)
        parser.add_argument('--opening-file', required=True)
        parser.add_argument('--daily-file', required=True)

    def handle(self, *args, **options):
        run = CalculationRun.objects.get(pk=options['run_id'])
        if run.output_digest != options['output_digest']:
            raise CommandError('Exact output digest required')
        self.stdout.write(json.dumps(prepare(run, options['opening_file'],
            options['daily_file']), sort_keys=True))
