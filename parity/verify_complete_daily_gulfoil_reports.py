"""Finite AST-isolated canonical pandas transformation proof; no SQL/day runs.

Only three retained function definitions execute. Joined SELECT rows are supplied
fixtures; SQL joins and diagnostic queries/text files are outside this proof.
"""
import argparse
import ast
from contextlib import redirect_stdout
from datetime import datetime, timedelta
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from mta.application import complete_daily_gulfoil_reports as modern

SOURCE=Path('F:/VFlow_Local/local-runtime/mta-engine')/modern.SOURCE[0]
OWNER='fdc5bc5e-4d68-4b3a-b8e6-d2754df0e2f4'
OUTPUT_ROOT=Path('D:/freshvcf-build/complete-daily-assessment')
INTERPRETER=Path('C:/Program Files/Python313/python.exe')
TEMP_ROOT=OUTPUT_ROOT/'gulfoil-transform'
FUNCTIONS=('calculate_age','calculate_color_counts','generate_report')
FILES=('mta/application/complete_daily_gulfoil_reports.py',
       'parity/verify_complete_daily_gulfoil_reports.py')


def code_pins():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES}


def extract_functions():
    content=SOURCE.read_bytes()
    if hashlib.sha256(content).hexdigest()!=modern.SOURCE[1]:
        raise ValueError('Pinned canonical GulfOil Python source drift')
    tree=ast.parse(content.decode('utf-8-sig'),filename=str(SOURCE))
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in FUNCTIONS]
    if tuple(node.name for node in selected)!=FUNCTIONS or any(node.decorator_list for node in selected):
        raise ValueError('Canonical function roster/decorators differ')
    # No imports, constructor, DB connection, top-level main or close survives.
    isolated=ast.Module(body=selected,type_ignores=[])
    return compile(ast.fix_missing_locations(isolated),str(SOURCE),'exec'), [dict(
        name=node.name,start=node.lineno,end=node.end_lineno) for node in selected]


def guard_options(owner,output):
    if owner!=OWNER:
        raise ValueError('Only approved owned transform proof permitted')
    output=Path(output).resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()) or output.suffix!='.json':
        raise ValueError('Owned JSON evidence path required')
    if output.exists():
        raise FileExistsError('Refusing to overwrite transform evidence')
    return output


def fixtures(today):
    def row(days=0,**changes):
        values={key:key for key in modern.STATIC}
        values.update(SKUCode='S',WHCode='W',Norm=7,RLT=4,VirtualNorm=3,
            ReportDate=datetime.combine(today,datetime.min.time())-timedelta(days=days),
            **{key:'Black' for key in modern.PIVOTS.values()})
        values.update(changes)
        return values
    mixed=[row(100,SKUCode='OUTSIDE',VirtualNorm=None),
        row(31,TechColor='Red',EcoColor='Red',PhysicalInventoryColor='Red',DispatchColor='Red'),
        row(29,SKUCode='COUNT',TechColor='Green',EcoColor='Yellow'),
        row(31,SKUCode='AGE',TechColor='Red',EcoColor='Red',PhysicalInventoryColor='Red',DispatchColor='Red'),
        row(1,Norm=5),
        row(Norm=8,WhName='quote " edge',ParentWhName='comma,new\nline',TechColor=None,EcoColor=None),
        row(Norm=9,WhName='ignored tie',TechColor='Red',EcoColor='Blue'),
        row(SKUCode='NULL',**{key:None for key in modern.PIVOTS.values()}),
        row(SKUCode='GREY',Norm=0,VirtualNorm=0),
        row(SKUCode='VIRTUAL',Norm=0,VirtualNorm=3),
        row(SKUCode='NULLVIRTUAL',VirtualNorm=None),
        row(SKUCode='AGE')]
    # Python's stable ordering retains declared exact-date tie sequence.
    mixed.sort(key=lambda r:r['ReportDate'])
    return [('mixed',mixed),('outside-window',[row(100)]),('empty',[]),
            ('target-present',[row(SKUCode=modern.TARGET[0],WHCode=modern.TARGET[1])])]


