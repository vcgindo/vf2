"""Retain redacted 3005 HTTP receipt with exact candidate image/source identity."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

target=Path(sys.argv[1]); target.mkdir(parents=True,exist_ok=False)
source=Path('tools/rrr_gateway_probe.py').read_bytes()
args=['docker','exec','-i']
export_mode=len(sys.argv)>2 and sys.argv[2]=='export'
if export_mode: args+=['-e','RRR_GATEWAY_EXPORT=1']
result=subprocess.run(args+['freshvcf-preview-user-service-1','python','-'],
    input=source.decode(),text=True,capture_output=True)
(target/'stdout.json').write_text(result.stdout,encoding='utf-8')
(target/'stderr.txt').write_text(result.stderr,encoding='utf-8')
(target/'probe-source.py').write_bytes(source)
runtime=json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
receipt=dict(exit_code=result.returncode,container=runtime['Id'],image=runtime['Image'],
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    dirty_source_hashes={str(p).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path('mta/presentation')/name for name in ('context.py','selective.py','rrr_sql.py','views.py','rrr_export.py','urls.py')]},
    probe_sha256=hashlib.sha256(source).hexdigest())
if result.returncode==0:
    receipt['proof']=json.loads(result.stdout)
    if export_mode:
        import base64
        parent=Path('D:/freshvcf-build/evidence/f3-rrr-export-comparison-001/receipt.json')
        expected=json.loads(parent.read_text())
        assert expected['status']=='PASS_RETAINED_EXPORT_SQL_HEADERS_TYPED_ROWS_AND_CSV_BYTES'
        receipt['oracle_receipt_sha256']=hashlib.sha256(parent.read_bytes()).hexdigest()
        for row in receipt['proof']['exports']:
            (target/(row['id']+'.csv')).write_bytes(base64.b64decode(row['base64']))
            row['legacy_bytes_match']=row['sha256']==next(c['legacy_sha256'] for c in expected['checks'] if c['id']==row['id'])
        receipt['proof']['status']='RRR_REAL_GATEWAY_EXPORT_BYTE_COMPARISON_PASS' if all(r['legacy_bytes_match'] for r in receipt['proof']['exports']) else 'FAILED_CSV_COMPARISON'
(target/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(dict(exit_code=result.returncode,receipt=str(target/'receipt.json'),stderr=result.stderr[-1200:])))
raise SystemExit(result.returncode or int(export_mode and receipt.get('proof',{}).get('status')!='RRR_REAL_GATEWAY_EXPORT_BYTE_COMPARISON_PASS'))
