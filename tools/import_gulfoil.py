"""One-time extraction of the selected pure file adapter and receipt register."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVISION = '66a77735d3f3f9a9becf4c87a08ae7827900cf84'
EVIDENCE = Path('F:/vflow_integrated/.local-stage7/block2-replay/gulfoil-continuation')


def extract():
    manifest = dict(revision=REVISION, files=[], receipts=[])
    for name in ('r1_file_input', 'r1_gulfoil_input'):
        path = f'mta/application/{name}.py'
        text = subprocess.check_output(['git','-C','F:/vflow_integrated','show',f'{REVISION}:{path}']).decode('utf-8-sig')
        for n in ast.walk(ast.parse(text)):
            if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('django'):
                raise ValueError('Not a pure producer: '+path)
        target = ROOT/path
        if target.exists():raise ValueError('Refusing overwrite: '+path)
        target.write_text(text.replace('\r\n','\n'),encoding='utf-8')
        manifest['files'].append(dict(path=path, source_sha256=hashlib.sha256(text.encode()).hexdigest(),transformation='LF only'))
    fixture = ROOT/'mta/fixtures/r1_gulfoil_common_selected.json'
    expected = '6d98b534b7e8e125ad0be985c4162e13b2288a5fa5a1e9402b6135e394ad5282'
    if hashlib.sha256(fixture.read_bytes()).hexdigest()!=expected:
        raise ValueError('Selected retained fixture differs from documented acceptance')
    manifest['input'] = dict(path=str(fixture.relative_to(ROOT)),sha256=expected,
                             role='retained approved five-SKU raw extension; not sizeable raw proof')
    names = ['selected-v2-identity.json','selected-v2-adapter.json','selected-v2-legacy.json',
             'selected-v2-legacy-repeat.json','selected-v2-standard.json',
             'selected-v2-report-comparison-contract.json', 'selected-v2-calculation-comparison.json',
             'selected-file-cases/summary.json']
    for case in ('valid','reordered','quoted','header_only','missing','byte_empty','missing_required_header'):
        names.extend(f'selected-file-cases/{case}/{n}.json' for n in ('input','result'))
    for name in names:
        path = EVIDENCE/name
        manifest['receipts'].append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    target=ROOT/'baseline/gulfoil-reuse.json'
    if target.exists():raise ValueError('Refusing overwrite: '+str(target))
    target.write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__=='__main__':extract()
