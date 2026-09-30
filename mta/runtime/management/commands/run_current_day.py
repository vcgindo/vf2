"""Execute one retained source-fact artifact and verify its durable readback."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.runtime.services import execute_current_day, read_outputs, digest


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('input', type=Path)
        parser.add_argument('--revision', required=True)
        parser.add_argument('--evidence', type=Path, required=True)

    def handle(self, *args, **options):
        target = options['evidence']
        if target.exists():
            raise CommandError('Evidence directory already exists; preserve prior receipts')
        artifact = json.loads(options['input'].read_text(encoding='utf-8'))
        payload = artifact.get('engine_input', artifact)
        run = execute_current_day(payload, execution_revision=options['revision'])
        outputs = read_outputs(run)
        target.mkdir(parents=True, exist_ok=False)
        receipt = dict(run_id=str(run.pk), business_date=run.business_date.isoformat(),
                       execution_revision=run.execution_revision, artifact_digest=digest(artifact),
                       input_digest=run.input_digest, output_digest=run.output_digest,
                       output_roster=run.output_roster,
                       populations={name: len(rows) for name, rows in outputs.items()},
                       parity='NOT_ASSERTED_BY_PERSISTENCE_COMMAND')
        (target / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        (target / 'outputs.json').write_text(json.dumps(outputs, indent=2, sort_keys=True), encoding='utf-8')
        self.stdout.write(json.dumps(receipt))
