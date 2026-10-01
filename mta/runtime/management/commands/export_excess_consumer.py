"""Export exact current-day Excess read models; no authorization acceptance."""
import gzip
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.presentation.context import publication
from mta.presentation.excess_storage import read_excess
from mta.presentation.excess_views import joined_rows,chart_queries,chart_response
from mta.presentation.excess_grid import excess_grid_rows,excess_grid_config
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha


class Command(BaseCommand):
    help=__doc__

    def add_arguments(self,parser):
        parser.add_argument('--evidence',type=Path,required=True)

    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists():
            raise CommandError('Preserve earlier evidence; choose a new directory')
        target.mkdir(parents=True)
        context=publication()
        before=run_identity(context.run)
        root=Path(__file__).resolve().parents[4]
        sources={p.relative_to(root).as_posix():file_sha(p) for p in sorted((root/'mta/presentation').glob('*.py'))}
        result=dict(status='FAILED',run=before,boundary='UNSCOPED_EXCESS_READ_MODEL',
                    business_date=context.business_date.isoformat(),sources=sources)
        try:
            rows=read_excess(context.run,output=context.output)
            grid=excess_grid_rows(joined_rows(context.output,rows,context.business_date))
            values=dict(grid=grid,count=len(grid),uiConfig=excess_grid_config(),
                queries=chart_queries(context.output,rows,context.business_date,products=None,locations=None),
                response=chart_response(context.output,rows,context.business_date,products=None,locations=None))
            path=target/'read-model.json.gz'
            with gzip.open(path,'wt',encoding='utf-8') as stream:
                json.dump(values,stream,ensure_ascii=False)
            if before!=run_identity(context.run) or any(file_sha(root/p)!=sha for p,sha in sources.items()):
                raise CommandError('Read mutated accepted identity or source changed')
            result.update(status='READBACK_EXPORTED_COMPARISON_REQUIRED',file=path.name,sha256=file_sha(path),
                qualification='Unscoped full-population read model, NOT authenticated authorization or filter acceptance')
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc))
            raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(grid=len(grid),charts={k:len(v) for k,v in values['queries'].items()},
                                         receipt_sha256=file_sha(target/'receipt.json'))))
