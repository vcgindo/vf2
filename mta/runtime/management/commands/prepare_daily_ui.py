"""Prepare the finite daily report roster without selecting or certifying it."""
import json
from django.core.management.base import BaseCommand, CommandError
from mta.presentation.daily_publication import prepare


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--run-id', required=True)
        parser.add_argument('--output-digest', required=True)

    def handle(self, *args, **options):
        receipt = prepare(options['run_id'], expected_output_digest=options['output_digest'])
        self.stdout.write(json.dumps(dict(run_id=str(receipt.run_id), status=receipt.status,
            seal_digest=receipt.seal_digest, layers=receipt.layers), sort_keys=True))
        if receipt.status != 'READY':
            raise CommandError('Daily calculation remains unselected: required report layers are incomplete')
