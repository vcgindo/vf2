"""Publish/read the complete current-day Expedite report without replay."""
import gzip
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.presentation.expedite_storage import read_expedite
from development.expedite_storage import publish_existing
from mta.presentation.expedite_views import counts
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha


class Command(BaseCommand):
    help=__doc__
    def add_arguments(self,parser):
        parser.add_argument('--run',required=True); parser.add_argument('--output-digest',required=True)
        parser.add_argument('--evidence',type=Path,required=True)

    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Preserve earlier receipts; choose a new directory')
        target.mkdir(parents=True)
        run=CalculationRun.objects.get(pk=options['run']); before=run_identity(run)
        result=dict(status='FAILED',run=before)
        try:
            receipt=publish_existing(run.pk,expected_output_digest=options['output_digest'])
            again=publish_existing(run.pk,expected_output_digest=options['output_digest'])
            if receipt.created_at!=again.created_at or before!=run_identity(run):
                raise CommandError('Accepted identity changed or publication not idempotent')
            output=read_outputs(run); rows=read_expedite(run,output=output)
            values=dict(rows=rows,counts={kind:counts(output,rows,kind,products=None,locations=None) for kind in ('parent','child')})
            path=target/'expedite.json.gz'
            with gzip.open(path,'wt') as stream: json.dump(values,stream)
            root=Path(__file__).resolve().parents[4]
            result.update(status='PERSISTED_READBACK_PASS_COMPARISON_REQUIRED',business_date=run.business_date.isoformat(),
                producer_sha256=receipt.producer_sha256,source_digest=receipt.source_digest,
                file=path.name,sha256=file_sha(path),rows=len(rows),
                sources={name:file_sha(root/name) for name in ('mta/presentation/expedite.py',
                    'mta/presentation/expedite_storage.py','mta/presentation/expedite_views.py','mta/presentation/rrr.py')},
                run_unchanged=True,idempotent=True,serving_changes=False)
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(rows=len(rows),counts=values['counts'],receipt_sha256=file_sha(target/'receipt.json'))))
