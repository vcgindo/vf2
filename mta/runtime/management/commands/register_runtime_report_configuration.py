"""Register only retained report definitions for future native captures."""
import hashlib
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from mta.application import runtime_report_configuration as definitions


def read_reference(path, expected_sha256):
    from mta.runtime.ingestion_context import sha
    sha(expected_sha256)
    with Path(path).open('rb') as stream:
        raw = stream.read(definitions.LIMIT + 1)
    if not 0 < len(raw) <= definitions.LIMIT or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Bounded report registration input SHA256 differs')
    return json.loads(raw, object_pairs_hook=definitions._pairs, parse_constant=definitions._nonfinite)


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--configuration', type=Path, required=True)
        for name in ('sha256', 'initialization-id', 'source-digest', 'certificate-digest'):
            parser.add_argument('--' + name, required=True)

    def handle(self, *args, **options):
        try:
            from mta.runtime.report_definition_registration import register
            reference = read_reference(options['configuration'], options['sha256'])
            owner = register(reference, initialization_id=options['initialization_id'],
                source_digest=options['source_digest'], certificate_digest=options['certificate_digest'])
            self.stdout.write(json.dumps(dict(registration_digest=owner.pk,
                initialization_id=str(owner.initialization_id), source_digest=owner.source_digest,
                definition_digest=owner.definition_digest, seed_digest=owner.seed_digest,
                configuration_digest=owner.configuration_digest)))
        except (ValueError, OSError, LookupError) as error:
            raise CommandError(str(error)) from error
