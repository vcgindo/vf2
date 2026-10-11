"""Prepare exact Planning contributions without calculation or selection."""
import json
from django.core.management.base import BaseCommand
from mta.runtime.models import CalculationRun
from mta.presentation.planning_summary import prepare, binding, verify


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--run-id',required=True)
        parser.add_argument('--verify-only',action='store_true')

    def handle(self,*args,**options):
        run=CalculationRun.objects.get(pk=options['run_id'])
        if options['verify_only']:
            from mta.runtime.planning_summary_models import PlanningSummaryReceipt
            identities,_,_=binding(run)
            result=PlanningSummaryReceipt.objects.get(run=run,**identities)
            verify(result,identities)
        else:
            result=prepare(run)
        self.stdout.write(json.dumps(dict(generation=str(result.pk),status=result.status,
            source_digest=result.source_digest,recipe_digest=result.recipe_digest,
            rows_digest=result.rows_digest,row_count=result.row_count)))
