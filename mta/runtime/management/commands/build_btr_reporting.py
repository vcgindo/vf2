"""Build/reuse BTR references after the configured publication passes admission."""
import json
import time
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.presentation.btr_reporting import build_selected


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--evidence', required=True, type=Path)

    def handle(self, *args, **options):
        path = options['evidence']
        if path.exists():
            raise CommandError('Preserve prior evidence; choose a new path')
        path.parent.mkdir(parents=True, exist_ok=True)
        result = dict(status='FAILED')
        started = time.monotonic()
        try:
            generation = build_selected()
            result.update(status='READY_NOT_SELECTED', generation=str(generation.pk),
                run=str(generation.run_id), source_digest=generation.source_digest,
                rows_digest=generation.rows_digest, rows=generation.row_count,
                eligible=generation.eligible, qualification=generation.qualification,
                business_date=str(generation.business_date))
        except BaseException as exc:
            result['error'] = type(exc).__name__ + ': ' + str(exc)
            raise
        finally:
            result['seconds'] = time.monotonic() - started
            with path.open('x', encoding='utf-8') as stream:
                json.dump(result, stream, indent=2)
        self.stdout.write(json.dumps(result))
