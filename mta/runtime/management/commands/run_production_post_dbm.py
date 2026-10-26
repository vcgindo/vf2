"""Continue the qualified retained DBM day through BTR and terminal publication."""
import json
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--run', required=True)
        parser.add_argument('--expected-dbm-digest', required=True)
        parser.add_argument('--expected-action-revision', required=True, type=int)
        parser.add_argument('--command-key', required=True)
        parser.add_argument('--worker-reference', required=True)
        parser.add_argument('--recovery-of')
        parser.add_argument('--inspect', action='store_true')

    def handle(self, *args, **options):
        from mta.presentation.native_mode import require_configuration
        from mta.runtime.production_post_dbm import execute
        require_configuration()
        try:
            report = execute(options['run'], expected_dbm_digest=options['expected_dbm_digest'],
                expected_action_revision=options['expected_action_revision'], command_key=options['command_key'],
                worker_reference=options['worker_reference'], recovery_of=options['recovery_of'],
                inspect_only=options['inspect'])
            self.stdout.write(json.dumps(report, sort_keys=True))
        except Exception as error:
            raise CommandError(str(error)) from error
