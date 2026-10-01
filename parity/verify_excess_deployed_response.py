"""Recheck retained Excess SQL results with the actual deployed GetResponse.

No engine/producer/SQL replay: the independent query capture is hash-pinned.
The earlier hand-transcribed response is retained, but is not the wire oracle.
"""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
from parity.output_archive import file_sha
from parity.temporal import differences

RETAINED=Path('D:/freshvcf-build/evidence/f3-excess-readmodel-comparison-002')
RECEIPT_SHA='d5fbbea579ac8394746521c895fc0408d16478b08825e5be516af2211036f233'
SECTIONS=('location_count','location_value','sku_count','sku_value')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path); parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists(): raise ValueError('Preserve prior receipts; choose new evidence directory')
    args.evidence.mkdir(parents=True)
    result=dict(status='FAILED',engine_replays=0,sql_replays=0,persistent_database_writes=False)
    try:
        if file_sha(RETAINED/'receipt.json')!=RECEIPT_SHA: raise ValueError('Retained query receipt changed')
        retained=json.loads((RETAINED/'receipt.json').read_text())
        capture=RETAINED/'legacy-read-model.json.gz'
        if file_sha(capture)!=retained['legacy_read_model_sha256']: raise ValueError('Retained SQL results changed')
        if any(file_sha(Path(p))!=sha for p,sha in retained['source_hashes'].items()):
            raise ValueError('Deployed query source changed')
        with gzip.open(capture,'rt') as stream: expected=json.load(stream)
        modern=json.loads((args.modern/'receipt.json').read_text())
        if modern['status']!='READBACK_EXPORTED_COMPARISON_REQUIRED' or modern['boundary']!='UNSCOPED_EXCESS_READ_MODEL':
            raise ValueError('Wrong modern export')
        if (modern['run']['id']!=retained['legacy_source']['modern_run'] or
            modern['run']['output_digest']!=retained['legacy_source']['modern_output_digest']):
            raise ValueError('Paired accepted run differs')
        root=Path(__file__).resolve().parents[1]
        if any(file_sha(root/p)!=sha for p,sha in modern['sources'].items()): raise ValueError('Modern source changed')
        if file_sha(args.modern/modern['file'])!=modern['sha256']: raise ValueError('Modern readback changed')
        with gzip.open(args.modern/modern['file'],'rt') as stream: actual=json.load(stream)
        tables=[]
        for name in SECTIONS:
            rows=expected['queries'][name]
            if not rows: raise ValueError('Selected full-estate chart population must be nonempty')
            tables.append(dict(columns=[dict(name=n,type=('int64' if name.endswith('_value') else 'int32')
                if n=='counts' else 'string') for n in rows[0]],rows=rows))
        path=args.evidence/'canonical-query-results.json'
        path.write_text(json.dumps(dict(tables=tables)),encoding='utf-8')
        output=args.evidence/'deployed-method-response.json'
        harness=root/'parity/invoke_legacy_quadrant.ps1'
        completed=subprocess.run(['pwsh','-NoProfile','-File',str(harness),'-InputPath',str(path),
            '-OutputPath',str(output),'-Processor','ExcessInventoryProcessor'],text=True,capture_output=True)
        (args.evidence/'deployed-method.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        if completed.returncode: raise RuntimeError('Deployed method invocation failed; see preserved log')
        binary=json.loads(output.read_text(encoding='utf-8-sig'))
        if binary['input_sha256']!=file_sha(path): raise ValueError('Deployed method input changed')
        delta=[]
        for key in ('grid','count','uiConfig','queries'):
            delta+=differences(expected[key],actual[key],'/excess/'+key)
        delta+=differences(binary['response'],actual['response'],'/deployed-GetResponse')
        order={name:[r['counts'] for r in expected['queries'][name]]==
                    [r['counts'] for r in actual['queries'][name]] for name in SECTIONS}
        result.update(status='PASS_UNSCOPED_EXCESS_DEPLOYED_RESPONSE' if not delta and all(order.values()) else 'FAIL',
            differences=delta,declared_order_matches=order,rows={k:len(v) for k,v in expected['queries'].items()},
            earlier_hand_transcribed_response_differences=differences(binary['response'],expected['response'],'/earlier-response'),
            modern_receipt_sha256=file_sha(args.modern/'receipt.json'),retained_query_receipt_sha256=RECEIPT_SHA,
            canonical_query_results_sha256=file_sha(path),deployed_response_sha256=file_sha(output),
            invocation_source_sha256=file_sha(harness),runtime=binary['runtime'],serializer=binary['serializer'],
            qualification='Unscoped retained SQL bags and actual DLL pure-method wire response under recorded CLR; not hosted legacy HTTP, authenticated scopes/filters or browser acceptance')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','rows','declared_order_matches')}))
    if result['status']=='FAIL': raise SystemExit(1)


if __name__=='__main__': main()
