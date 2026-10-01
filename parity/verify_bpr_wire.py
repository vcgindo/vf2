"""Verify actual HTTP wire against accepted raw SQL and pinned DLL/config types."""
from decimal import Decimal
import gzip
import json
from pathlib import Path
import re
import subprocess
import sys
from parity.output_archive import file_sha
from parity.verify_rrr_consumer import wire_rows
from parity.temporal import differences

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path('D:/freshvcf-build/evidence')
RAW = EVIDENCE/'f3-bpr-terminal-003'
RAW_SHA = '89a9ba03575422174690183aaa1771340aa57d759c925a1c6ecb27ad11ec1693'


def main():
    target = Path(sys.argv[1]); target.mkdir(parents=True,exist_ok=False)
    result = dict(status='FAILED',engine_replays=0,new_sql_comparisons=0,persistent_writes=False)
    try:
        assert file_sha(RAW/'receipt.json') == RAW_SHA
        raw_receipt = json.loads((RAW/'receipt.json').read_text())
        assert raw_receipt['status'] == 'PASS_TERMINAL_BPR_RAW_TYPED_SCOPED_CONSUMER'
        for name,sha in raw_receipt['candidate_sources'].items():
            assert file_sha(ROOT/name) == sha, name
        for name in ('legacy.json.gz','requests.json'):
            assert file_sha(RAW/name) == raw_receipt['file_hashes'][name]
        source = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/DBCreation/UI_ReportColumnTypes_2.0.sql')
        assert file_sha(source) == '51883c78e5effbb55b303f07b99df9c84a3a336b0525d19b0540a9b95df02a19'
        il = EVIDENCE/'f3-bpr-wire-source-001/VectorFlowAPIs.il'
        assert file_sha(il) == 'ccd47dc8d76895a6aa63ad5d6beaadb32f4f53ab75047a68fb8055382fd87ca1'
        types = {k.casefold():v for k,v in re.findall(r"VALUES \(N'AdminBPR', N'([^']+)', N'([^']+)'\)",source.read_text())}
        assert len(types) > 70
        runtime = json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
        args = ['docker','run','--rm','--name','freshvcf-bpr-wire-proof','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v',ROOT.as_posix()+':/app:ro',
            '-v',EVIDENCE.as_posix()+':/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_','MTA_')): args += ['-e',value]
        args += ['-e','VF_MTA_TERMINAL_FILE=/app/baseline/presentation-terminal-v1.json',
                 '-e','VF_MTA_TERMINAL_SHA256='+file_sha(ROOT/'baseline/presentation-terminal-v1.json')]
        for mount in runtime['Mounts']:
            if mount['Destination'] != '/app': args += ['-v',mount['Source']+':'+mount['Destination']+':ro']
        proc = subprocess.run(args+[runtime['Image'],'python','tools/bpr_wire_probe.py',
            '/evidence/f3-bpr-terminal-003/requests.json'],text=True,capture_output=True)
        (target/'stderr.log').write_text(proc.stderr)
        if proc.returncode: raise RuntimeError('Private HTTP probe failed; see stderr.log')
        observed = json.loads(proc.stdout)
        with gzip.open(target/'modern.json.gz','wt') as stream: json.dump(observed,stream)
        original = json.load(gzip.open(RAW/'legacy.json.gz','rt'))
        assert len(original) == len(observed) == 7
        delta = []; expected = []
        for case, actual in zip(original,observed):
            assert case['id'] == actual['id']
            rows = [{k:Decimal(v['value']) if v['type']=='decimal' else v['value'] for k,v in row.items()}
                    for row in case['rows']]
            grid = wire_rows(rows,types)
            expected.append(dict(id=case['id'],grid=grid,count=str(case['count'])))
            delta += differences(grid,actual['GetBPRData']['data'],'/'+case['id']+'/data')
            assert actual['GetBPRDataCount']['recordCount'] == str(case['count'])
            assert [(r['WHCode'],r['SKUCode']) for r in grid] == [
                (r['WHCode'],r['SKUCode']) for r in actual['GetBPRData']['data']]
        with gzip.open(target/'expected.json.gz','wt') as stream: json.dump(expected,stream)
        result.update(status='PASS_TERMINAL_BPR_HTTP_WIRE' if not delta else 'FAIL',
            raw_receipt_sha256=RAW_SHA,source_il_sha256=file_sha(il),type_config_sha256=file_sha(source),
            source_hashes={p:file_sha(ROOT/p) for p in ('mta/presentation/views.py','mta/presentation/urls.py',
                'mta/presentation/bpr_response.py','tools/bpr_wire_probe.py')},
            cases=len(expected),comparisons=2*len(expected),differences=delta,
            evidence_hashes={n:file_sha(target/n) for n in ('modern.json.gz','expected.json.gz')},
            qualification='Selected private HTTP scope/paging and full field types; not actual login/browser/filters/export/action proof')
        if delta: raise ValueError('Wire differences retained')
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        (target/'receipt.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(status=result['status'],comparisons=result['comparisons'])))


if __name__ == '__main__': main()