def typed_cell(value,pd):
    if value is None:
        return dict(type='NoneType',value=None)
    if pd.isna(value):
        return dict(type=type(value).__name__,value=None,native_missing=True)
    if isinstance(value,datetime):
        return dict(type=type(value).__name__,value=value.isoformat())
    if isinstance(value,float):
        return dict(type=type(value).__name__,value=value.hex())
    return dict(type=type(value).__name__,value=value)


def compare_case(code,pd,folder,today,name,rows,report_type):
    virtual=report_type in ('BTR_OnHand','BTR_Pipeline')
    fields=[*modern.STATIC,*modern.PIVOTS.values(),'ReportDate']
    if virtual:
        fields.insert(6,'VirtualNorm')
    inputs=[{field:row[field] for field in fields} for row in rows]
    source_frame=pd.DataFrame(inputs,columns=fields)
    queries=[]; diagnostics=[]; captures=[]
    class FakeDB:
        def fetch_dataframe(self,query):
            queries.append(query)
            return source_frame.copy(deep=True)
    zip_path=folder/(report_type+'.zip')
    zip_path.write_bytes(b'preexisting-zip-sentinel')
    ns=dict(pd=pd,zipfile=zipfile,DBConnBTR=FakeDB(),ImporterDatabaseName='DECLARED_OWNED_IMPORTER',
        ReportsDownloadLocation=str(folder),check_missing_entry=lambda sku,wh:diagnostics.append([sku,wh]))
    exec(code,ns)
    # Capture the *actual* final frame at pandas CSV conversion, while still
    # calling the original implementation and preserving real ZIP writing.
    original=pd.DataFrame.to_csv
    def record_csv(frame,*args,**kwargs):
        captures.append(frame.copy(deep=True))
        return original(frame,*args,**kwargs)
    pd.DataFrame.to_csv=record_csv
    console=StringIO()
    try:
        with redirect_stdout(console):
            ns['generate_report'](report_type)
    finally:
        pd.DataFrame.to_csv=original
    expected=modern.transform(inputs,report_type,host_today=today)
    result=dict(name=name,report_type=report_type,status='STARTED',
        inputs=[[typed_cell(row[field],pd) for field in fields] for row in inputs],input_fields=fields,
        source_dataframe_dtypes={key:str(value) for key,value in source_frame.dtypes.items()},
        captured_sql=queries,diagnostic_calls=diagnostics,console=console.getvalue(),
        modern_action=expected['action'],modern_columns=expected['columns'],
        modern_rows=[[typed_cell(row[field],pd) for field in expected['columns']] for row in expected['rows']])
    wanted_diagnostic=[list(modern.TARGET)] if expected['diagnostic_required'] else []
    if diagnostics!=wanted_diagnostic or len(queries)!=1:
        result.update(status='FAIL',failure='Diagnostic trigger/query invocation mismatch')
        return result
    if expected['action']=='PRESERVE_EXISTING':
        result['native_archive_sha256']=hashlib.sha256(zip_path.read_bytes()).hexdigest()
        if zip_path.read_bytes()!=b'preexisting-zip-sentinel' or captures:
            result.update(status='FAIL',failure='Canonical early return did not preserve original ZIP')
            return result
        result['status']='PASS'
        return result
    if len(captures)!=1 or not zipfile.is_zipfile(zip_path):
        result.update(status='FAIL',failure='Canonical did not generate exactly one final frame/ZIP')
        return result
    frame=captures[0]
    result['native_columns']=list(frame.columns)
    native_rows=frame.to_dict('records')
    result['native_rows']=[[typed_cell(row[field],pd) for field in frame.columns] for row in native_rows]
    # pandas missing values encode SQL NULL colors as NaN/None. This explicit
    # translation applies only missing cells; raw native typed cells remain.
    normalized=[{key:None if pd.isna(value) else value for key,value in row.items()} for row in native_rows]
    result['native_dataframe_dtypes']={key:str(value) for key,value in frame.dtypes.items()}
    with zipfile.ZipFile(zip_path) as archive:
        result['native_members']=archive.namelist()
        native_csv=archive.read(report_type+'.csv')
    expected_csv=modern.csv_bytes(expected,line_ending=os.linesep)
    result.update(native_csv=native_csv.decode('utf-8'),modern_csv=expected_csv.decode('utf-8'),
        native_csv_sha256=hashlib.sha256(native_csv).hexdigest(),
        modern_csv_sha256=hashlib.sha256(expected_csv).hexdigest())
    if (list(frame.columns)!=expected['columns'] or normalized!=expected['rows']
            or result['native_members']!=[report_type+'.csv'] or native_csv!=expected_csv):
        result['status']='FAIL'
        result['failure']='Canonical transform/full CSV bytes mismatch'
    else:
        result['status']='PASS'
    return result


