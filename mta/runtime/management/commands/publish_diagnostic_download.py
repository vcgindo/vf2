"""Publish exact retained diagnostic custody; never replay a failed producer."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError


class Command(BaseCommand):
    help=__doc__

    def add_arguments(self,parser):
        owner=parser.add_mutually_exclusive_group(required=True)
        owner.add_argument('--failure-id')
        owner.add_argument('--operational-file-id',type=int)
        parser.add_argument('--output-root',type=Path)

    def handle(self,*args,**options):
        from mta.runtime import diagnostic_publication as service
        try:
            if options['failure_id'] is not None:
                if options['output_root'] is None:raise ValueError('Failure publication requires its explicit owned output root')
                row=service.publish_failure(options['failure_id'],output_root=options['output_root'])
            else:
                if options['output_root'] is not None:raise ValueError('Original operational custody already owns its root')
                row=service.publish_operational(options['operational_file_id'])
            self.stdout.write(json.dumps(dict(publication_id=row.pk,initialization_id=str(row.initialization_id),
                selector=row.selector,digest=row.digest)))
        except (ValueError,OSError,LookupError) as error:
            raise CommandError(str(error)) from error
