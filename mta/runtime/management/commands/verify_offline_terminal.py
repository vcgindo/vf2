"""Verify every committed accepted day before any offline terminal publication."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.runtime.offline_scenario import registry, admit, require_run
from mta.runtime.temporal_continuation import validate_accepted_prefix, validate_source_transition
from mta.presentation.daily_sources import receipt, image_rows
from mta.presentation.offline_rrr import read


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--execution',type=Path,required=True)
        parser.add_argument('--input',type=Path,required=True)
        parser.add_argument('--scenario',choices=['trial','full'],required=True)
        parser.add_argument('--owner',required=True)

    def handle(self,*args,**options):
        item=registry()['scenarios'][options['scenario']]
        artifact=admit(options['input'].read_bytes(),item['sha256'])
        folder=options['execution'].resolve()
        execution=json.loads((folder/'execution.json').read_text())
        if (execution['artifact_sha256']!=item['sha256']
                or len(execution['days'])!=item['execution_through']+1):
            raise CommandError('Complete registered terminal prefix required; partial selection denied')
        source=json.loads((folder/'source.json').read_text())
        import hashlib
        root=Path(__file__).resolve().parents[4]
        current={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in source['files']}
        validate_source_transition(source,current)
        terminal=validate_accepted_prefix(folder,execution,artifact['case'])
        from mta.runtime.models import CalculationRun
        days=[]
        for entry in execution['days']:
            run=CalculationRun.objects.get(pk=entry['run_id'])
            binding=require_run(run)
            if binding['offline_owner']!=options['owner']:
                raise CommandError('Terminal prefix belongs to another offline owner')
            source=receipt(run)
            for path in source.images:
                image_rows(run,path)
            colour=read(run)
            days.append(dict(run_id=str(run.pk),source_digest=source.images_digest,
                             rrr_rows=len(colour),date=str(run.business_date)))
        self.stdout.write(json.dumps(dict(status='PASS',run_id=str(terminal.pk),
            output_digest=terminal.output_digest,business_date=str(terminal.business_date),
            accepted_days=len(days),daily_sources=days)))
