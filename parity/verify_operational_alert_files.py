"""Eight exact native attachment exports; owned rollback fixtures, never an engine run."""
import argparse
from datetime import date,datetime
from decimal import Decimal
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from mta.application.operational_alert_files import (
    SOURCES,invalid_data_bytes,unavailable_daily_bytes,phase_exception_bytes,failed_force_bytes,
)
from mta.serialization import storage
from parity.verify_operational_upload_files import SQLCMD,_insert,_diff,pin
from parity.verify_operational_bor import BorFixtureSQL,strict_rows,EVIDENCE
from parity.verify_complete_daily_pick_files import prepare
from parity.verify_complete_daily_producers import OWNER,SOURCE,native_context
from parity.adapters.legacy.complete_daily_sql import namespace

CLOCK='2026-06-06T00:00:00'
CODE=('parity/verify_operational_alert_files.py','mta/application/operational_alert_files.py',
      'mta/application/operational_sqlcmd.py','parity/verify_operational_upload_files.py',
      'parity/verify_operational_bor.py','parity/verify_complete_daily_producers.py',
      'parity/verify_complete_daily_pick_files.py','parity/legacy_isolation.py')


def fixtures():
    rejected=[dict(SKUCode='A',WhCode='W',RejectionDate=CLOCK,ReasonCode=3,ReasonDescription='bad, café  ')]*2
    rejected+=[dict(SKUCode='B',WhCode='W',RejectionDate=CLOCK,ReasonCode=0,ReasonDescription=None),
        dict(SKUCode='C',WhCode='W',RejectionDate='2026-06-05T00:00:00',ReasonCode=8,ReasonDescription='old')]
    reasons=[dict(FileId=1,RunDateTime=CLOCK,Reason='file, missing')]*2
    reasons+=[dict(FileId=2,RunDateTime=CLOCK,Reason='R'*300),
        dict(FileId=3,RunDateTime='2026-06-05T00:00:00',Reason='old')]
    phase=[dict(PhaseOutSKUCode='A',WhCode='W',PhaseInSKUCode=None,TargetNorm=None,Reason='reason, café',Log_Date=CLOCK)]*2
    phase+=[dict(PhaseOutSKUCode='B',WhCode='W',PhaseInSKUCode='C',TargetNorm=2147483647,Reason='positive',Log_Date=CLOCK)]
    phase_report=[dict(PhaseOutSKUCode=r['PhaseOutSKUCode'],WhCode=r['WhCode'],PhaseInSKUCode=r['PhaseInSKUCode'] or '',
        TargetNorm='' if r['TargetNorm'] is None else str(r['TargetNorm']),Reason=r['Reason'],Date=r['Log_Date']) for r in phase]
    force=[dict(SKUCode='A',WHCode='W',Reason='first  ')]*2+[dict(SKUCode='B',WHCode='W',Reason='last, café')]
    master=[dict(SKUCode='A',WhCode='W',Norm=12)]
    force_report=[dict(SKUCode=r['SKUCode'],WhCode=r['WHCode'],VectorFlowNorm='12' if r['SKUCode']=='A' else 'NA',Reason=r['Reason']) for r in force]
    for empty in (False,True):
        suffix='empty' if empty else 'populated'
        yield 'invalid-'+suffix,'invalid','Importer',{'RejectedMaster':[] if empty else rejected},invalid_data_bytes([] if empty else rejected,CLOCK)
        yield 'unavailable-'+suffix,'unavailable','Importer',{'RunAbortReasons':[] if empty else reasons},unavailable_daily_bytes([] if empty else reasons,CLOCK)
        yield 'phase-'+suffix,'phase','DBM',{'PhaseInPhaseOutExceptionLog':[] if empty else phase},phase_exception_bytes([] if empty else phase_report)
        yield 'force-'+suffix,'force','DBM',{'FailedForceNormChange':[] if empty else force,'DBMMaster':[] if empty else master},failed_force_bytes([] if empty else force_report)


def expand(sql,role,table,rows):
    columns=[c for c in sql.schema(role,table) if not c['identity'] and not c['computed']]
    result=[]
    for ordinal,row in enumerate(rows):
        if not set(row)<=set(c['name'] for c in columns):raise ValueError('Unknown declared fixture field')
        current={}
        for column in columns:
            name=column['name']
            if name in row:value=row[name]
            else:
                value,reason=sql.fill(column)
                sql.fills.append(dict(role=role,table=table,ordinal=ordinal,column=name,value=storage(value),reason=reason))
            if isinstance(value,(date,datetime)):value=value.isoformat()
            current[name]=value
        result.append(current)
    return [dict(name=c['name'],type=c['type_name']) for c in columns],result


