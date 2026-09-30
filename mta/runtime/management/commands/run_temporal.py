"""Execute retained external daily facts using only this engine's persisted state."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import time

from django.core.management.base import BaseCommand, CommandError
from mta.runtime.temporal import execute_day, record_command
from mta.runtime.services import read_outputs
from mta.serialization import digest


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('input',type=Path)
        parser.add_argument('--sha256',required=True)
        parser.add_argument('--revision',required=True)
        parser.add_argument('--evidence',type=Path,required=True)
        parser.add_argument('--through',type=int)
        parser.add_argument('--exceptions',type=Path)

    def handle(self,*args,**options):
        target=options['evidence'];target.mkdir(parents=True,exist_ok=False)
        source_root=Path(__file__).resolve().parents[4]
        source_files={str(p.relative_to(source_root)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((source_root/'mta').rglob('*.py'))}
        (target/'source.json').write_text(json.dumps(dict(execution_revision=options['revision'],
            files=source_files),indent=2),encoding='utf-8')
        raw=options['input'].read_bytes()
        if hashlib.sha256(raw).hexdigest()!=options['sha256']:
            raise CommandError('Registered external artifact hash differs')
        artifact=json.loads(raw);case=artifact['case']
        through=options['through'] if options['through'] is not None else len(case['days'])-1
        if not 0<=through<len(case['days']):raise CommandError('Day index outside retained artifact')
        exceptions=json.loads(options['exceptions'].read_text()) if options['exceptions'] else {}
        previous=None;receipts=[]
        for index in range(through+1):
            started=time.monotonic()
            day={**deepcopy(case['days'][index]),**deepcopy(case['static_day'])}
            receipt=dict(day_index=index,date=day['business_date'],status='RUNNING',input_sha256=options['sha256'])
            try:
                run=execute_day(day=day,profile=case['profile'],execution_revision=options['revision'],
                    predecessor=previous,opening=None if previous else dict(state=case['opening'],
                        opening_date=case['opening_date'],identity=case['case']+'-'+options['sha256']),
                    report_exceptions=exceptions)
                output=read_outputs(run)
                with gzip.open(target/f'day-{index:03d}.json.gz','wt',encoding='utf-8',compresslevel=1) as stream:
                    json.dump(output,stream,sort_keys=True,separators=(',',':'))
                receipt.update(status='COMPUTED_NOT_YET_PARITY',run_id=str(run.pk),
                    predecessor_id=str(run.predecessor_id) if run.predecessor_id else None,
                    input_digest=run.input_digest,output_digest=run.output_digest,
                    closing_digest=digest(output['ClosingState']),
                    boundaries=[r['boundary'] for r in output['MajorBoundaries']],
                    suggestions=len(output['DBMFinal'][0]['Suggestions']),commands=[])
                for position,command in enumerate(case['commands']):
                    if command['after_day']!=index:continue
                    event=record_command(run,operation=command['operation'],selected=command['selected'],
                        timestamp=command['timestamp'],actor='retained-synthetic-trial',
                        idempotency_key='retained-command-'+str(position))
                    receipt['commands'].append(dict(id=event.pk,command=command,digest=event.digest,
                                                     before=event.before_digest,after=event.after_digest))
                previous=run
            except Exception as error:
                receipt.update(status='FAILED',error_type=type(error).__name__,error=str(error))
                raise
            finally:
                receipt['seconds']=round(time.monotonic()-started,3)
                receipts.append(receipt)
                (target/'execution.json').write_text(json.dumps(dict(
                    artifact_sha256=options['sha256'],revision=options['revision'],
                    requested_days=through+1,artifact_days=len(case['days']),
                    report_exceptions=exceptions,days=receipts),indent=2),encoding='utf-8')
                self.stdout.write(json.dumps(receipt));self.stdout.flush()
