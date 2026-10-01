"""Export existing native insight consumers for independent retained SQL proof."""
from datetime import timedelta
import gzip
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.presentation import insights
from mta.presentation.insight_response import scalar_json_rows,chronic_grid_payload
from mta.presentation.context import publication
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha


class Command(BaseCommand):
    help=__doc__
    def add_arguments(self,parser): parser.add_argument('--evidence',type=Path,required=True)
    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Preserve evidence; choose a new directory')
        target.mkdir(parents=True); context=publication(); before=run_identity(context.run)
        result=dict(status='FAILED',run=before,boundary='UNSCOPED_TERMINAL_INSIGHTS')
        try:
            root=Path(__file__).resolve().parents[4]
            names=('mta/presentation/insights.py','mta/presentation/insight_response.py','mta/presentation/context.py',
                'mta/runtime/management/commands/export_insight_consumer.py')
            sources={n:file_sha(root/n) for n in names}; output=context.output; state=output['BTRFinal'][0]
            values={kind:insights.project(insights.joined_rows(state,output['DBMFinal'][0],kind),kind)
                for kind in ('loc','sku','pie','ageing','chronic-loc','chronic-sku')}
            values['chronic-grid']=chronic_grid_payload(insights.chronic_grid(state,
                output['ClosingState'][0]['consumer_context']['NMSAllItems']))
            rows=insights.availability_rows(state)
            for horizon in (12,90):
                cutoff=(context.business_date-timedelta(days=horizon)).isoformat()
                selected=[r for r in rows if r['ReportDate']>cutoff]
                values[f'availability-trend/{horizon}']=insights.availability_trend(selected)
                for age in (1,4):
                    values[f'availability-ageing/{horizon}/{age}']=insights.availability_ageing(selected,state['BTRSnapshotForUI'],age)
            values={k:scalar_json_rows(v) for k,v in values.items()}
            path=target/'insights.json.gz'
            with gzip.open(path,'wt') as stream: json.dump(values,stream)
            if before!=run_identity(context.run): raise CommandError('Accepted run identity changed')
            if any(file_sha(root/n)!=sha for n,sha in sources.items()): raise CommandError('Export source changed')
            result.update(status='READBACK_EXPORTED_COMPARISON_REQUIRED',sources=sources,file=path.name,sha256=file_sha(path),
                populations={k:None if v is None else len(v) for k,v in values.items()},run_unchanged=True,engine_replays=0,serving_changes=False)
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(populations=result['populations'],receipt_sha256=file_sha(target/'receipt.json'))))
