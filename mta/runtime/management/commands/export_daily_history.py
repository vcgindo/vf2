"""Export complete daily-history graph inputs/results from native publication."""
from collections import defaultdict
import gzip
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from mta.presentation.context import publication
from mta.presentation.dbm import key
from mta.presentation.daily_history import daily_graph
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.output_archive import file_sha

TABLES=('DBMMaster','DailyConsumption','SuspendHistory','NormChangeLogTbl',
        'SuspendStockType','SuspendConsumptionType','SuggestionsLog')


class Command(BaseCommand):
    help=__doc__
    def add_arguments(self,parser): parser.add_argument('--evidence',type=Path,required=True)
    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Preserve evidence; choose new directory')
        target.mkdir(parents=True); context=publication(); before=run_identity(context.run)
        result=dict(status='FAILED',run=before,boundary='UNSCOPED_ALL_TERMINAL_DAILY_HISTORY')
        try:
            root=Path(__file__).resolve().parents[4]
            names=('mta/presentation/dbm.py','mta/presentation/daily_history.py','mta/presentation/context.py',
                   'mta/runtime/management/commands/export_daily_history.py')
            sources={n:file_sha(root/n) for n in names}
            # Validation export groups the exact committed rows once to avoid
            # scanning unrelated entities for every graph. No values change.
            grouped={}
            for table in TABLES:
                grouped[table]=defaultdict(list)
                for row in context.dbm[table]: grouped[table][key(row)].append(row)
            pairs=sorted(grouped['DBMMaster'])
            if len(pairs)!=1240: raise CommandError('Selected full-estate master identity changed')
            values=[]
            for pair in pairs:
                state={n:grouped[n][pair] for n in TABLES}
                state.update(LastBatchRunTbl=context.dbm['LastBatchRunTbl'],ReasonCodes=context.dbm['ReasonCodes'])
                graph=daily_graph(state,*pair)
                values.append(dict(SKUCode=pair[0],WhCode=pair[1],graph=graph))
            path=target/'daily-history.json.gz'
            with gzip.open(path,'wt') as stream: json.dump(values,stream)
            if before!=run_identity(context.run): raise CommandError('Accepted identity changed')
            if any(file_sha(root/n)!=s for n,s in sources.items()): raise CommandError('Source changed during export')
            counts={n:sum(len(v['graph'][0][n] or []) for v in values) for n in (
                'StockData','NormData','MasterData','MonitoringData','NormChangeHistoryData','SuggestionHistoryData')}
            result.update(status='READBACK_EXPORTED_COMPARISON_REQUIRED',pairs=len(pairs),rows=counts,
                file=path.name,sha256=file_sha(path),sources=sources,run_unchanged=True,serving_changes=False,engine_replays=0)
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(pairs=len(pairs),rows=counts,receipt_sha256=file_sha(target/'receipt.json'))))
