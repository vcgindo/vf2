"""Export native history/DBM consumers from the immutable selected publication."""
import gzip,json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.presentation.context import publication
from mta.presentation import history_native
from mta.presentation.dbm import dbm_rows
from mta.presentation.insight_response import scalar_json_rows
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha


class Command(BaseCommand):
    help=__doc__
    def add_arguments(self,parser): parser.add_argument('--evidence',type=Path,required=True)
    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Preserve evidence; choose new directory')
        target.mkdir(parents=True); context=publication(); before=run_identity(context.run)
        result=dict(status='FAILED',run=before,boundary='UNSCOPED_NATIVE_HISTORY_DBM')
        try:
            root=Path(__file__).resolve().parents[4]
            names=('mta/presentation/history_native.py','mta/presentation/dbm.py','mta/presentation/context.py',
                'mta/presentation/insight_response.py','mta/runtime/management/commands/export_history_consumers.py')
            sources={n:file_sha(root/n) for n in names}; state=context.output['BTRFinal'][0]
            master=context.output['BPRReports'][0]['vf_RationedReqReport']
            selected=[dict(SKUCode=r['SKUCode'],WhCode=r['WhCode']) for r in master]
            values=dict(master=[{f:r[f] for f in ('SKUCode','WhCode','ParentWhCode')} for r in master],
                selected=selected,graphs={})
            for name in ('tech','eco'):
                for days in (12,90):
                    values['graphs'][f'{name}/{days}']=history_native.buffer_graph(state,name,days,products=None,locations=None)
            values['availability']=history_native.historical_availability(state,products=None,locations=None)
            values['research']=history_native.research_rows(state,master,selected,products=None,locations=None)
            rows=dbm_rows(context.dbm)
            values['dbm']=dict(count=str(len(rows)),grid=scalar_json_rows([{k:v for k,v in r.items() if v is not None} for r in rows]))
            path=target/'history.json.gz'
            with gzip.open(path,'wt') as stream: json.dump(values,stream)
            if before!=run_identity(context.run): raise CommandError('Accepted run identity changed')
            if any(file_sha(root/n)!=sha for n,sha in sources.items()): raise CommandError('Export source changed')
            result.update(status='READBACK_EXPORTED_COMPARISON_REQUIRED',sources=sources,file=path.name,sha256=file_sha(path),
                research_rows=len(values['research'] or []),dbm_count=len(rows),run_unchanged=True,engine_replays=0,serving_changes=False)
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally: (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(research_rows=result['research_rows'],dbm_count=len(rows),receipt_sha256=file_sha(target/'receipt.json'))))
