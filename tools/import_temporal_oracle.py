"""Extract canonical SQL orchestration without the old shared-DB replay harness.

Fresh SQL ownership is already enforced by legacy_isolation. Business SQL and
producer order are unchanged. Only test orchestration/metadata dependencies move.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PREVIOUS=Path('F:/vflow_integrated')
REVISION='66a77735d3f3f9a9becf4c87a08ae7827900cf84'


def source(path):
    return subprocess.check_output(['git','-C',str(PREVIOUS),'show',f'{REVISION}:{path}']).decode('utf-8-sig').replace('\r\n','\n')


def replace_once(text, old, new):
    if text.count(old)!=1:raise ValueError('Extraction boundary differs: '+old[:80])
    return text.replace(old,new,1)


def between(text, begin, end, replacement):
    start=text.index(begin); stop=text.index(end,start)
    return text[:start]+replacement+text[stop:]


def extract():
    records=[]
    def write(path,text,origin,original,changes):
        ast.parse(text)
        target=ROOT/path
        if target.exists():raise ValueError('Refusing overwrite: '+path)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(text,encoding='utf-8')
        records.append(dict(path=path,source=origin,source_sha256=hashlib.sha256(original.encode()).hexdigest(),changes=changes))

    origin='parity/block3_control_carry_cases.py'; original=source(origin)
    selected=[]
    for node in ast.parse(original).body:
        if isinstance(node,ast.FunctionDef):break
        if isinstance(node,(ast.Assign,ast.Expr)) and not isinstance(getattr(node,'value',None),ast.Constant):
            selected.append(ast.get_source_segment(original,node))
    timeline=source('mta/application/calculation_timeline.py')
    shared=next(n for n in ast.parse(timeline).body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='SHARED_CONTROLS' for t in n.targets))
    support='''"""Static SQL bindings only; no modern producer or fixture generator."""
from datetime import date, datetime
from decimal import Decimal
import json

def _json(value):
    if isinstance(value,(date,datetime)): return value.isoformat()
    if isinstance(value,Decimal): return format(value,'f')
    raise TypeError(type(value).__name__)

def _write(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,default=_json)

'''+ '\n\n'.join(selected)+'\n\n'+ast.get_source_segment(timeline,shared)+'\n'
    write('parity/adapters/legacy/temporal_support.py',support,origin,original,
          'Extract static control bindings and SHARED_CONTROLS only; local typed JSON helpers')

    origin='parity/adapters/legacy/block3_accepted_norm_stock.py'; original=source(origin)
    selected=[]
    for node in ast.parse(original).body:
        if isinstance(node,ast.FunctionDef) and node.name not in ('_sha','source_receipt'):continue
        if isinstance(node,ast.ImportFrom) and node.module.startswith('parity.'):continue
        selected.append(ast.get_source_segment(original,node))
    write('parity/adapters/legacy/temporal_maintenance.py','\n\n'.join(selected)+'\n',origin,original,
          'Retain exact approved maintenance capture and source hash checks, exclude execution/test framework')

    origin='parity/adapters/legacy/block3_one_pass.py'; original=source(origin)
    text=original.replace('from parity.adapters.legacy.block2_binding import MAPPING, bind_sql',
                          'from parity.legacy_isolation import MAPPING, bind_sql')
    text=text.replace("EVIDENCE = Path('.local-stage7/block3-one-pass/delivery-v1')",
                      "EVIDENCE = Path('F:/vflow_integrated/.local-stage7/block3-one-pass/delivery-v1')")
    text=text.replace('parity.adapters.legacy.block3_accepted_norm_stock','parity.adapters.legacy.temporal_maintenance')
    text=text.replace('from mta.application.calculation_timeline import SHARED_CONTROLS',
                      'from parity.adapters.legacy.temporal_support import SHARED_CONTROLS')
    text=between(text,'def prepare():','class DeliverySQL:', '''def prepare():
    # Read-only retained metadata. Never create or bless source pins on replay.
    register=json.loads((Path(__file__).resolve().parents[3]/'baseline/temporal-oracle-reuse.json').read_text())
    for resource in register['resources']:
        if hashlib.sha256(Path(resource['path']).read_bytes()).hexdigest()!=resource['sha256']:
            raise ValueError('Registered oracle metadata differs: '+resource['path'])
    baseline=json.loads((Path(__file__).resolve().parents[3]/'baseline/manifest.json').read_text())
    for row in baseline['canonical_api']+baseline['engine_sources']:
        if hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Canonical source changed: '+row['path'])
    pins=json.loads((EVIDENCE/'full-sql-pins.json').read_text())
    for path,expected in pins.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:
            raise ValueError('Pinned SQL source drift: '+path)
    return pins


''')
    write('parity/adapters/legacy/temporal_delivery.py',text,origin,original,
          'Fresh-only binding; read-only metadata pin check; static controls; unchanged SQL execution sequence')

    origin='parity/adapters/legacy/block3_calculation_timeline.py'; original=source(origin)
    text=original.replace('from parity.adapters.legacy.block2_binding import BoundCursor, MAPPING, validate_files',
                          'from parity.legacy_isolation import Cursor as BoundCursor, MAPPING')
    text=text.replace('from parity.block3_control_carry_cases import BINDINGS as CONTROL_BINDINGS, SCRIPTS as CONTROL_SCRIPTS',
                      'from parity.adapters.legacy.temporal_support import BINDINGS as CONTROL_BINDINGS, SCRIPTS as CONTROL_SCRIPTS')
    text=text.replace('from parity.block3_ingestion_evidence import _json, _write',
                      'from parity.adapters.legacy.temporal_support import _json, _write')
    text=text.replace('parity.adapters.legacy.block3_one_pass','parity.adapters.legacy.temporal_delivery')
    text=text.replace("!= 'block2'","!= 'fresh'").replace('VFTEST_PROFILE=block2','VFTEST_PROFILE=fresh')
    text=between(text,'    owned_locks = []','        quote = lambda name:',
                 "    with runner.connection('VFTEST_Importer') as owner:\n        raw = owner.raw\n")
    text=between(text,'        def fingerprints():','        def load(', '')
    text=between(text,'        before, original_identity = fingerprints(), identity()','        result = None','')
    text=between(text,"            after = fingerprints()",'        if error is not None:', '')
    text=replace_once(text,"        result['rollback_verified'] = True\n        result['identity_restored'] = True",
                      "        result['rollback_executed'] = True\n        result['ownership'] = 'exclusive Fresh-only databases; counters are owned scratch'")
    write('parity/adapters/legacy/temporal_day.py',text,origin,original,
          'Fresh exclusive lease replaces Block2 locks; no whole-DB fingerprints/restoration; unchanged producer SQL; rollback owned transaction only')

    resources=[]
    for name in ('btr-source-contract.json','consumer-settings-full.json','selected-clock-source.json','full-sql-pins.json'):
        p=PREVIOUS/'.local-stage7/block3-one-pass/delivery-v1'/name
        resources.append(dict(path=p.as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    p=PREVIOUS/'docs/block3/R2_ACCEPTED_NORM_STOCK_CONTRACT.md'
    resources.append(dict(path=p.as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),role='previously approved shared-tempdb capture only'))
    target=ROOT/'baseline/temporal-oracle-reuse.json'
    if target.exists():raise ValueError('Oracle manifest already exists')
    target.write_text(json.dumps(dict(revision=REVISION,files=records,resources=resources),indent=2),encoding='utf-8')
    print(json.dumps(dict(modules=len(records),resources=len(resources))))


if __name__=='__main__':extract()
