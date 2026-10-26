"""Coordinate CSV facts with the existing native day and presentation services."""
import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('operation', choices=('inspect', 'stage', 'execute', 'select', 'acknowledge', 'status', 'schema'))
        parser.add_argument('--binding', default=os.environ.get('VF_DAILY_BINDING_FILE', '/onboarding/binding.json'))
        parser.add_argument('--date')
        parser.add_argument('--input-directory')
        parser.add_argument('--input-root', default='/incoming')
        parser.add_argument('--work-root', default='/var/lib/vectorflow/daily')
        parser.add_argument('--pick-root', default='/var/lib/vectorflow/pick')
        parser.add_argument('--selection-file', default='/var/lib/vectorflow/selection.json')
        parser.add_argument('--attempt')
        parser.add_argument('--proof')
        parser.add_argument('--resume', action='store_true')
        parser.add_argument('--fullkit-configuration',type=Path)
        parser.add_argument('--fullkit-sha256')

    def handle(self, *args, **options):
        from mta.runtime import daily_feed as service
        try:
            operation = options['operation']
            fullkit=None
            if options['fullkit_configuration'] is not None or options['fullkit_sha256'] is not None:
                if operation!='stage' or options['fullkit_configuration'] is None or options['fullkit_sha256'] is None:
                    raise ValueError('Fullkit configuration and SHA256 apply together only to staging')
                from mta.runtime.management.commands.register_runtime_report_configuration import read_reference
                fullkit=read_reference(options['fullkit_configuration'],options['fullkit_sha256'])
            if operation == 'schema':
                from mta.application.production_csv_contract import describe
                from mta.application.production_csv_files import load_binding
                value = describe(load_binding(options['binding'])['intake_schema'])
            elif operation in ('stage', 'inspect'):
                if not options['date'] or not options['input_directory']:
                    raise ValueError('Explicit business date and completed input directory required')
                params = dict(input_root=options['input_root'], pick_root=options['pick_root'])
                if operation == 'stage':
                    params['work_root'] = options['work_root']
                    if fullkit is not None:params['fullkit']=fullkit
                value = getattr(service, operation)(options['binding'], options['input_directory'], options['date'], **params)
            elif operation == 'execute':
                value = service.execute(options['attempt'], options['binding'],
                    pick_root=options['pick_root'], resume=options['resume'])
            elif operation == 'select':
                value = service.select(options['attempt'], options['binding'], options['selection_file'])
            elif operation == 'acknowledge':
                value = service.acknowledge(options['attempt'], options['binding'], options['selection_file'], json.loads(options['proof']))
            else:
                binding, _ = service.binding_owner(options['binding'])
                value = service.result(service._bound_attempt(options['attempt'], binding))
            self.stdout.write(json.dumps(value, sort_keys=True))
        except Exception as error:
            raise CommandError(str(error)) from error
