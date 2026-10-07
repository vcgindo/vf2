import json
from django.core.management.base import BaseCommand
from mta.runtime.models import CalculationRun
from mta.runtime.offline_scenario import require_run
from mta.presentation.daily_planning_extension import activate
from mta.presentation.offline_rrr import read_published


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--run-id',required=True)
        parser.add_argument('--output-digest',required=True)
        parser.add_argument('--publication-seal',required=True)

    def handle(self,*args,**options):
        run=CalculationRun.objects.get(pk=options['run_id'],output_digest=options['output_digest'])
        require_run(run)
        planning=activate(run,expected_seal=options['publication_seal'])
        rows=read_published(run)
        self.stdout.write(json.dumps(dict(run_id=str(run.pk),planning=planning.extension_digest,
            rrr_rows=len(rows),selected=False)))
