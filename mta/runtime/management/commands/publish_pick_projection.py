"""Materialize only accepted calculated Pick bands, without calculation/replay."""
import hashlib
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from mta.presentation.pick_storage import read_pick_bands, restore_pick_bands
from mta.runtime.models import CalculationRun
from mta.runtime.management.commands.verify_application_reads import run_identity
from mta.serialization import digest


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--run', required=True)
        parser.add_argument('--output-digest', required=True)
        parser.add_argument('--evidence', type=Path, required=True)

    def handle(self, *args, **options):
        target = options['evidence']
        if target.exists():
            raise CommandError('Preserve earlier receipts; choose a new evidence directory')
        target.mkdir(parents=True)
        root = Path(__file__).resolve().parents[4]
        sources = [root/name for name in ('mta/runtime/models.py','mta/runtime/services.py',
            'mta/runtime/migrations/0007_pick_consumer_projection.py','mta/presentation/pick_storage.py')]
        sources.append(Path(__file__))
        hashes = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        (target/'source.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
        run = CalculationRun.objects.get(pk=options['run'])
        before = run_identity(run)
        try:
            receipt = restore_pick_bands(run.pk, expected_output_digest=options['output_digest'])
            rows = read_pick_bands(run)
            after = run_identity(run)
            if before != after:
                raise CommandError('Read-model publication changed accepted run/action identity')
            again = restore_pick_bands(run.pk, expected_output_digest=options['output_digest'])
            if again.created_at != receipt.created_at:
                raise CommandError('Idempotent publication rewrote the receipt')
            if any(hashlib.sha256((root/p).read_bytes()).hexdigest()!=sha for p,sha in hashes.items()):
                raise CommandError('Read-model implementation changed during proof')
            result = dict(status='PICK_RELATIONAL_PROJECTION_PASS_NOT_API_PARITY', run=before,
                row_count=len(rows), rows_digest=digest(rows), calculation_digest=receipt.calculation_digest,
                provenance=receipt.provenance, accepted_run_unchanged=True, idempotent=True,
                calculations_executed=0, serving_changes=False,
                source_sha256=hashlib.sha256((target/'source.json').read_bytes()).hexdigest())
        except Exception as exc:
            result = dict(status='FAILED',run=before,error=dict(type=type(exc).__name__,message=str(exc)))
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            raise
        (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(status=result['status'],row_count=len(rows),
            receipt_sha256=hashlib.sha256((target/'receipt.json').read_bytes()).hexdigest())))
