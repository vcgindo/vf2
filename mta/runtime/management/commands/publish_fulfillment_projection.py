"""Explicit accepted-run publication/readback of current-day Fulfilment."""
import gzip
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.presentation.fulfillment import PRODUCER_SHA
from mta.presentation.fulfillment_storage import publish_existing,read_fulfillment
from mta.presentation.fulfillment_views import joined_rows,detail_aliases
from mta.presentation.fulfillment_grid import fulfillment_grid_rows,fulfillment_grid_config
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha


class Command(BaseCommand):
    help=__doc__
    def add_arguments(self,parser):
        parser.add_argument('--run',required=True)
        parser.add_argument('--output-digest',required=True)
        parser.add_argument('--evidence',type=Path,required=True)

    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Preserve previous evidence; select a new directory')
        target.mkdir(parents=True)
        run=CalculationRun.objects.get(pk=options['run'])
        before=run_identity(run)
        root=Path(__file__).resolve().parents[4]
        sources={name:file_sha(root/name) for name in ('mta/presentation/fulfillment.py',
            'mta/presentation/fulfillment_storage.py','mta/presentation/fulfillment_grid.py','mta/presentation/fulfillment_views.py')}
        result=dict(status='FAILED',run=before,business_date=run.business_date.isoformat(),sources=sources)
        try:
            first=publish_existing(run.pk,expected_output_digest=options['output_digest'])
            second=publish_existing(run.pk,expected_output_digest=options['output_digest'])
            output=read_outputs(run)
            values=read_fulfillment(run,output=output)
            values['grid']=fulfillment_grid_rows(joined_rows(output,values['summary']),detail_aliases(values['details']))
            values.update(count=len(values['grid']),uiConfig=fulfillment_grid_config())
            if first.created_at!=second.created_at or before!=run_identity(run):
                raise CommandError('Publication was not idempotent or accepted identity changed')
            path=target/'fulfillment.json.gz'
            with gzip.open(path,'wt',encoding='utf-8') as stream: json.dump(values,stream)
            result.update(status='PERSISTED_READBACK_PASS_COMPARISON_REQUIRED',producer_sha256=PRODUCER_SHA,
                source_digest=first.source_digest,calculation_digest=first.calculation_digest,
                file=path.name,sha256=file_sha(path),run_unchanged=True,idempotent=True,
                qualification='Producer and unscoped grid only; authenticated filters/chart/browser acceptance remains open')
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc))
            raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(summary=len(values['summary']),details=len(values['details']),
            grid=len(values['grid']),receipt_sha256=file_sha(target/'receipt.json'))))
