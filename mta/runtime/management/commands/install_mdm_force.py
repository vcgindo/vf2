import hashlib
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from mta.mdm.force_source import install


class Command(BaseCommand):
    help = 'Install the approved registered master13 source in its owned private database'

    def add_arguments(self, parser):
        parser.add_argument('input', type=Path)
        parser.add_argument('--sha256', required=True)

    def handle(self, *args, **options):
        raw = options['input'].read_bytes()
        if hashlib.sha256(raw).hexdigest() != options['sha256']:
            raise CommandError('Input hash differs')
        source = install(raw, options['sha256'])
        self.stdout.write(f'source_id={source.pk} source_digest={source.digest}')