def run(owner,output):
    output=guard_options(owner,output)
    code,functions=extract_functions()
    if Path(sys.executable).resolve()!=INTERPRETER.resolve():
        raise ValueError('Transform proof requires actual canonical Python313 interpreter')
    import pandas as pd
    import numpy as np
    today=pd.Timestamp.today().normalize().date()
    receipt=dict(owner=owner,status='STARTED',source_path=str(SOURCE),source_sha256=modern.SOURCE[1],
        implementation_pins=code_pins(),functions=functions,host_today=today.isoformat(),
        environment=dict(interpreter=sys.executable,python=platform.python_version(),
            pandas=pd.__version__,numpy=np.__version__,pandas_module=pd.__file__,numpy_module=np.__file__,
            native_line_ending=repr(os.linesep)),cases=[],
        scope='finite injected joined-population transform and exact CSV/ZIP member proof; zero SQL/business days',
        limitations=['SQL joins/source ordering qualification and actual diagnostic queries/text file outside proof',
            'diagnostic trigger recorded only; no canonical top-level DBConnect/main/import execution',
            'actual host today retained; no clock patch or frozen business-date substitution',
            'NULL/NaN translation explicitly limited to pandas missing cells; raw typed cells retained'])
    output.parent.mkdir(parents=True,exist_ok=True)
    TEMP_ROOT.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as file:
        try:
            with tempfile.TemporaryDirectory(prefix='proof-',dir=TEMP_ROOT) as directory:
                receipt['owned_temp_directory']=directory
                for name,rows in fixtures(today):
                    for report in modern.PIVOTS:
                        folder=Path(directory)/name/report
                        folder.mkdir(parents=True)
                        try:
                            case=compare_case(code,pd,folder,today,name,rows,report)
                        except Exception as error:
                            case=dict(name=name,report_type=report,status='FAIL',
                                failure_type=type(error).__name__,failure=str(error))
                        receipt['cases'].append(case)
                        if case['status']!='PASS':
                            raise ValueError('Stopped at first transform mismatch: '+name+'/'+report)
            if pd.Timestamp.today().normalize().date()!=today:
                raise ValueError('Host date changed during transform proof')
            receipt['status']='PASS'
        except Exception as error:
            receipt.update(status='FAIL',failure_type=type(error).__name__,failure=str(error))
        finally:
            receipt['implementation_identity_unchanged']=receipt['implementation_pins']==code_pins()
            receipt['source_identity_unchanged']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()==modern.SOURCE[1]
            if not receipt['implementation_identity_unchanged'] or not receipt['source_identity_unchanged']:
                receipt.update(status='FAIL',failure='Source/implementation drift')
            json.dump(receipt,file,indent=2,allow_nan=False);file.write('\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--output',required=True,type=Path)
    options=parser.parse_args()
    result=run(options.owner,options.output)
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),output=str(options.output))))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
