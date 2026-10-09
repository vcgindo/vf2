"""Install explicit SOB and both MOQ raw bags on an existing pinned source."""
import hashlib
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from mta.mdm.source import DLL
from mta.mdm.supplier_source import install
from mta.runtime.mdm_models import MdmSource


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate installation JSON key: ' + key)
        result[key] = value
    return result


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('input_file')
        parser.add_argument('--sha256', required=True)
        parser.add_argument('--source-digest', required=True)

    def handle(self, *args, **options):
        try:
            data = Path(options['input_file']).read_bytes()
            if hashlib.sha256(data).hexdigest() != options['sha256']:
                raise ValueError('Supplier installation file checksum differs')
            manifest = json.loads(data, object_pairs_hook=unique_object)
            if set(manifest) != {'schema', 'dll_sha256', 'source_digest', 'raw',
                                 'moq_format', 'upload_log_active', 'provenance'}:
                raise ValueError('Supplier installation envelope differs')
            if (manifest['schema'] != 'fresh-mdm-supplier-install-v1'
                    or manifest['dll_sha256'] != DLL
                    or manifest['source_digest'] != options['source_digest']):
                raise ValueError('Supplier installation source identity differs')
            source = MdmSource.objects.get(digest=options['source_digest'])
            config = install(source, manifest['raw'], moq_format=manifest['moq_format'],
                upload_log_active=manifest['upload_log_active'], provenance=manifest['provenance'])
        except (OSError, ValueError, MdmSource.DoesNotExist) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write('Supplier owners installed on ' + source.digest +
                          '; installation ' + config.receipt_digest)
