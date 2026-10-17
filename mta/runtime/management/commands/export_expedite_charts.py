"""Publish missing post-colour rows once, then export native Expedite charts."""
import gzip
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.presentation.context import publication
from mta.presentation.pick_post_storage import read_pick_post
from development.pick_post_storage import publish_existing
from mta.presentation.expedite_storage import read_expedite
from mta.presentation.expedite_charts import queries,response
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha


class Command(BaseCommand):
    help=__doc__
    def add_arguments(self,parser): parser.add_argument('--evidence',type=Path,required=True)
    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Preserve receipts; choose new directory')
        target.mkdir(parents=True); context=publication(); before=run_identity(context.run)
        result=dict(status='FAILED',run=before,boundary='UNSCOPED_EXPEDITE_CHARTS')
        try:
            first=publish_existing(context.run.pk,expected_output_digest=context.run.output_digest)
            second=publish_existing(context.run.pk,expected_output_digest=context.run.output_digest)
            if first.created_at!=second.created_at: raise CommandError('Post-report publication not idempotent')
            pick=read_pick_post(context.run,output=context.output); rows=read_expedite(context.run,output=context.output)
            values=dict(pick=pick,charts={})
            for kind in ('parent','child'):
                tables=queries(context.output,rows,pick,kind,products=None,locations=None)
                chart=dict(queries=tables)
                try:
                    chart['response']=response(tables,kind)
                except ValueError as exc:
                    if str(exc)!='Legacy Expedite receiving LogisticsLocation depends on unordered critical rows': raise
                    chart.update(response=None,source_flaw=str(exc),response_status='UNAVAILABLE_NOT_PARITY')
                values['charts'][kind]=chart
            path=target/'charts.json.gz'
            with gzip.open(path,'wt') as stream: json.dump(values,stream)
            if before!=run_identity(context.run): raise CommandError('Accepted run changed')
            root=Path(__file__).resolve().parents[4]
            result.update(status='READBACK_EXPORTED_COMPARISON_REQUIRED',file=path.name,sha256=file_sha(path),
                sources={n:file_sha(root/n) for n in ('mta/presentation/pick_post.py','mta/presentation/pick_post_storage.py',
                    'mta/presentation/expedite_charts.py','mta/presentation/expedite_storage.py','mta/presentation/context.py')},
                pick_rows=len(pick),row_counts={k:{n:len(r) for n,r in v['queries'].items()} for k,v in values['charts'].items()},
                run_unchanged=True,idempotent=True,serving_changes=False)
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(rows=result['row_counts'],receipt_sha256=file_sha(target/'receipt.json'))))
