from django.core.management.base import BaseCommand
from mta.mdm.source import install_sku


class Command(BaseCommand):
    help = 'Install the explicitly pinned raw SKU application source once; no reset.'

    def add_arguments(self, parser):
        parser.add_argument('source_directory')

    def handle(self, *args, **options):
        source = install_sku(options['source_directory'])
        self.stdout.write(source.digest)
