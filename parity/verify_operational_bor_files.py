"""Native SQLCMD BOR bytes on explicit report-component fixtures, rollback only."""
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from mta.application import operational_bor as bor
from mta.application.operational_sqlcmd import bor_report_bytes
from mta.domain.complete_daily_scalars import ascii_equal
from mta.serialization import storage
from parity.verify_operational_bor import BorFixtureSQL, cases, EVIDENCE, strict_rows
from parity.verify_operational_upload_files import SQLCMD, _insert, _diff, pin
from parity.verify_complete_daily_pick_files import prepare
from parity.verify_complete_daily_producers import OWNER, SOURCE, native_context
from parity.adapters.legacy.complete_daily_sql import namespace

TABLES=('BORWithOrderAllocation','ColorSequence','SKUDescriptionTbl','SiteDescriptionTbl','vf_ReqCalculation')
CODE=('parity/verify_operational_bor_files.py','parity/verify_operational_bor.py',
      'parity/verify_operational_upload_files.py','parity/verify_complete_daily_producers.py',
      'parity/verify_complete_daily_pick_files.py','parity/legacy_isolation.py',
      'mta/application/operational_bor.py','mta/application/operational_sqlcmd.py')


def complete_fixture(sql,table,rows):
    columns=[]
    native=[col for col in sql.schema('BPR',table) if not col['identity'] and not col['computed']]
    for col in native:
        kind=col['type_name']
        parameters=(str(col['max_length']//2) if kind in ('nvarchar','nchar') else
                    str(col['max_length']) if kind in ('varchar','char') else
                    str(col['precision'])+','+str(col['scale']) if kind in ('decimal','numeric') else None)
        columns.append(dict(name=col['name'],type=kind,parameters=parameters,nullable=bool(col['nullable'])))
    expanded=[]
    for ordinal,row in enumerate(rows):
        by_name={key.casefold():value for key,value in row.items()}
        if not set(by_name) <= {col['name'].casefold() for col in native}:
            raise ValueError('Unexpected report fixture field')
        current={}
        for col in native:
            if col['name'].casefold() in by_name:
                value=by_name[col['name'].casefold()]
            else:
                value,reason=sql.fill(col)
                sql.fills.append(dict(table=table,ordinal=ordinal,field=col['name'],value=storage(value),reason=reason))
            if isinstance(value,Decimal):
                value=value.quantize(Decimal(1).scaleb(-col['scale']))
            current[col['name']]=value
        expanded.append(current)
    return columns,expanded


def run(owner,output):
    output=Path(output).resolve()
    if owner!=OWNER or not output.is_relative_to(EVIDENCE.resolve()) or output.suffix!='.json' or output.exists():
        raise ValueError('Exact owned evidence path and SQL owner required')
    from parity import legacy_isolation as isolation
    _,setup=prepare(owner,isolation)
    os.environ['VFTEST_PROFILE']='fresh'
    path,expected=bor.SOURCES['report']; source=SOURCE/path
    if pin(source)!=expected:
        raise ValueError('Canonical BOR export changed')
    code={name:pin(ROOT/name) for name in CODE}; tool=pin(SQLCMD)
    directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    receipt=dict(status='STARTED',setup=setup,owner=owner,namespace=namespace(owner),
        source_sha256=expected,tool_sha256=tool,code_pins=code,cases=[],
        scope='report-only explicit input fixtures; pure BOR outputs are fixture facts here, not SQL calculation parity')
    with output.open('x',encoding='utf-8') as stream:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                with isolation.connection('VFTEST_BPR') as raw:
                    receipt['native_context']=native_context(raw,isolation)
                    sql=BorFixtureSQL(raw,isolation)
                    originals={table:sql.rows('BPR',table) for table in TABLES}
                    for name,inputs,report,*_ in cases():
                        rows=bor.collect_bor_order_allocation(**inputs,equal=ascii_equal)
                        modern=bor_report_bytes(bor.generate_bor_order_allocation(bor_rows=rows,**report,equal=ascii_equal))
                        populations=dict(BORWithOrderAllocation=rows,ColorSequence=report['color_sequence'],
                            SKUDescriptionTbl=report['sku_descriptions'],SiteDescriptionTbl=report['site_descriptions'],
                            vf_ReqCalculation=report['requirement_rows'])
                        native_path=directory/(name+'.native.csv')
                        statements=[':setvar IsMTOEnvironment "0"',
                            "EXECUTE AS LOGIN = '"+isolation.PRINCIPAL+"' WITH NO REVERT;",
                            'SET XACT_ABORT ON;','BEGIN TRANSACTION;']
                        expanded={}
                        for table in TABLES:
                            columns,full_rows=complete_fixture(sql,table,populations[table])
                            expanded[table]=full_rows
                            statements.extend(_insert(table,columns,full_rows))
                        statements.extend(['GO',':out "'+str(native_path)+'"',':r "'+str(source)+'"',
                            'GO',':out stdout',"IF @@TRANCOUNT<>1 THROW 51000,'BOR fixture transaction changed',1;",
                            'ROLLBACK TRANSACTION;',"IF @@TRANCOUNT<>0 THROW 51000,'BOR rollback failed',1;"])
                        script=directory/(name+'.sql');script.write_text('\n'.join(statements)+'\n',encoding='utf-8')
                        command=[str(SQLCMD),'-C','-E','-S','localhost','-d',namespace(owner)['VFTEST_BPR'],
                            '-b','-r','1','-f','i:65001','-i',str(script),'-h-1','-W','-s',',']
                        result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,timeout=60,check=False)
                        native=native_path.read_bytes() if native_path.exists() else b''
                        item=dict(name=name,status='PASS' if result.returncode==0 and native==modern else 'FAIL',
                            fixture=storage(expanded),script_sha256=pin(script),returncode=result.returncode,
                            stdout_hex=result.stdout.hex(),stderr_hex=result.stderr.hex(),
                            native_sha256=hashlib.sha256(native).hexdigest(),modern_sha256=hashlib.sha256(modern).hexdigest(),
                            native_size=len(native),modern_size=len(modern))
                        receipt['cases'].append(item)
                        (directory/(name+'.modern.csv')).write_bytes(modern)
                        if item['status']!='PASS':item['strict_diff']=_diff(directory,name,native,modern)
                        preservation={table:strict_rows(sql,('BPR',table),prior) for table,prior in originals.items()}
                        item['preservation']=preservation
                        if any(check['status']!='PASS' for check in preservation.values()):
                            raise ValueError('BOR export fixture rollback preservation failed')
                    receipt['filler_policy']=sql.fills
            receipt['status']='PASS' if all(case['status']=='PASS' for case in receipt['cases']) else 'FAIL'
        except Exception as error:
            receipt.update(status='FAIL',error=type(error).__name__+': '+str(error))
        finally:
            receipt['identities_unchanged']=(pin(source)==expected and pin(SQLCMD)==tool and
                code=={name:pin(ROOT/name) for name in CODE})
            if not receipt['identities_unchanged']:receipt.update(status='FAIL',error='Source/tool/code changed')
            json.dump(storage(receipt),stream,indent=2,ensure_ascii=False,allow_nan=False)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',required=True);parser.add_argument('--output',required=True)
    options=parser.parse_args(); result=run(options.owner,options.output)
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),error=result.get('error'))))
    raise SystemExit(result['status']!='PASS')
