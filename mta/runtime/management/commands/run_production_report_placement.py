"""Run the explicitly configured owned-test report placement through an existing scope."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.runtime.production_preflight import PreflightError


class Command(BaseCommand):
    help=__doc__

    def add_arguments(self,parser):
        parser.add_argument('input',type=Path)
        parser.add_argument('--scope',choices=('Full','UptoBPR','UptoDBM'),required=True)
        for name in ('sha256','initialization','source-digest','configuration-digest','revision',
                     'pick-output-root','command-key','runtime-reports-sha256'):
            parser.add_argument('--'+name,required=True)
        parser.add_argument('--runtime-reports-file',type=Path,required=True)
        for name in ('predecessor','predecessor-output-digest','worker-reference','recovery-of','retry-capture'):
            parser.add_argument('--'+name)
        parser.add_argument('--inspect',action='store_true')
        parser.add_argument('--repair-files',action='store_true')

    def handle(self,*args,**options):
        from mta.presentation.native_mode import require_configuration
        from mta.runtime.production_report_placement import execute
        from mta.runtime.scope_runtime_reports import load
        require_configuration()
        try:
            result=execute(options['input'].read_bytes(),options['sha256'],scope=options['scope'],
                initialization_id=options['initialization'],source_digest=options['source_digest'],
                configuration_digest=options['configuration_digest'],execution_revision=options['revision'],
                pick_output_root=options['pick_output_root'],predecessor_id=options['predecessor'],
                predecessor_output_digest=options['predecessor_output_digest'],command_key=options['command_key'],
                runtime_reports=load(options['runtime_reports_file'],options['runtime_reports_sha256']),
                worker_reference=options['worker_reference'],recovery_of=options['recovery_of'],
                retry_capture_id=options['retry_capture'],inspect_only=options['inspect'],repair_files=options['repair_files'])
            self.stdout.write(json.dumps(result,sort_keys=True))
        except PreflightError as error:
            self.stdout.write(json.dumps(error.report,sort_keys=True))
            raise CommandError('Native placement preflight has blocking requirements') from error
        except Exception as error:raise CommandError(str(error)) from error
