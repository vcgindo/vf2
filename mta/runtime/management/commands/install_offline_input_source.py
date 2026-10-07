import json
from pathlib import Path
from django.core.management.base import BaseCommand
from mta.mdm.offline_source import install


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('input',type=Path)
        parser.add_argument('--sha256',required=True)
        parser.add_argument('--owner',required=True)

    def handle(self,*args,**options):
        source = install(options['input'].read_bytes(),options['sha256'],options['owner'])
        self.stdout.write(json.dumps(dict(id=source.pk,digest=source.digest,
                                         owner=options['owner'],artifact_sha256=options['sha256'])))
