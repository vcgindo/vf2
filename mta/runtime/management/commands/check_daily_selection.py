"""Validate an explicit selection before changing the isolated instance config."""
import json
from django.core.management.base import BaseCommand, CommandError
from mta.runtime.models import CalculationRun
from mta.presentation.daily_publication import require_ready


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--run-id', required=True)
        parser.add_argument('--output-digest', required=True)
        parser.add_argument('--selection-file')

    def handle(self, *args, **options):
        from mta.presentation.native_publication import require_mode
        require_mode()
        run = CalculationRun.objects.get(pk=options['run_id'])
        from mta.presentation import native_publication
        native = native_publication.enabled()
        if native:
            native_publication.require_mode()
        elif options.get('selection_file'):
            raise CommandError('Selection files require explicit native admission')
        operational = False
        if run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED' or run.output_digest != options['output_digest'] or (not native and (not operational) and (run.parity_summary.get('status') not in ('PASS', 'PASS_WITH_LEGACY_FLAWS'))):
            raise CommandError('Explicit independently accepted daily calculation required')
        from mta.presentation.admission import verify
        accepted = None
        verify(run)
        receipt = require_ready(run, verify_rows=True)
        values = dict(VF_MTA_PUBLISHED_RUN=str(run.pk), VF_MTA_PUBLISHED_DIGEST=run.output_digest, VF_MTA_DAILY_PUBLICATION='1', VF_BTR_REPORTING_GENERATION=receipt.layers['btr']['receipt']['generation'], configuration_digest=receipt.configuration_digest, publication_seal=receipt.seal_digest)
        if accepted is not None:
            values.update(VF_MTA_OPERATIONAL_POLICY=accepted.policy, VF_MTA_OPERATIONAL_RECEIPT=accepted.receipt_digest)
        if native:
            from mta.presentation.planning_summary_daily import require_ready as require_summary
            from mta.presentation.native_selection import candidate, write, read, selected_archive
            summary = require_summary(run, verify_rows=True)
            from django.conf import settings
            loaded = getattr(settings, 'VF_MTA_SELECTION', None)
            archived = selected_archive(run) if loaded and loaded['run_id'] == str(run.pk) else None
            if options.get('selection_file'):
                from pathlib import Path
                path = Path(options['selection_file'])
                if path.exists():
                    previous = read(path)
                    if previous['run_id'] == str(run.pk):
                        archived = previous.get('input_archive')
            bundle = candidate(run, receipt, summary, native_publication.identity(run), input_archive=archived)
            values['native_selection'] = bundle
            if options.get('selection_file'):
                write(options['selection_file'], bundle)
        self.stdout.write(json.dumps(values, sort_keys=True))
