"""Benchmark-only sqlcmd transport: owned bindings and native SQLCMD output.

Canonical SQL and BAT conditions remain the business implementation. This adapter
only substitutes isolated database/path variables, impersonates a restricted
login, records elapsed time and prevents subsequent SQL after a failure.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.large_data_benchmark import EVIDENCE, bindings

SQLCMD = Path('C:/Program Files/Microsoft SQL Server/Client SDK/ODBC/180/Tools/Binn/SQLCMD.EXE')
CANONICAL = Path('F:/VFlow_Local/local-runtime/mta-engine')


def validate_source(raw, original, pin, relative, approval=None, report_approval=None, supplier_approval=None):
    """Exact approved variants only; original canonical pins stay mandatory."""
    if pin is None or hashlib.sha256(original).hexdigest() != pin:
        raise ValueError('Unpinned canonical SQL source: '+relative)
    if raw == original:
        return False
    variants = (
        (approval, 'APPROVE_ISOLATED_LEGACY_CORRECTION_AND_ONE_RERUN',
         'Scripts/BPR/Ration_Scripts/GenerateLogisticPickList.sql'),
        (report_approval, 'APPROVE_REPORT_FIX_AND_REMAINING_STAGE_CONTINUATION',
         'Scripts/BPR/OrderAllocationReports/CollectBOR_OrderAllocationData.sql'),
        (supplier_approval, 'APPROVE_BOUNDED_ALIGNMENT_AND_CONTINUATION',
         'Scripts/BPR/Ration_Scripts/GenSupplierWiseReq.sql'),
    )
    for receipt, decision, allowed_path in variants:
        if (receipt and receipt.get('decision') == decision and relative == allowed_path
                and receipt.get('canonical_sha256') == pin
                and hashlib.sha256(raw).hexdigest() == receipt.get('proposed_sha256')):
            return True
    raise ValueError('Canonical SQL bytes changed without exact variant approval')


def decode_output(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        return raw.decode('utf-16', errors='replace')
    if raw and raw[1::2].count(0) > len(raw) // 4:
        return raw.decode('utf-16-le', errors='replace')
    return raw.decode('utf-8-sig', errors='replace')


def execute(argv):
    case, isolation = bindings()
    failure = EVIDENCE/'day-failure.json'
    if failure.exists():
        raise ValueError('Previous failure preserved; no further SQL allowed')
    variables = {k.lower():v for k,v in os.environ.items()}
    passthrough = []
    database = None
    sql = None
    source = None
    output = None
    approved_variant = False
    i = 0
    while i < len(argv):
        key = argv[i]
        if key.lower() == '-v':
            i += 1
            while i < len(argv) and not argv[i].startswith('-'):
                name,value = argv[i].split('=',1)
                variables[name.lower()] = value.strip('"')
                i += 1
            continue
        if key.lower() in ('-i','-q','-d','-s','-o') and key not in ('-Q',):
            # -S is server; lowercase -s is the native result delimiter.
            if key == '-s':
                passthrough += argv[i:i+2]
                i += 2
                continue
        if key.lower() == '-i':
            source = Path(argv[i+1]).resolve()
            if not source.is_relative_to((EVIDENCE/'canonical').resolve()):
                raise ValueError('SQL file outside frozen canonical copy')
            original = CANONICAL/source.relative_to((EVIDENCE/'canonical').resolve())
            raw = source.read_bytes()
            pins = json.loads((ROOT/'baseline/manifest.json').read_text())['engine_sources']
            pin = next((p['sha256'] for p in pins if Path(p['path'])==original),None)
            approval_path = EVIDENCE/'correction-approval.json'
            approval = json.loads(approval_path.read_text()) if approval_path.exists() else None
            report_path = EVIDENCE/'report-continuation-approval.json'
            report_approval = json.loads(report_path.read_text()) if report_path.exists() else None
            supplier_path = EVIDENCE/'supplier-continuation-approval.json'
            supplier_approval = json.loads(supplier_path.read_text()) if supplier_path.exists() else None
            approved_variant = validate_source(raw, original.read_bytes(), pin,
                original.relative_to(CANONICAL).as_posix(), approval, report_approval, supplier_approval)
            encoding = 'utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'cp1252'
            sql = raw.decode(encoding)
            source = str(original)
            i += 2
            continue
        if key.lower() == '-q':
            sql = argv[i+1]
            source = 'canonical-batch-inline-query'
            i += 2
            continue
        if key.lower() == '-d':
            database = argv[i+1].strip('"')
            i += 2
            continue
        if key == '-S':
            if argv[i+1].lower() not in ('localhost','.'):
                raise ValueError('Unexpected SQL server')
            i += 2
            continue
        if key.lower() == '-o':
            output = Path(argv[i+1].strip('"')).resolve()
            if not output.is_relative_to(EVIDENCE.resolve()):
                raise ValueError('Native output outside owner directory')
            passthrough += [key,str(output)]
            i += 2
            continue
        if key in ('-U','-P'):
            raise ValueError('No alternate SQL credential allowed')
        passthrough.append(key)
        i += 1
    if database not in isolation.MAPPING.values() or sql is None:
        raise ValueError('Explicit owned SQL database and source required')
    raw_sha = hashlib.sha256(sql.encode('utf-8')).hexdigest()
    names = {**variables,
        'scriptExecutionFlagQuery'.lower():'update A set A.IsScriptExecuted=1 from '+isolation.MAPPING['VFTEST_Importer']+'.dbo.ScriptExecutedFlag A where ScriptName='}
    def substitute(match):
        if match[1].lower() not in names:
            raise ValueError('Unbound SQLCMD variable: '+match[1])
        return names[match[1].lower()]
    sql = re.sub(r'\$\(([^)]+)\)',substitute,sql)
    aliases = {'Demo_Importer_1':'Importer','Demo_BPR_1':'BPR','Demo_DBM_1':'DBM','Demo_BTR_1':'BTR',
        'Demo_Interface_1':'Interface','Gulf_Oil_Interface':'Interface','Demo_IntermediateDB_1':'Intermediate'}
    for alias,role in aliases.items():
        sql = re.sub(r'\b'+re.escape(alias)+r'\b',isolation.MAPPING['VFTEST_'+role],sql,flags=re.I)
    sql = isolation.bind_sql(sql)
    count_query = source=='canonical-batch-inline-query' and bool(re.match(r'^\s*EXIT\s*\(',sql,re.I))
    # GO ends the impersonation statement, retaining WITH NO REVERT for all
    # subsequent native batches/transactions/RETURN and SQLCMD EXIT processing.
    bound = "EXECUTE AS LOGIN='"+isolation.PRINCIPAL+"' WITH NO REVERT;\nGO\n"+sql
    directory = EVIDENCE/'sql'
    directory.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8-sig',suffix='.sql',dir=directory,delete=False) as stream:
        stream.write(bound)
        sql_path = Path(stream.name)
    started = time.perf_counter()
    proc = subprocess.run([str(SQLCMD),'-S','localhost','-d',database,'-b','-i',str(sql_path),*passthrough],
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    text = decode_output(proc.stdout)
    sys.stdout.buffer.write(proc.stdout)
    sys.stdout.buffer.flush()
    report_bytes = output.read_bytes() if output and output.exists() else b''
    report = decode_output(report_bytes)
    caught = bool(re.search(r'(?im)^\s*(?:Msg \d+, Level|Sqlcmd: Error|ERROR\s+ErrorNumber|ErrorNumber\s+ErrorSeverity)',text+'\n'+report))
    failed = caught or (proc.returncode!=0 and not count_query)
    receipt = dict(source=source,source_text_sha256=raw_sha,bound_sha256=hashlib.sha256(bound.encode()).hexdigest(),
        bound_file=str(sql_path),database=database,seconds=time.perf_counter()-started,
        exit_code=proc.returncode,count_query=count_query,failed=failed,
        output=str(output) if output else None,
        approved_calculation_variant=approved_variant,
        baseline_kind='CORRECTED_LEGACY' if (EVIDENCE/'correction-approval.json').exists() else 'UNCHANGED_LEGACY')
    with (EVIDENCE/'sql-calls.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(receipt)+'\n')
    if failed:
        failure.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        return 1
    return proc.returncode


if __name__=='__main__':
    try:
        code = execute(sys.argv[1:])
    except Exception as error:
        path = EVIDENCE/'day-failure.json'
        if not path.exists():
            path.write_text(json.dumps(dict(error=type(error).__name__,message=str(error)),indent=2),encoding='utf-8')
        print(type(error).__name__+': '+str(error),file=sys.stderr)
        code = 1
    sys.exit(code)
