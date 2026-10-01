"""Compare DBM's shared description lookups with deployed SQL on retained facts."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from parity.insight_queries import SOURCE, SOURCE_SHA
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_excess_readmodel import literals
from parity.verify_rrr_consumer import auth_ctes, supplement_temp_hierarchy, temp_rows


def main():
    target = Path(sys.argv[1]).resolve()
    assert target.parent == Path('D:/freshvcf-build/evidence').resolve() and not target.exists()
    target.mkdir()
    result = dict(status='FAILED', engine_replays=0, persistent_sql_writes=False,
                  serving_changes=False, postgres_writes=False)
    try:
        dll = Path('F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll')
        assert file_sha(dll) == '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346'
        assert file_sha(SOURCE) == SOURCE_SHA
        source = SOURCE.read_text()
        il_path = Path('D:/freshvcf-build/evidence/f3-bpr-wire-source-001/VectorFlowAPIs.il')
        il = il_path.read_text()
        queries = {}
        for route, method in [('SKUDesc', 'GetSKUDescription'), ('WHDesc', 'GetWHDescription')]:
            body = source.split('public responseMessage ' + method + '(', 1)[1].split('\n\tpublic ', 1)[0]
            parts = re.findall(r'(?m)^\s*(?:string )?text\s*(?:\+=|=)\s*(.*);$', body)
            assert len(parts) == 3
            query = ''.join(literals(part) for part in parts)
            method_il = il.split('} // end of method GuidedInsightsProcessor::' + method, 1)[0].rsplit('\n\t.method', 1)[1]
            for part in parts:
                for literal in re.findall(r'"(?:[^"\\]|\\.)*"', part):
                    assert literal in method_il
            assert 'Startup::VectorFlow_BufferTrend' in method_il
            table = 'SKUDescriptionTbl' if route == 'SKUDesc' else '[SiteDescriptionTbl]'
            queries[route] = query.replace(table, '[#Descriptions]')
        catalogue_path = Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(catalogue_path) == '18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356'
        catalogue = json.loads(catalogue_path.read_text())
        sku_leaf, loc_leaf = [next(r['id'] for r in catalogue[k]['records']
            if all(r['level_' + str(i)] is not None for i in (1, 2, 3))) for k in ('products', 'locations')]
        cases = [dict(id=name, hierarchy=hierarchy, payload=dict(product_permissions=products, location_permissions=locations))
            for name, hierarchy, products, locations in [
                ('root', True, [71001], [72001]), ('product-leaf', True, [sku_leaf], [72001]),
                ('location-leaf', True, [71001], [loc_leaf]),
                ('root-and-leaf-overlap', True, [71001, sku_leaf], [72001, loc_leaf]),
                ('native-null-hierarchy', False, [71001], [72001]),
                ('empty-product', True, [], [72001]), ('empty-location', True, [71001], [])]]
        (target / 'requests.json').write_text(json.dumps(cases, indent=2))
        relative = target.name
        probe = '''import os,json
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django;django.setup()
from django.conf import settings
settings.DATABASES['default']['OPTIONS']['options']+=' -c default_transaction_read_only=on'
from django.test import Client,override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from mta.runtime.models import CalculationRun
from mta.presentation.admission import admit
from unittest.mock import patch
target=Path('/evidence/TARGET')
cases=json.loads((target/'requests.json').read_text()); rows=[]
with override_settings(VF_MTA_PUBLISHED_RUN='ac1612c8-0e49-4155-83c3-f59f41422293',
 VF_MTA_PUBLISHED_DIGEST='bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d',
 VF_MTA_PERMISSIONS_FILE='/inputs/permission-input-v1.json',VF_MTA_PERMISSIONS_SHA256='18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356',
 VF_MTA_HIERARCHY_FILE='/app/baseline/presentation-hierarchy-v1.json',VF_MTA_HIERARCHY_SHA256='d69c63804798b3cf31f98849341d7a61d38a37fe73c05e627aef1237e5ecfc6a',
 VF_MTA_TERMINAL_FILE='/app/baseline/presentation-terminal-v1.json',VF_MTA_TERMINAL_SHA256='bca78680e3fd2162c097ef0abcc5894e9177e77da5a3d75cb367742fbf97fdd5'):
 admission=admit();client=Client()
 for case in cases:
  opts={} if case['hierarchy'] else dict(VF_MTA_HIERARCHY_FILE='',VF_MTA_HIERARCHY_SHA256='')
  with override_settings(**opts),patch('mta.presentation.views.publication',side_effect=AssertionError('no whole-run read')):
   for route in ('SKUDesc','WHDesc'):
    with CaptureQueriesContext(connection) as captured:
     response=client.generic('GET','/api/mta/'+route,data=json.dumps(case['payload']),content_type='application/json',HTTP_X_VECTORFLOW_IDENTITY='{"id":"1"}')
    rows.append(dict(case=case['id'],route=route,status=response.status_code,body=response.json(),queries=[q['sql'] for q in captured.captured_queries]))
 denied={route:client.get('/api/mta/'+route).status_code for route in ('SKUDesc','WHDesc')}
 assert set(denied.values())=={403}
(target/'modern.json').write_text(json.dumps(dict(cases=rows,admission=admission,unauthenticated=denied),indent=2))
print(json.dumps({'modern_cases':len(rows),'unauthenticated':denied}))
'''.replace('TARGET', relative)
        (target / 'modern-probe.py').write_text(probe)
        subprocess.run(['docker', 'compose', '-f', str(ROOT / 'compose.test.yaml'), 'run', '--rm', '-T', '--no-deps',
            '--name', 'freshvcf-stage2-descriptions', '-v', 'F:/freshvcf/vectorflow:/app/vectorflow:ro',
            'mta', 'python', '-'], input=probe, text=True, check=True)
        modern = json.loads((target / 'modern.json').read_text())
        legacy, provenance = terminal_inputs()
        tables = legacy['closing']['btr']
        expected, checks = [], []
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay():
            for case in cases:
                for route in ('SKUDesc', 'WHDesc'):
                    with connection('VFTEST_BTR') as db:
                        temp_rows(db, '#Sku', 'dbo.SkuAttributeData', tables['SkuAttributeData'])
                        temp_rows(db, '#Loc', 'dbo.LocationAttributeData', tables['LocationAttributeData'])
                        name = 'SKUDescriptionTbl' if route == 'SKUDesc' else 'SiteDescriptionTbl'
                        temp_rows(db, '#Descriptions', 'dbo.' + name, tables[name])
                        if case['hierarchy']:
                            supplement_temp_hierarchy(db, catalogue)
                        payload = case['payload']
                        # The other kind is not used by this method's final CTE.
                        bound = {key: value or [71001 if key == 'product_permissions' else 72001]
                                 for key, value in payload.items()}
                        auth = auth_ctes(db, catalogue, bound)
                        key = 'product_permissions' if route == 'SKUDesc' else 'location_permissions'
                        if not payload[key]:
                            # Exact deployed fallback adds quotes around already
                            # quoted empty input, leaving a quote in string_split.
                            table = '#ProductPermissions' if route == 'SKUDesc' else '#LocationPermissions'
                            error_query = "SELECT id FROM " + table + " WHERE id IN (SELECT value FROM STRING_SPLIT('''', ','))"
                            try:
                                db.execute(error_query).fetchall()
                            except Exception as exc:
                                assert '245' in str(exc) and 'Conversion failed' in str(exc)
                                data, status = None, 500
                            else:
                                raise AssertionError('Expected deployed empty-ID conversion failure')
                        else:
                            scalar = db.execute(auth + queries[route]).fetchone()[0]
                            data, status = json.loads(scalar) if scalar else None, 200
                        body = dict(recordCount=None, data=data, status=status, msg=None,
                                    errorCount=None, error=None, conflictErrorCount=None, conflictError=None)
                        actual = next(row for row in modern['cases'] if row['case'] == case['id'] and row['route'] == route)
                        delta = differences(body, actual['body'], '/' + case['id'] + '/' + route)
                        assert status == actual['status'] and not delta, delta
                        expected.append(dict(case=case['id'], route=route, status=status, body=body))
                        checks.append(dict(case=case['id'], route=route, status=status,
                                           population=None if data is None else len(data), exact_typed=True))
        (target / 'legacy.json').write_text(json.dumps(expected, indent=2))
        (target / 'queries.json').write_text(json.dumps(queries, indent=2))
        result.update(status='PASS_RETAINED_DESCRIPTION_LOOKUPS', checks=checks, legacy_provenance=provenance,
            canonical_dll_sha256=file_sha(dll), canonical_source_sha256=SOURCE_SHA,
            il_sha256=file_sha(il_path), comparison='full ordered typed envelope and HTTP status; no count-only proof',
            hierarchy='exact approved six-field terminal opt-in; native-null case keeps opt-in off',
            modern_sha256=file_sha(target / 'modern.json'), legacy_sha256=file_sha(target / 'legacy.json'))
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        (target / 'receipt.json').write_text(json.dumps(result, indent=2))
        print(json.dumps({key: result[key] for key in ('status', 'checks', 'error') if key in result}), flush=True)


if __name__ == '__main__':
    main()
