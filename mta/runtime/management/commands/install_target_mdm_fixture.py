"""Explicit approved 3005 fixture-only MDM owner installation."""
import hashlib
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.mdm.target_fixture import install
from mta.serialization import digest


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--input', required=True)
        parser.add_argument('--sha256', required=True)

    def handle(self, *args, **options):
        raw = Path(options['input']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != options['sha256']:
            raise CommandError('Target input file SHA256 differs')
        package = json.loads(raw)
        result = install(package, digest(package))
        self.stdout.write(json.dumps(dict(status='INSTALLED_CONSUMER_FIXTURE',
            source_id=result.source_id, digest=result.digest, run_id=str(result.run_id),
            daily_acceptance=False)))
