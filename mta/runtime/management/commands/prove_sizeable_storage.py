"""Bounded F2 gate: one unchanged full-estate day, rollback then readback.

This is a storage proof, not legacy parity. The same day's eight boundaries
must subsequently pass the independent canonical comparator before resuming.
"""
import gzip
import json
import os
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from mta.runtime.models import CalculationRun, Checkpoint
from mta.runtime.services import read_outputs
from mta.runtime.temporal import BOUNDARIES, command_state
from mta.runtime.relational_state import CATALOG, table_sql, production_projection
from mta.serialization import digest, storage
from mta.temporal.actions import apply_command
from parity.output_archive import OutputArchive

SHA='0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546'


def state_row_count(run):
    tables=[table_sql(key) for key in CATALOG['tables']]+['mta_state.report_export_cell']
    query='SELECT SUM(n) FROM ('+' UNION ALL '.join('SELECT COUNT(*) AS n FROM '+table+' WHERE vf_run_id=%s' for table in tables)+') counts'
    with connection.cursor() as cursor:
        cursor.execute(query,[run.pk]*len(tables))
        return int(cursor.fetchone()[0])


def resources():
    worker=Path('/sys/fs/cgroup')
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_read_file('/sys/fs/cgroup/memory.max'),pg_read_file('/sys/fs/cgroup/memory.events')")
        pg_limit,pg_events=cursor.fetchone()
    result=dict(worker_limit=int((worker/'memory.max').read_text()),
        worker_peak=int((worker/'memory.peak').read_text()),postgres_limit=int(pg_limit),
        postgres_events=dict((k,int(v)) for k,v in (line.split() for line in pg_events.splitlines())))
    if result['worker_limit']>4*1024**3 or result['postgres_limit']>1024**3:
        raise CommandError('The bounded test memory contract was expanded')
    return result


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--input',type=Path,required=True)
        parser.add_argument('--exceptions',type=Path,required=True)
        parser.add_argument('--revision',required=True)
        parser.add_argument('--evidence',type=Path,required=True)

    def handle(self,*args,**options):
        target=options['evidence'];target.mkdir(parents=True,exist_ok=False)
        before=resources()
        revision=options['revision']
        if len(revision)>70:raise CommandError('Bounded revision required')
        common=dict(sha256=SHA,through=0,automatic_actions=True,exceptions=options['exceptions'])
        original=Checkpoint.objects.create
        def fail_after_trace(**fields):
            if fields['name']=='DBMStages':raise RuntimeError('F2 injected mid-write rollback proof')
            return original(**fields)
        with patch('mta.runtime.services.Checkpoint.objects.create',side_effect=fail_after_trace):
            try:
                call_command('run_temporal',str(options['input']),revision=revision+'-rollback',
                             evidence=target/'rollback',**common)
            except RuntimeError as error:
                if str(error)!='F2 injected mid-write rollback proof':raise
            else:raise CommandError('Injected mid-write failure was not reached')
        failed=CalculationRun.objects.get(execution_revision=revision+'-rollback')
        rolled_back=dict(run_id=str(failed.pk),status=failed.status,state_rows=state_row_count(failed),
            checkpoints=failed.checkpoints.count(),commands=failed.commands.count(),output_digest=failed.output_digest)
        if failed.status!='FAILED' or any(rolled_back[k] for k in ('state_rows','checkpoints','commands','output_digest')):
            raise CommandError('Atomic rollback failed')
        if not list((Path(os.environ['VF_EVIDENCE_ROOT'])/str(failed.pk)).glob('*.jsonl.gz')):
            raise CommandError('Failed evidence was not retained')
        (target/'rollback-proof.json').write_text(json.dumps(rolled_back,indent=2),encoding='utf-8')
        self.stdout.write('Full-estate mid-write rollback PASS; proceeding to the same unchanged day.')
        call_command('run_temporal',str(options['input']),revision=revision,
                     evidence=target/'day-one',**common)
        receipt=json.loads((target/'day-one/execution.json').read_text())['days'][0]
        run=CalculationRun.objects.get(pk=receipt['run_id'])
        actual=read_outputs(run)
        archive=OutputArchive(target/'day-one'/receipt['output_archive'])
        expected={name:archive[name] for name in ('ClosingState','Reports','BPRFinal','Lineage','PublicationContext')}
        if digest(actual)!=digest(production_projection(expected)):
            raise CommandError('Operational projections do not exactly round-trip')
        if len(actual['ClosingState'][0]['dbm']['DBMMaster'])!=1240:
            raise CommandError('Full retained SKU-location population differs')
        next_dbm,events=command_state(run,actual['ClosingState'][0]['dbm'])
        expected_dbm=expected['ClosingState'][0]['dbm']
        for command in receipt['commands']:
            value=command['command']
            expected_dbm=storage(apply_command(expected_dbm,value['operation'],
                [tuple(k) for k in value['selected']],value['timestamp']))
        if digest(next_dbm)!=digest(expected_dbm):raise CommandError('Next opening differs from committed action effects')
        boundaries=[r['boundary'] for r in archive.iter_rows('MajorBoundaries')]
        if boundaries!=list(BOUNDARIES):raise CommandError('Eight-boundary evidence roster differs')
        if run.checkpoints.exclude(rows=[]).exists():raise CommandError('Daily trace data remains in PostgreSQL JSON')
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='mta_state' AND data_type IN ('json','jsonb','bytea')")
            if cursor.fetchone()[0]:raise CommandError('Operational state uses a JSON/blob column')
        result=dict(status='STORAGE_GATE_PASS_NOT_YET_LEGACY_PARITY',input_sha256=SHA,
            rollback=rolled_back,run_id=str(run.pk),pairs=1240,production_rows=state_row_count(run),
            manifest_bytes=len(json.dumps(run.production_manifest)),closing_digest=digest(actual['ClosingState']),
            next_dbm_digest=digest(next_dbm),committed_actions=len(events),boundaries=boundaries,
            production_digest=run.production_digest,complete_output_digest=run.output_digest)
        after=resources()
        if after['postgres_events']['oom_kill']!=before['postgres_events']['oom_kill']:
            raise CommandError('PostgreSQL had an OOM during the storage proof')
        result.update(resources_before=before,resources_after=after)
        (target/'storage-proof.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(result))
