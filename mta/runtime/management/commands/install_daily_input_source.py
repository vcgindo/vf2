"""Install the registered synthetic opening and fresh workflow owners once."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from mta.mdm.daily_source_install import install


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('input',type=Path)
        parser.add_argument('--sha256',required=True)

    def handle(self,*args,**options):
        source=install(options['input'].read_bytes(),options['sha256'])
        self.stdout.write(json.dumps(dict(id=source.pk,digest=source.digest,receipt=source.receipt)))
