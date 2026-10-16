"""Run one native supplied-input day from initialized or persisted own state."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.runtime.production_daily import execute, inspect_execution
from mta.runtime.production_preflight import PreflightError, require


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('input', type=Path)
        for name in ('sha256', 'initialization', 'source-digest', 'configuration-digest', 'revision', 'pick-output-root'):
            parser.add_argument('--'+name, required=True)
        parser.add_argument('--predecessor')
        parser.add_argument('--predecessor-output-digest')
        parser.add_argument('--retry-capture')
        parser.add_argument('--report-disposition')
        parser.add_argument('--inspect',action='store_true')

    def handle(self, *args, **options):
        try:
            if options['inspect']:
                report,*_=inspect_execution(options['input'].read_bytes(),options['sha256'],
                    initialization_id=options['initialization'],source_digest=options['source_digest'],
                    configuration_digest=options['configuration_digest'],pick_output_root=options['pick_output_root'],
                    execution_revision=options['revision'],retry_capture_id=options['retry_capture'],
                    report_disposition=options.get('report_disposition'),
                    predecessor_id=options['predecessor'],predecessor_output_digest=options['predecessor_output_digest'])
                require(report,'day')
                self.stdout.write(json.dumps(report,sort_keys=True))
                return
            run = execute(options['input'].read_bytes(), options['sha256'],
                initialization_id=options['initialization'], source_digest=options['source_digest'],
                configuration_digest=options['configuration_digest'], execution_revision=options['revision'],
                pick_output_root=options['pick_output_root'], predecessor_id=options['predecessor'],
                predecessor_output_digest=options['predecessor_output_digest'],
                retry_capture_id=options['retry_capture'],report_disposition=options.get('report_disposition'))
            self.stdout.write(json.dumps(dict(status=run.status, run_id=str(run.pk),
                predecessor_id=str(run.predecessor_id) if run.predecessor_id else None,
                business_date=run.business_date.isoformat(), input_digest=run.input_digest,
                output_digest=run.output_digest, input_sha256=options['sha256'],
                serving_selected=False, application_acceptance=False), sort_keys=True))
        except PreflightError as error:
            self.stdout.write(json.dumps(error.report,sort_keys=True))
            raise CommandError('Native '+error.stage+' preflight has blocking requirements') from error
        except Exception as error:
            raise CommandError(str(error)) from error
