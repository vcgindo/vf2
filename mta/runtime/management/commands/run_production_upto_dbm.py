"""Capture a fresh native day through DBM and stop before BTR.

Calculation acceptance does not select a serving generation or certify UI readiness.
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.runtime.production_preflight import PreflightError


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('input', type=Path)
        for name in ('sha256','initialization','source-digest','configuration-digest',
                     'revision','pick-output-root','command-key','worker-reference',
                     'runtime-reports-sha256','dispositions-sha256'):
            parser.add_argument('--'+name, required=True)
        for name in ('runtime-reports-file','dispositions-file'):
            parser.add_argument('--'+name, type=Path, required=True)
        parser.add_argument('--predecessor')
        parser.add_argument('--predecessor-output-digest')
        parser.add_argument('--recovery-of')
        parser.add_argument('--inspect', action='store_true')
        parser.add_argument('--repair-files', action='store_true')

    def handle(self, *args, **options):
        from mta.presentation.native_mode import require_configuration
        from mta.runtime.production_upto_dbm import execute, load_disposition
        from mta.runtime.scope_runtime_reports import load
        require_configuration()
        try:
            report = execute(options['input'].read_bytes(), options['sha256'],
                initialization_id=options['initialization'], source_digest=options['source_digest'],
                configuration_digest=options['configuration_digest'], execution_revision=options['revision'],
                pick_output_root=options['pick_output_root'], predecessor_id=options['predecessor'],
                predecessor_output_digest=options['predecessor_output_digest'],
                command_key=options['command_key'], worker_reference=options['worker_reference'],
                runtime_reports=load(options['runtime_reports_file'], options['runtime_reports_sha256']),
                dispositions=load_disposition(options['dispositions_file'], options['dispositions_sha256']),
                recovery_of=options['recovery_of'], inspect_only=options['inspect'],
                repair_files=options['repair_files'])
            self.stdout.write(json.dumps(report, sort_keys=True))
        except PreflightError as error:
            self.stdout.write(json.dumps(error.report, sort_keys=True))
            raise CommandError('Native '+error.stage+' preflight has blocking requirements') from error
        except Exception as error:
            raise CommandError(str(error)) from error
