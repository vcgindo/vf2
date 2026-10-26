"""Fence an inspected bounded PostDBM worker before explicit recovery."""
import json
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('attempt_id')
        parser.add_argument('--expected-worker-token', required=True)
        parser.add_argument('--reason', required=True)

    def handle(self, *args, **options):
        from mta.presentation.native_mode import require_configuration
        from mta.runtime.production_post_dbm import fence
        require_configuration()
        try:
            attempt = fence(options['attempt_id'], expected_worker_token=options['expected_worker_token'],
                            reason=options['reason'])
            self.stdout.write(json.dumps(dict(attempt_id=str(attempt.pk), run_id=str(attempt.run_id),
                status=attempt.status, scope_ready=False, serving_selected=False), sort_keys=True))
        except Exception as error:
            raise CommandError(str(error)) from error
