"""Compare PostgreSQL readback to the Fresh SQL receipts, never seed results."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError

from mta.runtime.services import execute_current_day, read_outputs, digest
from parity.current_day import compare
from parity.verify_raw import options


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('receipts', type=Path)
        parser.add_argument('fixtures', nargs='+')
        parser.add_argument('--revision', required=True)
        parser.add_argument('--evidence', required=True, type=Path)

    def handle(self, *args, **options_):
        target = options_['evidence']
        target.mkdir(parents=True, exist_ok=False)
        summary = []
        for fixture in options_['fixtures']:
            if Path(fixture).name != fixture:
                raise CommandError('Named receipt files only')
            oracle = json.loads((options_['receipts'] / fixture).read_text())
            if oracle['status'] != 'PASS' or digest(oracle['input']) != oracle['input_sha256']:
                raise CommandError('Source receipt not accepted or immutable input changed')
            payload = oracle['input']
            run = execute_current_day(payload, execution_revision=options_['revision'])
            output = read_outputs(run)
            contracts = compare(oracle['legacy']['checkpoints'], output, **options(payload))
            passed = set(contracts) == set(oracle['contracts']) and all(c['status']=='PASS' for c in contracts.values())
            receipt = dict(fixture=fixture, run_id=str(run.pk), input_digest=run.input_digest,
                           output_digest=run.output_digest, output=output, contracts=contracts,
                           status='PASS' if passed else 'FAIL', source_receipt_digest=digest(oracle))
            (target / fixture).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            result = dict(fixture=fixture, run_id=str(run.pk), status=receipt['status'], comparisons=len(contracts))
            summary.append(result)
            (target / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
            self.stdout.write(json.dumps(result))
            if not passed:
                raise CommandError('Earliest persisted comparison diverges: '+fixture)
