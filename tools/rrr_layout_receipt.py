"""Verify one actual actor layout/export against retained independent RRR cells.

Read-only gateway and session-temp SQL; no engine replay or persistent SQL writes.
Run after browser layout save. Existing ten-case report proof is reused, not rerun.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha


def main():
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    parent = Path('D:/freshvcf-build/evidence/f3-rrr-export-comparison-001')
    assert file_sha(parent / 'receipt.json') == 'd9c24b50a782e7e32b8ff3392604a4c466c889dc854cac7549e045f1b9c4539a'
    receipt = json.loads((parent / 'receipt.json').read_text())
    previous = next(c for c in receipt['checks'] if c['id'] == 'location-type')
    prior_cells = next(c for c in json.loads((parent / 'oracle-cells.json').read_text())['cases']
                       if c['id'] == 'location-type')['records']
    old_headers = previous['headers']
    assert [c['value'] for c in prior_cells[0]] == [h for h, _ in old_headers]
    rows = [dict(zip([c for _, c in old_headers], row)) for row in prior_cells[1:]]
    assert len(rows) == 4
    case = next(c for c in json.loads((parent / 'requests.json').read_text())['cases']
                if c['id'] == 'location-type')
    payload = case['payload']
    payload['paginationParameter'] = {'pageNumber': 1, 'recordsPerPage': 2}
    prefix = (ROOT / 'tools/bpr_gateway_probe.py').read_text().split('observed=[]', 1)[0]
    source = prefix + '''
layout = session.post(base+'/api/mta/GetState',json={'reportname':'RRR','user':{'id':'forged'}},timeout=15)
assert layout.status_code == 200
reply = session.post(base+'/api/mta/GetExportDataAsync',json=PAYLOAD,timeout=15)
assert reply.status_code == 200
denied = requests.post(base+'/api/mta/GetExportDataAsync',json=PAYLOAD,headers={'Host':'localhost'},timeout=15)
assert denied.status_code == 401
print(json.dumps({'layout':layout.json(),'export_base64':base64.b64encode(reply.content).decode(),
 'status':reply.status_code,'content_type':reply.headers['Content-Type'],
 'unauthenticated_status':denied.status_code,'actor_payload_overridden':True}))
'''.replace('PAYLOAD', repr(payload))
    actual = json.loads(subprocess.check_output(
        ['docker', 'exec', '-i', 'freshvcf-preview-user-service-1', 'python', '-'],
        input=source, text=True))
    (target / 'gateway.json').write_text(json.dumps(actual, indent=2))
    layout = actual['layout']['data']
    columns = json.loads(layout)['columns']
    assert len(columns) == 37
    assert [c['colId'] for c in columns if c['hide']] == ['SKUName']
    request = {'cases': [dict(id='browser-layout-depo', payload=payload, layout=layout)]}
    (target / 'request.json').write_text(json.dumps(request, indent=2))
    script = ROOT / 'parity/invoke_legacy_rrr_export.ps1'
    subprocess.run(['pwsh', '-NoProfile', '-File', str(script), '-InputPath', str(target / 'request.json'),
                    '-OutputPath', str(target / 'headers.json'), '-Mode', 'headers'], check=True)
    query = json.loads((target / 'headers.json').read_text())['cases'][0]['query']
    for old, new in [('VFTEST_BINDING.dbo.[Userwise_UiReportConfiguration]', '#Layouts'),
                     ('VFTEST_BINDING.dbo.ui_ReportConfigurations', '#Config'),
                     ('VFTEST_BINDING.dbo.BufferTrendDates', '#Dates')]:
        query = query.replace(old, new)
    config = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/DBCreation/UI_ReportConfiguration_2.0.sql')
    assert file_sha(config) == '4b248637cd659bdf05730964513bf555103d83521a268e93cddb24bc8c6f34da'
    os.environ['VFTEST_PROFILE'] = 'fresh'
    with exclusive_replay():
        with connection('VFTEST_BPR') as db:
            db.execute('SELECT TOP 0 * INTO #Config FROM dbo.ui_ReportConfigurations; '
                       'SELECT TOP 0 * INTO #Layouts FROM dbo.Userwise_UiReportConfiguration; '
                       'SELECT TOP 0 * INTO #Dates FROM VFTEST_BTR.dbo.BufferTrendDates')
            lines = [line.strip().replace('[dbo].[ui_ReportConfigurations]', '#Config')
                     for line in config.read_text(encoding='utf-8-sig').splitlines()
                     if line.startswith('INSERT') and "VALUES (N'RationRequirementReport'," in line]
            assert len(lines) == 118
            db.execute('\n'.join(lines))
            db.execute('INSERT INTO #Layouts (username,reportname,state) VALUES (?,?,?)',
                       'rrr-export-proof', 'RRR', layout)
            cursor = db.execute(query)
            while cursor.description is None:
                assert cursor.nextset(), 'No canonical header result'
            mapping = sorted([(r[0] or '', r[1], r[2]) for r in cursor.fetchall()], key=lambda r: r[2])
    effective = [(h, c) for h, c, _ in mapping if c in rows[0]]
    assert len(effective) == 36 and 'SKUName' not in [c for _, c in effective]
    cells = [[{'type': 'str', 'value': h} for h, _ in effective]]
    cells += [[row[c] for _, c in effective] for row in rows]
    (target / 'header-query.sql').write_text(query)
    (target / 'oracle-cells.json').write_text(json.dumps({'cases': [dict(id='browser-layout-depo', records=cells)]}, indent=2))
    subprocess.run(['pwsh', '-NoProfile', '-File', str(script), '-InputPath', str(target / 'oracle-cells.json'),
                    '-OutputPath', str(target / 'legacy-csv.json'), '-Mode', 'csv'], check=True)
    expected = base64.b64decode(json.loads((target / 'legacy-csv.json').read_text())['cases'][0]['base64'])
    body = base64.b64decode(actual['export_base64'])
    (target / 'legacy.csv').write_bytes(expected)
    (target / 'gateway.csv').write_bytes(body)
    assert expected == body, 'Full CSV bytes differ from retained independent legacy rows/actual DLL headers'
    result = dict(status='PASS_ACTOR_LAYOUT_FILTERED_FULL_EXPORT', parent_receipt_sha256=file_sha(parent / 'receipt.json'),
                  rows=4, requested_page_size=2, headers=36, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                  unauthenticated_status=401, saved_layout=True, engine_replays=0, persistent_oracle_writes=False,
                  browser_download_file_verified=False, headers_and_cells=effective,
                  qualification='Gateway bytes; actual browser download file must be bound separately. No performance claim.')
    (target / 'receipt.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'headers_and_cells'}))


if __name__ == '__main__':
    main()
