"""Read-only chart export from the explicit accepted PostgreSQL publication."""
import gzip
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.presentation.context import publication
from mta.presentation.fulfillment_storage import read_fulfillment
from mta.presentation.fulfillment_charts import chart_queries,chart_response
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha


class Command(BaseCommand):
    help=__doc__
    def add_arguments(self,parser): parser.add_argument('--evidence',type=Path,required=True)
    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Preserve earlier receipt; choose a new directory')
        target.mkdir(parents=True)
        context=publication(); before=run_identity(context.run)
        root=Path(__file__).resolve().parents[4]
        sources={name:file_sha(root/name) for name in ('mta/presentation/fulfillment_charts.py',
            'mta/presentation/fulfillment_storage.py','mta/presentation/context.py')}
        result=dict(status='FAILED',run=before,sources=sources,boundary='UNSCOPED_FULFILLMENT_CHARTS',
                    business_date=context.business_date.isoformat())
        try:
            reports=read_fulfillment(context.run,output=context.output)
            queries=chart_queries(context.output,reports,products=None,locations=None)
            values=dict(queries=queries,response=chart_response(queries))
            path=target/'charts.json.gz'
            with gzip.open(path,'wt') as stream: json.dump(values,stream)
            if before!=run_identity(context.run): raise CommandError('Accepted run changed during chart read')
            result.update(status='READBACK_EXPORTED_COMPARISON_REQUIRED',file=path.name,sha256=file_sha(path),
                row_counts={k:len(v) for k,v in queries.items()},run_unchanged=True)
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(rows=result['row_counts'],receipt_sha256=file_sha(target/'receipt.json'))))
