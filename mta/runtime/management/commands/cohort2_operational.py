"""Materialize/check/recover the isolated Cohort2 operational boundary."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.runtime.operational_models import OperationalAttempt
from mta.runtime.operational_attempts import verify_attempt, operational_worker
from mta.runtime.operational_runner import materialize, validate_configuration


class Command(BaseCommand):
    help = 'Cohort2 only: materialize, check, retry an interrupted/failed attempt, or repair declared missing files.'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=('materialize', 'check', 'recover'))
        parser.add_argument('--request', help='Path to an explicit JSON request; no default owners or roots')
        parser.add_argument('--attempt', type=str)

    def handle(self, *args, **options):
        try:
            if options['action'] == 'check':
                if not options['attempt'] or options['request']:
                    raise ValueError('check requires only --attempt')
                owner = OperationalAttempt.objects.select_related('configuration').get(pk=options['attempt'])
                if owner.status != 'SUCCEEDED':
                    raise ValueError('check requires a completed operational attempt')
                verify_attempt(owner)
            else:
                if not options['request'] or options['attempt']:
                    raise ValueError('materialize/recover requires only --request')
                request = json.loads(Path(options['request']).read_text(encoding='utf-8'))
                required = {'run_id', 'configuration_id', 'request_key', 'owned_root', 'expected_output_digest'}
                optional = {'predecessor_id', 'retry_of_id', 'interrupted_attempt_id', 'repair_of_id',
                            'repair_file_ids', 'openings', 'abort_opening'}
                if not isinstance(request, dict) or not required <= set(request) or set(request)-required-optional:
                    raise ValueError('Explicit supported request fields required')
                if options['action'] == 'materialize' and any(request.get(name) for name in
                        ('retry_of_id', 'interrupted_attempt_id', 'repair_of_id', 'repair_file_ids')):
                    raise ValueError('Recovery lineage requires recover')
                if options['action'] == 'recover' and not (request.get('retry_of_id') or request.get('repair_of_id')):
                    raise ValueError('recover requires explicit failed/interrupted or missing-file lineage')
                if request.get('repair_of_id'):
                    if 'openings' in request or 'abort_opening' in request:
                        raise ValueError('Repair uses its preserved original sources')
                    from functools import partial
                    from mta.application.operational_io import archive_files
                    from mta.runtime.operational_repair import materialize_repair
                    with operational_worker(**request) as owner:
                        if owner.status != 'SUCCEEDED':
                            config = validate_configuration(owner.configuration)
                            tool = config['bindings']['zip_tool']
                            materialize_repair(owner.pk, archive_writer=partial(archive_files,
                                executable=tool['path'], tool_sha256=tool['sha256']))
                    owner.refresh_from_db()
                else:
                    owner = materialize(**request)
            self.stdout.write(json.dumps(dict(attempt=str(owner.pk), status=owner.status,
                run=str(owner.run_id), root=owner.root)))
        except Exception as error:
            raise CommandError(type(error).__name__+': '+str(error)) from error