def run(owner,output):
    output=Path(output).resolve()
    if owner!=OWNER or not output.is_relative_to(EVIDENCE.resolve()) or output.exists() or output.suffix!='.json':
        raise ValueError('Exact owned new evidence path and owner required')
    from parity import legacy_isolation as isolation
    _,setup=prepare(owner,isolation);os.environ['VFTEST_PROFILE']='fresh'
    sources={key:SOURCE/path for key,(path,_) in SOURCES.items()}
    if any(pin(sources[key])!=expected for key,(_,expected) in SOURCES.items()):raise ValueError('Attachment source changed')
    code={name:pin(ROOT/name) for name in CODE};tool=pin(SQLCMD)
    directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    receipt=dict(status='STARTED',owner=owner,setup=setup,code_pins=code,tool_sha256=tool,cases=[])
    with output.open('x',encoding='utf-8') as stream:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                with isolation.connection('VFTEST_Importer') as raw:
                    receipt['native_context']=native_context(raw,isolation)
                    sql=BorFixtureSQL(raw,isolation)
                    all_cases=list(fixtures())
                    touched={(role,table) for _,_,role,populations,_ in all_cases for table in populations}
                    originals={key:sql.rows(*key) for key in touched}
                    expanded={name:{table:expand(sql,role,table,rows) for table,rows in populations.items()}
                              for name,_,role,populations,_ in all_cases}
                    for name,kind,role,populations,modern in all_cases:
                        native_path=directory/(name+'.native.csv')
                        statements=[':setvar RunDateTime "'+CLOCK+'"',
                            "EXECUTE AS LOGIN = '"+isolation.PRINCIPAL+"' WITH NO REVERT;",
                            'SET XACT_ABORT ON;','BEGIN TRANSACTION;']
                        for table,(columns,rows) in expanded[name].items():statements.extend(_insert(table,columns,rows))
                        statements.extend(['GO',':out "'+str(native_path)+'"',':r "'+str(sources[kind])+'"','GO',':out stdout',
                            "IF @@TRANCOUNT<>1 THROW 51000,'Attachment fixture transaction changed',1;",'ROLLBACK TRANSACTION;',
                            "IF @@TRANCOUNT<>0 THROW 51000,'Attachment rollback failed',1;"])
                        script=directory/(name+'.sql');script.write_text('\n'.join(statements)+'\n',encoding='utf-8')
                        command=[str(SQLCMD),'-C','-E','-S','localhost','-d',namespace(owner)['VFTEST_'+role],
                            '-b','-r','1','-f','i:65001','-i',str(script),'-h-1','-s',',']
                        if kind!='force':command+=['-W']
                        result=subprocess.run(command,capture_output=True,timeout=90)
                        native=native_path.read_bytes() if native_path.exists() else b''
                        item=dict(name=name,status='PASS' if result.returncode==0 and native==modern else 'FAIL',
                            returncode=result.returncode,stderr_hex=result.stderr.hex(),native_size=len(native),modern_size=len(modern),
                            native_sha256=hashlib.sha256(native).hexdigest(),modern_sha256=hashlib.sha256(modern).hexdigest())
                        receipt['cases'].append(item);(directory/(name+'.modern.csv')).write_bytes(modern)
                        if item['status']!='PASS':item['strict_diff']=_diff(directory,name,native,modern)
                        item['preservation']={role+'/'+table:strict_rows(sql,(role,table),rows) for (role,table),rows in originals.items()}
                        if any(v['status']!='PASS' for v in item['preservation'].values()):raise ValueError('Native fixture preservation failed')
                    receipt['filler_policy']=sql.fills
            receipt['status']='PASS' if all(c['status']=='PASS' for c in receipt['cases']) else 'FAIL'
        except Exception as error:receipt.update(status='FAIL',error=type(error).__name__+': '+str(error))
        finally:
            receipt['identities_unchanged']=code=={name:pin(ROOT/name) for name in CODE} and pin(SQLCMD)==tool and all(pin(sources[k])==p for k,(_,p) in SOURCES.items())
            if not receipt['identities_unchanged']:receipt['status']='FAIL'
            json.dump(storage(receipt),stream,indent=2,ensure_ascii=False)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--owner',required=True);parser.add_argument('--output',required=True)
    options=parser.parse_args();result=run(options.owner,options.output)
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),error=result.get('error'))))
    raise SystemExit(result['status']!='PASS')
