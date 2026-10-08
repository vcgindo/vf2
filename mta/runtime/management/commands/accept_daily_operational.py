"""Verify one supported owner and atomically bind operational acceptance/access."""
import json
from django.core.management.base import BaseCommand, CommandError
from mta.presentation.operational_admission import issue


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        for name in ('run-id', 'output-digest', 'attempt', 'artifact', 'finalization-config'):
            parser.add_argument('--' + name, required=True)
        parser.add_argument('--repair')

    def handle(self, *args, **options):
        try:
            row = issue(options['run_id'], output_digest=options['output_digest'],
                attempt_id=options['attempt'], repair_id=options['repair'], artifact_path=options['artifact'],
                finalization_path=options['finalization_config'])
            self.stdout.write(json.dumps(dict(run_id=str(row.pk), policy=row.policy,
                qualification=row.qualification, receipt=row.receipt_digest,
                activation=row.activation_digest, selected=False)))
        except Exception as exc:
            raise CommandError(str(exc)) from exc
