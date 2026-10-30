"""Upgrade only operator selection custody for an already published native ZIP.

The original complete archive audit is mandatory. No input, calculation,
publication, producer receipt or business journal is created or rewritten.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--selection-file', required=True)
        parser.add_argument('--output-file', help='Stage the upgraded operator bundle without changing serving selection')

    def handle(self, *args, **options):
        from mta.application.native_input_archive import audited_receipt
        from mta.presentation import native_selection as selection, native_publication
        from mta.presentation.accepted_publication import _qualified_ownership, _summary_ready
        from mta.presentation.context import configured_run
        from mta.presentation.daily_publication import require_ready
        native_publication.require_mode()
        # The database is evidence input throughout this maintenance operation.
        with connection.cursor() as cursor:
            cursor.execute('SET default_transaction_read_only=on')
        path = Path(options['selection_file'])
        before = path.read_bytes()
        previous = selection.read(path)
        run = configured_run()
        selection.require_selected(run)
        if previous['run_id'] != str(run.pk) or not _qualified_ownership(run):
            raise CommandError('Exact selected run and qualified immutable ownership required')
        receipt = audited_receipt(run)
        bundle = selection.candidate(run, require_ready(run), _summary_ready(run),
            native_publication.identity(run), input_archive=receipt)
        if selection.base_digest(bundle) != selection.base_digest(previous):
            raise CommandError('Archive qualification changed the selected publication identity')
        if path.read_bytes() != before:
            raise CommandError('Operator selection changed during archive qualification')
        target = Path(options['output_file']) if options.get('output_file') else path
        if target == path:
            backup = path.with_name(path.name + '.pre-archive-' + previous['selection_digest'] + '.json')
            if backup.exists():
                if backup.read_bytes() != before:
                    raise CommandError('Preserved operator selection differs')
            else:
                with backup.open('xb') as stream:
                    stream.write(before)
        elif target.exists() and selection.read(target) != bundle:
            raise CommandError('Staged archive selection already exists with different identity')
        selection.write(target, bundle)
        self.stdout.write(json.dumps(dict(status='EXISTING_ARCHIVE_FULLY_AUDITED_SELECTION_ONLY',
            run_id=str(run.pk), selection_file=str(target), selection_digest=bundle['selection_digest'],
            base_selection_digest=selection.base_digest(bundle), archive=receipt,
            database_read_only=True, calculation_or_report_preparation=False), sort_keys=True))
