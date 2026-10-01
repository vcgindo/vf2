"""Read-only export of the persisted fields required by the Pick/RRR consumer."""
import hashlib
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from mta.presentation.context import publication
from mta.presentation.pick_storage import read_pick_bands
from mta.presentation.rrr import pick_rows, selected_rows
from mta.presentation.rrr_types import selected_rrr_response
from mta.runtime.management.commands.verify_application_reads import run_identity
from mta.serialization import storage
from parity.output_archive import write_rows


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--evidence', type=Path, required=True)
        parser.add_argument('--rrr-read-model', action='store_true',
                            help='Export the unscoped deployed-shaped RRR projection; not an authorization proof')

    def handle(self, *args, **options):
        target = options['evidence']
        if target.exists():
            raise CommandError('Preserve earlier receipt; choose a new directory')
        target.mkdir(parents=True)
        context = publication()
        before = run_identity(context.run)
        bands = read_pick_bands(context.run)
        rows = (storage([selected_rrr_response(row) for row in selected_rows(context.output,bands)])
                if options['rrr_read_model'] else
                storage(pick_rows(context.output['BPRReports'][0]['vf_RationedReqReport'],bands)))
        if run_identity(context.run) != before:
            raise CommandError('Accepted source changed during read')
        root = Path(__file__).resolve().parents[4]
        sources = {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in (
            'mta/presentation/rrr.py','mta/presentation/rrr_types.py',
            'mta/presentation/pick_storage.py','mta/presentation/context.py')}
        receipt = dict(status='READBACK_EXPORTED_COMPARISON_REQUIRED',run=before,
            business_date=context.business_date.isoformat(), sources=sources,
            boundary='UNSCOPED_RRR_READ_MODEL' if options['rrr_read_model'] else 'NATIVE_PICK',
            file='pick-rows.jsonl.gz', **write_rows(target/'pick-rows.jsonl.gz',rows))
        (target/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(rows=len(rows),fields=len(rows[0]) if rows else 0,
            receipt_sha256=hashlib.sha256((target/'receipt.json').read_bytes()).hexdigest())))
