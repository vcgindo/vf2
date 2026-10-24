"""Capture one native JSON day and accept only its PRE_BPR/BPR work.

Does not select a serving generation or acknowledge whole-scope readiness.
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.runtime.production_preflight import PreflightError


class Command(BaseCommand):
    help=__doc__

    def add_arguments(self,parser):
        parser.add_argument('input',type=Path)
        for name in ('sha256','initialization','source-digest','configuration-digest','revision','pick-output-root'):
            parser.add_argument('--'+name,required=True)
        parser.add_argument('--predecessor')
        parser.add_argument('--predecessor-output-digest')
        parser.add_argument('--inspect',action='store_true')
        parser.add_argument('--command-key',required=True)
        parser.add_argument('--worker-reference',required=True)
        parser.add_argument('--recovery-of')
        parser.add_argument('--repair-files',action='store_true')

    def handle(self,*args,**options):
        from mta.presentation.native_mode import require_configuration
        from mta.runtime.production_scope import execute
        require_configuration()
        try:
            report=execute(options['input'].read_bytes(),options['sha256'],
                initialization_id=options['initialization'],source_digest=options['source_digest'],
                configuration_digest=options['configuration_digest'],execution_revision=options['revision'],
                pick_output_root=options['pick_output_root'],predecessor_id=options['predecessor'],
                predecessor_output_digest=options['predecessor_output_digest'],
                command_key=options['command_key'],worker_reference=options['worker_reference'],
                recovery_of=options['recovery_of'],repair_files=options['repair_files'],
                inspect_only=options['inspect'])
            self.stdout.write(json.dumps(report,sort_keys=True))
        except PreflightError as error:
            self.stdout.write(json.dumps(error.report,sort_keys=True))
            raise CommandError('Native '+error.stage+' preflight has blocking requirements') from error
        except Exception as error:raise CommandError(str(error)) from error
