"""Continue the captured owned-test placement from its accepted BPR or DBM cut."""
import json
from django.core.management.base import BaseCommand,CommandError


class Command(BaseCommand):
    help=__doc__

    def add_arguments(self,parser):
        parser.add_argument('run_id')
        parser.add_argument('--scope',choices=('PostBPR','PostDBM'),required=True)
        for name in ('expected-phase-digest','command-key','worker-reference'):
            parser.add_argument('--'+name,required=True)
        parser.add_argument('--expected-action-revision',type=int,required=True)
        parser.add_argument('--recovery-of')
        parser.add_argument('--inspect',action='store_true')

    def handle(self,*args,**options):
        from mta.presentation.native_mode import require_configuration
        from mta.runtime.production_report_placement import continue_run
        require_configuration()
        try:
            result=continue_run(options['run_id'],scope=options['scope'],
                expected_phase_digest=options['expected_phase_digest'],
                expected_action_revision=options['expected_action_revision'],command_key=options['command_key'],
                worker_reference=options['worker_reference'],recovery_of=options['recovery_of'],inspect_only=options['inspect'])
            self.stdout.write(json.dumps(result,sort_keys=True))
        except Exception as error:raise CommandError(str(error)) from error
