"""Initialize supplied master/opening inputs; never extract, generate or calculate."""
import json
import hashlib
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.mdm.initialization import initialize, implementation_digest
from mta.mdm.initialization_contract import decode
from mta.runtime.production_preflight import initialization as inspect, PreflightError, require


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('input', type=Path)
        parser.add_argument('--sha256', required=True)
        parser.add_argument('--configuration-digest', required=True)
        parser.add_argument('--recipe-digest', required=True)
        parser.add_argument('--inspect', action='store_true')
        parser.add_argument('--csv', action='store_true', help='Read a complete CSV opening directory; --sha256 pins its opening-manifest.json')

    def handle(self, *args, **options):
        from mta.presentation.native_mode import require_configuration
        require_configuration()
        try:
            parameters = dict(expected_configuration=options['configuration_digest'],
                              expected_recipe=options['recipe_digest'])
            if options.get('csv'):
                from mta.application.initialization_csv import read
                raw = read(options['input'], options['sha256'], **parameters)
                input_sha256 = hashlib.sha256(raw).hexdigest()
            else:
                raw = options['input'].read_bytes()
                input_sha256 = options['sha256']
            if options['inspect']:
                report=inspect(raw,input_sha256,**parameters)
                report.update(implementation_digest=implementation_digest(),input_sha256=input_sha256,
                    status='INPUT_CONTRACT_VALIDATED_NOT_INSTALLED' if report['stage_eligibility']['installation'] else 'INPUT_REQUIREMENTS_INCOMPLETE')
                require(report,'installation')
                self.stdout.write(json.dumps(report,sort_keys=True))
                return
            owner, created = initialize(raw, input_sha256, **parameters)
            result = dict(status='INITIALIZED' if created else 'REVERIFIED',
                source_id=owner.source_id, source_digest=owner.source.digest,
                opening_id=str(owner.pk), opening_identity=owner.opening_identity,
                opening_date=owner.opening_date.isoformat(), input_sha256=owner.input_sha256,
                configuration_digest=owner.configuration_digest, recipe_digest=owner.recipe_sha256,
                implementation_digest=owner.implementation_digest, content_digest=owner.input_digest,
                accepted_day=False)
            if options.get('csv'):
                result['csv_manifest_sha256'] = options['sha256']
            self.stdout.write(json.dumps(result, sort_keys=True))
        except PreflightError as error:
            self.stdout.write(json.dumps(error.report,sort_keys=True))
            raise CommandError('Native '+error.stage+' preflight has blocking requirements') from error
        except Exception as error:
            raise CommandError(str(error)) from error
