"""Prepare the finite daily report roster without selecting or certifying it."""
import json
from django.core.management.base import BaseCommand, CommandError
from mta.presentation.daily_publication import prepare_reporting_generation


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--run-id', required=True)
        parser.add_argument('--output-digest', required=True)

    def handle(self, *args, **options):
        from mta.presentation import qualified_consumption
        if qualified_consumption.enabled():
            from mta.runtime.models import CalculationRun
            run = CalculationRun.objects.get(pk=options['run_id'])
            qualified_consumption.verify(run)
        receipt, summary = prepare_reporting_generation(options['run_id'], expected_output_digest=options['output_digest'])
        self.stdout.write(json.dumps(dict(run_id=str(receipt.run_id), status=receipt.status,
            seal_digest=receipt.seal_digest, layers=receipt.layers,
            planning_summary=dict(generation=str(summary.pk), status=summary.status,
                rows_digest=summary.rows_digest)), sort_keys=True))
        if receipt.status != 'READY':
            raise CommandError('Daily calculation remains unselected: required report layers are incomplete')
