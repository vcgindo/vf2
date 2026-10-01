"""Publish the source-backed current-day Excess report from an accepted run."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.presentation.excess_storage import publish_existing,read_excess
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha,write_rows


class Command(BaseCommand):
    help=__doc__

    def add_arguments(self,parser):
        parser.add_argument('--run',required=True)
        parser.add_argument('--output-digest',required=True)
        parser.add_argument('--evidence',type=Path,required=True)

    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists():
            raise CommandError('Preserve receipts; choose a new evidence directory')
        target.mkdir(parents=True)
        run=CalculationRun.objects.get(pk=options['run'])
        before=run_identity(run)
        result=dict(status='FAILED',run=before)
        try:
            projection=publish_existing(run.pk,expected_output_digest=options['output_digest'])
            again=publish_existing(run.pk,expected_output_digest=options['output_digest'])
            if again.created_at!=projection.created_at or before!=run_identity(run):
                raise CommandError('Publication changed accepted identity or was not idempotent')
            rows=read_excess(run,output=read_outputs(run))
            root=Path(__file__).resolve().parents[4]
            result.update(status='PERSISTED_READBACK_PASS_COMPARISON_REQUIRED',
                business_date=run.business_date.isoformat(),source_digest=projection.source_digest,
                producer_sha256=projection.producer_sha256,
                sources={name:file_sha(root/name) for name in ('mta/presentation/excess.py','mta/presentation/excess_storage.py')},
                file='excess.jsonl.gz',**write_rows(target/'excess.jsonl.gz',rows),
                run_unchanged=True,idempotent=True,serving_changes=False)
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc))
            raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(rows=len(rows),receipt_sha256=file_sha(target/'receipt.json'))))
