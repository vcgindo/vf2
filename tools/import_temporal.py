"""Extract only pure temporal business functions from the pinned implementation.

No old run/audit/report persistence models are transferred. The fresh runtime
owns its daily run and calls the already verified current-day calculation.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REVISION='66a77735d3f3f9a9becf4c87a08ae7827900cf84'


def source(path):
    return subprocess.check_output(['git','-C','F:/vflow_integrated','show',f'{REVISION}:{path}']).decode('utf-8-sig').replace('\r\n','\n')


def extract():
    records=[]
    pending=[]
    def write(path,text,origin,original,transformation):
        target=ROOT/path
        if target.exists():
            if target.read_text(encoding='utf-8')!=text:raise ValueError('Refusing overwrite: '+path)
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(text,encoding='utf-8')
        records.append(dict(path=path,source_path=origin,source_sha256=hashlib.sha256(original.encode()).hexdigest(),transformation=transformation))
    def dependencies(text):
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,ast.ImportFrom) and node.module:
                if node.module.startswith('django'):raise ValueError('ORM dependency in selected pure code')
                if node.module in ('mta.domain','mta.application'):
                    pending.extend(node.module+'.'+name.name for name in node.names)
                    continue
                if node.module.startswith('mta.'):
                    if not node.module.startswith(('mta.domain.','mta.application.')):
                        raise ValueError('Non-pure dependency: '+node.module)
                    pending.append(node.module)
    origin='mta/application/calculation_timeline.py';original=source(origin)
    nodes=[]
    for node in ast.parse(original).body:
        if isinstance(node,ast.FunctionDef) and node.name=='read_calculation_day':break
        nodes.append(ast.get_source_segment(original,node))
    chain='\n\n'.join(nodes)+'\n'
    dependencies(chain)
    write('mta/temporal/chain.py',chain,origin,original,'Keep pure code through calculate_day; exclude every persistence function')
    origin='mta/application/dbm_delivery.py';original=source(origin)
    functions={node.name:ast.get_source_segment(original,node) for node in ast.parse(original).body if isinstance(node,ast.FunctionDef)}
    actions='from copy import deepcopy\nfrom datetime import datetime\n\n'+ '\n\n'.join(functions[name] for name in ('key','apply_command'))+'\n'
    write('mta/temporal/actions.py',actions,origin,original,'Extract key/apply_command only; no old ORM')
    visited=set()
    while pending:
        module=pending.pop()
        if module in visited:continue
        visited.add(module)
        path=module.replace('.','/')+'.py'
        original=source(path)
        if module=='mta.application.r1_report_facts':
            node=next(n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef) and n.name=='rationed_leftovers')
            text='from decimal import Decimal\n\n'+ast.get_source_segment(original,node)+'\n'
            write(path,text,path,original,'Extract pure rationed_leftovers only; exclude ORM report readers')
            continue
        if (ROOT/path).exists():
            if (ROOT/path).read_text(encoding='utf-8').replace('\r\n','\n')!=original:
                raise ValueError('Existing reused dependency changed; review explicitly: '+path)
            records.append(dict(path=path,source_path=path,source_sha256=hashlib.sha256(original.encode()).hexdigest(),transformation='Existing identical pinned pure dependency'))
            dependencies(original)
            continue
        dependencies(original)
        write(path,original,path,original,'LF only; pure functions unchanged')
    write('mta/temporal/__init__.py','','', '', 'Fresh package')
    path=ROOT/'baseline/temporal-reuse.json'
    if path.exists():raise ValueError('Manifest already exists')
    path.write_text(json.dumps(dict(revision=REVISION,files=records,acceptance='NOT_CERTIFIED'),indent=2),encoding='utf-8')
    print(json.dumps(dict(extracted=len(records),dependencies=len(visited))))


if __name__=='__main__':extract()
