"""Convert supplied raw starter inputs to dated CSV examples; never calculate/seed answers.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from mta.application.production_csv_contract import SCHEMA_VERSION, feeds
from mta.application.operational_inputs import encode_csv
from mta.serialization import digest


def create(source, destination, *, csv_onboarding=False):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(source) as archive:
        opening = archive.read('initialization.json')
        (destination / 'initialization.json').write_bytes(opening)
        (destination / 'permissions.json').write_bytes(archive.read('permissions.json'))
        base = None
        for name in ('day-01.json', 'day-02.json'):
            value = json.loads(archive.read(name))
            if base is None:
                base = dict(schema='vectorflow-daily-binding-v1',
                    initialization_id='REPLACE_FROM_INITIALIZATION_RECEIPT',
                    source_digest='REPLACE_FROM_INITIALIZATION_RECEIPT',
                    configuration_digest=digest(json.loads(opening)['configuration']),
                    opening_file='initialization.json',
                    opening_sha256=hashlib.sha256(opening).hexdigest(),
                    intake_schema=value['intake_schema'],
                    producer_source_schema=value['producer_sources']['schema'],
                    report_policy=value['producer_sources']['report_policy'],
                    report_opening=value['producer_sources']['report_opening'],
                    consumer_opening_file='consumer-opening.json',
                    consumer_opening_sha256=hashlib.sha256(json.dumps(value['consumer_opening'],
                        sort_keys=True).encode()).hexdigest(),
                    validation={k:value['day'][k] for k in
                        ('phase_controls_input_validation', 'seasonality_input_validation')})
                (destination / 'consumer-opening.json').write_bytes(
                    json.dumps(value['consumer_opening'], sort_keys=True).encode())
            directory = destination / value['day']['business_date']
            directory.mkdir()
            declared = {}
            for filename, spec in feeds(value['intake_schema']).items():
                rows = value
                for key in spec['path'].split('/'):
                    rows = rows[key]
                declared[filename] = (value['day']['order_feed_status']
                    if filename == 'OrderFeed.csv' else 'PRESENT')
                if declared[filename] == 'PRESENT':
                    (directory / filename).write_bytes(encode_csv(spec['columns'], rows))
            manifest = dict(schema=SCHEMA_VERSION, batch_id='starter-' + value['day']['business_date'],
                            business_date=value['day']['business_date'], feeds=declared)
            (directory / 'batch.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
            (directory / 'READY').write_bytes(b'')
        (destination / 'binding-template.json').write_text(json.dumps(base, indent=2) + '\n', encoding='utf-8')
        from mta.application.production_csv_contract import describe
        (destination / 'csv-schema.json').write_text(json.dumps(describe(base['intake_schema']), indent=2) + '\n', encoding='utf-8')
        if csv_onboarding:
            from mta.application.initialization_csv import create as create_opening
            _, native = create_opening(json.loads(opening), destination / 'opening')
            # This is an automatically reconstructed provenance/download artifact.
            # Operators submit opening/*.csv to initialize_production --csv.
            (destination / 'native-opening.json').write_bytes(native)
            (destination / 'initialization.json').unlink()
            base['opening_file'] = 'native-opening.json'
            base['opening_sha256'] = hashlib.sha256(native).hexdigest()
            (destination / 'binding-template.json').write_text(json.dumps(base, indent=2) + '\n', encoding='utf-8')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('examples/starter-data/vectorflow-starter-inputs-v1.zip'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--csv-onboarding', action='store_true', help='Also export all master/opening populations as CSV')
    args = parser.parse_args()
    if args.csv_onboarding:
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.mta_settings')
        import django
        django.setup()
    print(create(args.source, args.output, csv_onboarding=args.csv_onboarding))
