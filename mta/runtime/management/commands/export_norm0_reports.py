import json
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from mta.runtime.norm0_reports import export_reports


class Command(BaseCommand):
    help='Export enabled Norm0 horizons from their completed native run without calculation.'

    def add_arguments(self,parser):
        parser.add_argument('--run',required=True)
        parser.add_argument('--output-digest',required=True)
        parser.add_argument('--owned-root',required=True)

    def handle(self,*args,**options):
        try:
            receipt=export_reports(run_id=options['run'],expected_output_digest=options['output_digest'],root=options['owned_root'])
        except (ValueError,KeyError,OSError,ObjectDoesNotExist) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps(receipt,sort_keys=True))
