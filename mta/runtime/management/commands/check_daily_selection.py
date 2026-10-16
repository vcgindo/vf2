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
        run=CalculationRun.objects.get(pk=options['run_id'])
        from mta.presentation import operational_admission, native_publication
        native = native_publication.enabled()
        if native:
            native_publication.require_mode()
        elif options.get('selection_file'):
            raise CommandError('Selection files require explicit native admission')
        operational = operational_admission.enabled()
        if (run.kind!='DAILY_CHAIN' or run.status!='SUCCEEDED' or run.output_digest!=options['output_digest']
                or (not native and not operational and run.parity_summary.get('status') not in ('PASS','PASS_WITH_LEGACY_FLAWS'))):
            raise CommandError('Explicit independently accepted daily calculation required')
        # Apply the same native readback/catalogue/action/projection checks as
        # startup before emitting any selection values. A UI seal is not a
        # replacement for the existing calculation admission boundary.
        from mta.presentation.admission import verify
        accepted = operational_admission.verify(run, selected=False) if operational else None
        if not operational:
            verify(run)
        receipt=require_ready(run, verify_rows=True)
        # No environment/file/service mutation: the prior selection survives any
        # failure. Apply these together only through the owned deployment config.
        values = dict(VF_MTA_PUBLISHED_RUN=str(run.pk),
            VF_MTA_PUBLISHED_DIGEST=run.output_digest, VF_MTA_DAILY_PUBLICATION='1',
            VF_BTR_REPORTING_GENERATION=receipt.layers['btr']['receipt']['generation'],
            configuration_digest=receipt.configuration_digest, publication_seal=receipt.seal_digest)
        if accepted is not None:
            values.update(VF_MTA_OPERATIONAL_POLICY=accepted.policy,
                          VF_MTA_OPERATIONAL_RECEIPT=accepted.receipt_digest)
        if native:
            from mta.presentation.planning_summary_daily import require_ready as require_summary
            from mta.presentation.native_selection import candidate, write
            summary = require_summary(run, verify_rows=True)
            bundle = candidate(run, receipt, summary, native_publication.identity(run))
            values['native_selection'] = bundle
            if options.get('selection_file'):
                write(options['selection_file'], bundle)
        self.stdout.write(json.dumps(values, sort_keys=True))
