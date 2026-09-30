"""Supplement the connected trial with retained positive Rule4 seam evidence.

No new fixture or legacy execution. Recompute fresh Python against the exact
earlier canonical SQL captures after checking input, identity and source pins.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

from mta.domain.dbm_rules import too_much_in_red, stockout_rules_one_four
from mta.serialization import storage
from parity.temporal import differences

ROOT=Path(__file__).resolve().parents[1]
RETAINED=Path('F:/vflow_integrated/.local-stage7/block3')
CASES={
    'sequence-rule4-wins':(
        'aa618a26bed2136db16a2f483bd17c5dc113d500a879050627a104ca6316891d',
        'cec2ad9f8ad70f984c02a73e973c88c4ee6c140c1f8bfd8c5b8e32ab1353c71e'),
    'threshold-inclusive':(
        '21e60fcaefb8e458d5a44208c996e9123eba2d7a6f64cc9510b6024af2f45d72',
        '8bf0e262f00842e51136b2d78038a7517b615866b5f59871b30b8c305b68406f'),
}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources(value):
    if isinstance(value,dict):
        if set(value)>={'path','sha256'} and sha(Path(value['path']))!=value['sha256']:
            raise ValueError('Retained canonical source differs: '+value['path'])
        for child in value.values():verify_sources(child)
    elif isinstance(value,list):
        for child in value:verify_sources(child)


def run(destination):
    destination.mkdir(parents=True,exist_ok=False)
    sources=RETAINED/'rule4-proof-v1/sources.json'
    verify_sources(json.loads(sources.read_text()))
    results=[]
    for name,(input_sha,legacy_sha) in CASES.items():
        path=RETAINED/'rule4-inputs-v1'/f'{name}.input.json'
        oracle=RETAINED/'rule4-proof-v1'/f'{name}.legacy.json'
        if (sha(path),sha(oracle))!=(input_sha,legacy_sha):raise ValueError('Retained Rule4 artifact differs')
        fixture=json.loads(path.read_text());expected=json.loads(oracle.read_text())
        logical=hashlib.sha256(json.dumps({k:v for k,v in fixture.items() if k!='input_sha256'},
                              sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        if logical!=fixture['input_sha256']:raise ValueError('Rule4 logical identity differs')
        identity=RETAINED/'rule4-inputs-v1'/f'{name}.identity.json'
        if json.loads(identity.read_text())['status']!='PASS':raise ValueError('Retained identity failed')
        before=deepcopy(fixture['state'])
        fn=stockout_rules_one_four if fixture['ordered_sequence'] else too_much_in_red
        actual=storage(fn(fixture['business_date'],fixture['state']))
        if fixture['state']!=before:raise ValueError('Rule4 mutated its external input')
        if set(actual)!=set(expected):raise ValueError('Rule4 table roster differs')
        checks=[dict(table=table,differences=differences(expected[table],actual[table],'/'+table))
                for table in expected]
        positives=sum(r['Type']==4 for r in actual['Suggestions'])
        passed=positives>0 and all(not c['differences'] for c in checks)
        with (destination/f'{name}.modern.json').open('x',encoding='utf-8') as stream:json.dump(actual,stream,indent=2)
        results.append(dict(case=name,status='PASS' if passed else 'FAIL',input_path=str(path),input_sha256=input_sha,
                            legacy_path=str(oracle),legacy_sha256=legacy_sha,identity_sha256=sha(identity),
                            logical_input_sha256=logical,positive_rule4_suggestions=positives,comparisons=checks))
    receipt=dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',
                 scope='Fresh Python vs retained qualified SQL; positive Rule4 seams, not full daily/population acceptance',
                 source_receipt_sha256=sha(sources),modern_sha256=sha(ROOT/'mta/domain/dbm_rules.py'),cases=results)
    with (destination/'comparison.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps(dict(status=receipt['status'],cases=len(results),compared_tables=sum(len(r['comparisons']) for r in results))))
    return receipt['status']=='PASS'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination',type=Path,required=True)
    raise SystemExit(0 if run(parser.parse_args().destination) else 1)
