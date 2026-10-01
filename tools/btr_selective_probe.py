"""Read-only affected BTR proof against the registered independent SQL receipts.

Run in the isolated test worker; no new legacy replay, serving switch or writes.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.conf import settings
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from mta.presentation.admission import admit
from parity.temporal import differences


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = Path(sys.argv[1])
    target.mkdir(exist_ok=False)
    root = Path('/evidence/f3-btr-filters-modern-001')
    legacy = Path('/evidence/f3-btr-filters-comparison-001')
    retained = json.loads((root / 'receipt.json').read_text())
    oracle = json.loads((legacy / 'receipt.json').read_text())
    assert sha(root / 'receipt.json') == oracle['modern_receipt_sha256']
    assert sha(root / 'cases.json') == retained['cases_sha256']
    cases = json.loads((root / 'cases.json').read_text())['cases']
    settings.DATABASES['default']['OPTIONS']['options'] += ' -c default_transaction_read_only=on -c statement_timeout=45000'
    result = dict(status='FAILED', checks=[], engine_replays=0, writes=False,
                  retained_modern_sha256=sha(root / 'receipt.json'), retained_legacy_sha256=sha(legacy / 'receipt.json'))
    try:
        with override_settings(VF_MTA_PUBLISHED_RUN='ac1612c8-0e49-4155-83c3-f59f41422293',
                VF_MTA_PUBLISHED_DIGEST='bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d',
                VF_MTA_PERMISSIONS_FILE='/inputs/permission-input-v1.json',
                VF_MTA_PERMISSIONS_SHA256='18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356',
                VF_MTA_HIERARCHY_FILE='/app/baseline/presentation-hierarchy-v1.json',
                VF_MTA_HIERARCHY_SHA256='d69c63804798b3cf31f98849341d7a61d38a37fe73c05e627aef1237e5ecfc6a',
                VF_MTA_TERMINAL_FILE='/app/baseline/presentation-terminal-v1.json',
                VF_MTA_TERMINAL_SHA256='bca78680e3fd2162c097ef0abcc5894e9177e77da5a3d75cb367742fbf97fdd5'):
            result['admission'] = admit()
            client = Client()
            with patch('mta.presentation.views.publication', side_effect=AssertionError('whole-publication read forbidden')):
                for index, case in enumerate(cases):
                    for route in ('GetBTRDataCount', 'GetBTRData'):
                        entry = next(row for row in retained['observations'] if row['case_id'] == case['id'] and row['path'] == route)
                        path = root / entry['payload']
                        assert sha(path) == entry['sha256']
                        with gzip.open(path, 'rt') as stream:
                            old = json.load(stream)
                        independent = next(row for row in oracle['cases'] if row['id'] == case['id'] and row['route'] == route)
                        expected = old['response']
                        if independent['status'] == 'PASS':
                            if route == 'GetBTRData':
                                legacy_path = legacy / independent['legacy_response_file']
                                assert sha(legacy_path) == independent['legacy_response_sha256']
                                with gzip.open(legacy_path, 'rt') as stream:
                                    data = json.load(stream)
                            else:
                                data = independent['counts']
                            assert not differences(data, expected['data']) and data == expected['data']
                        else:
                            assert independent['status'] == 'LEGACY_FLAW_NOT_PARITY' and old['status'] == 503
                        started = time.monotonic()
                        with CaptureQueriesContext(connection) as captured:
                            response = client.post('/api/mta/' + route, data=case['payload'], content_type='application/json',
                                                   HTTP_X_VECTORFLOW_IDENTITY='{"id":"1"}')
                        body = response.json()
                        delta = differences(expected, body, '/' + case['id'] + '/' + route)
                        row = dict(case=case['id'], route=route, status=response.status_code,
                                   seconds=time.monotonic() - started, query_count=len(captured),
                                   independent_status=independent['status'], differences=delta,
                                   ordered_body_equal=expected == body)
                        result['checks'].append(row)
                        with gzip.open(target / f'response-{index:02d}-{route}.json.gz', 'wt') as stream:
                            json.dump(dict(request=case['payload'], status=response.status_code, response=body,
                                           queries=[q['sql'] for q in captured]), stream)
                        assert response.status_code == old['status'] and not delta and expected == body, row
                    print(json.dumps(dict(case=case['id'], status='PASS_EXACT_RETAINED')), flush=True)
            result.update(status='PASS_BTR_SELECTIVE_RETAINED_CONTRACTS',
                          strict_pass=sum(row['independent_status'] == 'PASS' for row in result['checks']),
                          declared_flaws=sum(row['independent_status'] == 'LEGACY_FLAW_NOT_PARITY' for row in result['checks']),
                          qualification='Private identity retained consumer proof; not serving/browser/matched speed acceptance')
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        result['sources'] = {name: sha(Path('/app') / name) for name in ('mta/presentation/btr_sql.py', 'mta/presentation/views.py')}
        (target / 'receipt.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
