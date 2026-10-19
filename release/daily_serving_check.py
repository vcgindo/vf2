"""Verify the actual MTA process serves the exact selected candidate; no mutation.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import argparse
import json
import os
from pathlib import Path
import runpy
import urllib.request


def configure_image(identity=Path('/opt/vectorflow/release.json')):
    if identity.is_file():
        # The bootstrap lives outside the authenticated /app source roster.
        # Load its image-owned location without changing a sealed application.
        configure = runpy.run_path(str(identity.with_name('image_entrypoint.py')))['configure']
        configure(identity)


def check(run_id, output_digest):
    configure_image()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.mta_settings')
    import django
    django.setup()
    from django.conf import settings
    from mta.presentation.admission import admit
    from mta.presentation.native_selection import read
    expected = admit()
    if expected['run_id'] != run_id or expected['output_digest'] != output_digest:
        raise ValueError('MTA container is configured for another run/output')
    with urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=10) as response:
        actual = json.load(response)
    selected = read(settings.VF_MTA_SELECTION_FILE)
    if actual.get('ready') is not True or actual.get('admission_digest') != expected['admission_digest']:
        raise ValueError('Serving process has not admitted the selected generation')
    return dict(ready=True, run_id=run_id, output_digest=output_digest,
        selection_digest=selected['selection_digest'], admission_digest=expected['admission_digest'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-digest', required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.run_id, args.output_digest), sort_keys=True))
