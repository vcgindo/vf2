"""Export existing native BTR consumers; no publication or engine mutation."""
import gzip
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.presentation import btr
from mta.presentation.context import publication
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha

FIELDS=('SKUCode','WhCode','ParentWhCode','Norm','VirtualNorm')
CASES=(('full',1,5000,1,90),('recent',1,5000,79,90),('page2',2,7,79,90))


class Command(BaseCommand):
    help=__doc__
    def add_arguments(self,parser): parser.add_argument('--evidence',type=Path,required=True)
    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Preserve evidence; choose a new directory')
        target.mkdir(parents=True); context=publication(); before=run_identity(context.run)
        result=dict(status='FAILED',run=before,boundary='UNSCOPED_TERMINAL_BTR')
        try:
            root=Path(__file__).resolve().parents[4]
            names=('mta/presentation/btr.py','mta/presentation/context.py',
                   'mta/runtime/management/commands/export_btr_consumer.py')
            sources={n:file_sha(root/n) for n in names}
            values=dict(requirements=[{f:r[f] for f in FIELDS} for r in
                context.output['BPRReports'][0]['vf_RationedReqReport']],counts={},cases={})
            joined={name:btr.joined_rows(context.output,name) for name in ('tech','eco')}
            values['counts']={name:str(len(rows)) for name,rows in joined.items()}
            for case,page,size,start,end in CASES:
                columns=tuple(f'D{i}' for i in range(start,end+1))
                values['cases'][case]=dict(page=page,size=size,start=start,end=end,
                    labels=[{c:r[c] for c in columns} for r in context.output['BTRFinal'][0]['BufferTrendDates']],
                    **{name:btr.project_rows(context.output,name,rows[(page-1)*size:page*size],columns,size)
                       for name,rows in joined.items()})
            path=target/'btr.json.gz'
            with gzip.open(path,'wt') as stream: json.dump(values,stream)
            if before!=run_identity(context.run): raise CommandError('Accepted run identity changed')
            if any(file_sha(root/n)!=sha for n,sha in sources.items()): raise CommandError('Export source changed')
            result.update(status='READBACK_EXPORTED_COMPARISON_REQUIRED',sources=sources,file=path.name,
                sha256=file_sha(path),counts=values['counts'],run_unchanged=True,engine_replays=0,serving_changes=False)
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(counts=values['counts'],receipt_sha256=file_sha(target/'receipt.json'))))
