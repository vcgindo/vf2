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

    def handle(self, *args, **options):
        run=CalculationRun.objects.get(pk=options['run_id'])
        if (run.kind!='DAILY_CHAIN' or run.status!='SUCCEEDED' or run.output_digest!=options['output_digest']
                or run.parity_summary.get('status') not in ('PASS','PASS_WITH_LEGACY_FLAWS')):
            raise CommandError('Explicit independently accepted daily calculation required')
        # Apply the same native readback/catalogue/action/projection checks as
        # startup before emitting any selection values. A UI seal is not a
        # replacement for the existing calculation admission boundary.
        from mta.presentation.admission import verify
        verify(run)
        receipt=require_ready(run, verify_rows=True)
        # No environment/file/service mutation: the prior selection survives any
        # failure. Apply these together only through the owned deployment config.
        self.stdout.write(json.dumps(dict(VF_MTA_PUBLISHED_RUN=str(run.pk),
            VF_MTA_PUBLISHED_DIGEST=run.output_digest, VF_MTA_DAILY_PUBLICATION='1',
            VF_BTR_REPORTING_GENERATION=receipt.layers['btr']['receipt']['generation'],
            configuration_digest=receipt.configuration_digest, publication_seal=receipt.seal_digest),sort_keys=True))
