"""Install the pinned Location and SKU–Location sources onto the selected root."""
from pathlib import Path

from django.core.management.base import BaseCommand
from mta.mdm.source import source


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('source_directory')
        parser.add_argument('--family', choices=('2', '3', 'all'), default='all',
                            help='Select an uninstalled family after a partial installation; never reset one.')

    def handle(self, *args, **options):
        from mta.mdm.location_source import install_location
        from mta.mdm.skuloc_source import install_skuloc
        installed = source()
        root = Path(options['source_directory'])
        if options['family'] in ('2', 'all'):
            install_location(root / 'location', installed)
        if options['family'] in ('3', 'all'):
            install_skuloc(root / 'skuloc', installed)
        self.stdout.write('Selected MDM family sources installed on ' + installed.digest)
