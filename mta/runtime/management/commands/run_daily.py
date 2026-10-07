"""Execute exactly one declared day; never select a serving run or infer actions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from django.core.management.base import BaseCommand, CommandError
from mta.runtime.models import CalculationRun, MdmSource
from mta.runtime.temporal import execute_day


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('input', type=Path)
        parser.add_argument('--sha256', required=True)
        parser.add_argument('--day-index', type=int, required=True)
        parser.add_argument('--revision', required=True)
        parser.add_argument('--evidence-mode', choices=('production','validation'), default='production')
        parser.add_argument('--predecessor')
        parser.add_argument('--mdm-source', required=True)
        parser.add_argument('--mdm-source-digest', required=True)
        parser.add_argument('--bpr-remark-horizon', type=int, required=True)
        parser.add_argument('--exceptions', type=Path)

    def handle(self, *args, **options):
        raw=options['input'].read_bytes()
        if hashlib.sha256(raw).hexdigest()!=options['sha256']:
            raise CommandError('Frozen artifact identity differs')
        artifact=json.loads(raw);case=artifact['case'];index=options['day_index']
        if not 0<=index<len(case['days']):raise CommandError('Day index outside artifact')
        if bool(index)!=bool(options['predecessor']):
            raise CommandError('Only day zero uses an opening; every successor requires its predecessor')
        source=MdmSource.objects.get(pk=options['mdm_source'],digest=options['mdm_source_digest'])
        from mta.mdm.daily_source import require_binding
        require_binding(source,artifact_sha256=options['sha256'],artifact_schema=artifact.get('schema'))
        parent=CalculationRun.objects.get(pk=options['predecessor']) if index else None
        if parent and parent.business_date.isoformat()!=case['days'][index-1]['business_date']:
            raise CommandError('Predecessor date does not match the frozen preceding day')
        profile=deepcopy(case['profile']);profile['daily_publication']=True
        config=profile.setdefault('daily_publication_config',{})
        horizon=options['bpr_remark_horizon']
        if config.get('bpr_remark_horizon',horizon)!=horizon:
            raise CommandError('Pinned remark horizon differs')
        config['bpr_remark_horizon']=horizon
        day={**deepcopy(case['days'][index]),**deepcopy(case['static_day'])}
        exceptions=json.loads(options['exceptions'].read_text()) if options['exceptions'] else {}
        opening=None if parent else dict(state=case['opening'],opening_date=case['opening_date'],
            identity=case['case']+'-'+options['sha256']+'-daily')
        started=time.monotonic()
        run=execute_day(day=day,profile=profile,execution_revision=options['revision'],
            predecessor=parent,opening=opening,mdm_source=source,
            evidence_mode=options['evidence_mode'],report_exceptions=exceptions)
        self.stdout.write(json.dumps(dict(status=run.status,run_id=str(run.pk),
            business_date=run.business_date.isoformat(),input_digest=run.input_digest,
            output_digest=run.output_digest,validation_digest=run.validation_digest,
            evidence_mode=run.evidence_mode,seconds=round(time.monotonic()-started,3),
            publication='unselected; parity and preparation are separate')))
