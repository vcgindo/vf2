"""Required O2/O3/O6 native file proof: six mapped exports, empty/populated only."""
import argparse
from copy import deepcopy
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from mta.application.operational_exceptions import SOURCES as EXCEPTION_SOURCES, bpr_exception_resultsets, no_norm_at_parent_rows
from mta.application.operational_norm_reports import SOURCES as NORM_SOURCES, NORM_HEADER, REQUIRED_CONFIGURATION, norm_report_resultsets
from mta.application.operational_sqlcmd import resultset_bytes,no_norm_parent_bytes,norm_report_bytes
from mta.domain.complete_daily_scalars import ascii_equal
from mta.domain.dbm_norm_change_report import norm_change_report
from mta.domain.dbm_norm_change_history import norm_change_history
from mta.domain.dbm_norm012 import export_stage
from mta.serialization import storage
from tests.test_operational_exceptions import processed
from parity.verify_operational_alert_files import expand
from parity.verify_operational_upload_files import SQLCMD,_insert,_diff,pin
from parity.verify_operational_bor import BorFixtureSQL,strict_rows,EVIDENCE
from parity.verify_complete_daily_pick_files import prepare
from parity.verify_complete_daily_producers import OWNER,SOURCE,native_context
from parity.adapters.legacy.complete_daily_sql import namespace

SOURCES=dict(bpr=EXCEPTION_SOURCES['bpr_export'],parent=EXCEPTION_SOURCES['parent_norm'],
    change=NORM_SOURCES['dbm_sql'],history=NORM_SOURCES['history_sql'],norm=NORM_SOURCES['norm_export'])
CODE=('parity/verify_operational_remaining_files.py','parity/verify_operational_alert_files.py',
    'mta/application/operational_exceptions.py','mta/application/operational_norm_reports.py',
    'mta/application/operational_sqlcmd.py','mta/domain/dbm_norm_change_report.py',
    'mta/domain/dbm_norm_change_history.py','mta/domain/dbm_norm012.py',
    'parity/verify_operational_upload_files.py','parity/verify_operational_bor.py',
    'parity/verify_complete_daily_pick_files.py','parity/verify_complete_daily_producers.py',
    'parity/legacy_isolation.py')


def fixtures():
    for empty in (True,False):
        suffix='empty' if empty else 'populated'
        exceptions=[] if empty else [dict(SKUCode='S',WhCode='W',Norm=None,Stock=None,GIT=4)]*2
        skus=[dict(SKUCode='S',SKUDescription='Some, café')]*2
        sites=[]
        projection=bpr_exception_resultsets(exceptions=exceptions,sku_descriptions=skus,site_descriptions=sites,equal=ascii_equal)
        yield dict(name='bpr-'+suffix,kind='bpr',role='BPR',variables={},
            tables={('BPR','BPRExceptions'):exceptions,('BPR','SKUDescriptionTbl'):skus,
                    ('BPR','SiteDescriptionTbl'):sites},modern=resultset_bytes(projection))
        master=[] if empty else [processed(),processed(),processed(WhCode='P',Norm=0,ParentWhCode='P')]
        parent=no_norm_at_parent_rows(master_data=master,phase_out=[],equal=ascii_equal)
        yield dict(name='parent-'+suffix,kind='parent',role='Importer',variables={},
            tables={('Importer','MasterData'):master,('DBM','PhaseOutTbl'):[],
                ('Importer','ScriptExecutedFlag'):[dict(ScriptName='ValidationForParentNorm.sql',
                    ModuleName='Importer',IsScriptExecuted=False,IsScriptCritical=True)]},modern=no_norm_parent_bytes(parent))
        logs=[] if empty else [dict(SKUCode='S',WHCode='W',OldNorm=1,NewNorm=2,
            NormChangeDate='2026-06-06',NormChangeReason=4)]*2+[
            dict(SKUCode='X',WHCode='Q',OldNorm=2,NewNorm=3,NormChangeDate='2026-05-31',NormChangeReason=100),
            dict(SKUCode='S',WHCode='W',OldNorm=3,NewNorm=4,NormChangeDate='2026-05-30',NormChangeReason=4)]
        state=dict(LastBatchRunTbl=[dict(LastRunDate='2026-06-06T00:00:00')],NormChangeLogTbl=logs,
            ReasonCodes=[dict(Id=4,Reason='Reason, café')],SKUDescriptionTbl=skus,
            SiteDescriptionTbl=[dict(WHCode='W',WHDescription='Site, west')])
        selected=['SKUCode','SKUName','WHCode','WhName','ParentWhCode','ParentNorm','NumOfDaysSold','TotalSale','Occurances']
        config=[dict(ReportName='Norm_0_1_2Report',Col_Code=column,Header=header,Col_Position=i,Visible=True)
                for i,(column,header) in enumerate(zip(selected,NORM_HEADER),1)]
        details=[] if empty else [dict(SKUCode='S',SKUName='Some, "café"',WhCode='W',WhName=None,
            ParentWhCode=None,ParentNorm=12,NumOfDaysSold=2,TotalSale=3,Occurances='[01/06/26 - 3]')]*2
        exported=export_stage(dict(ui_ReportConfigurations=config,Norm0_1_2ReportDetails=details))
        outputs=[dict(stage='norm-change-export',tables=norm_change_report('2026-06-06',state,1)),
                 dict(stage='norm-change-history',tables=norm_change_history('2026-06-06',state,7)),
                 dict(stage='norm1-export',tables=exported),dict(stage='norm2-export',tables=exported)]
        reports=norm_report_resultsets(reports=outputs,configuration=REQUIRED_CONFIGURATION)
        for kind,key in (('change','DBMNormChange'),('history','NormChangeLog')):
            yield dict(name=kind+'-'+suffix,kind=kind,role='DBM',variables={},
                tables={('DBM',name):rows for name,rows in state.items()},modern=norm_report_bytes(reports[key]))
        for number in (1,2):
            yield dict(name=f'norm{number}-'+suffix,kind='norm',role='DBM',variables={'ReportName':str(number)},
                tables={('DBM','Norm0_1_2ReportDetails'):details,('BPR','ui_ReportConfigurations'):config},
                modern=norm_report_bytes(reports[f'Norm{number}_30days']))


def run(owner,output):
    output=Path(output).resolve()
    if owner!=OWNER or not output.is_relative_to(EVIDENCE.resolve()) or output.exists() or output.suffix!='.json':
        raise ValueError('Exact owned new evidence path and owner required')
    from parity import legacy_isolation as isolation
    _,setup=prepare(owner,isolation);os.environ['VFTEST_PROFILE']='fresh'
    mapping=namespace(owner)
    sources={key:SOURCE/path for key,(path,_) in SOURCES.items()}
    if any(pin(sources[key])!=sha for key,(_,sha) in SOURCES.items()):raise ValueError('Mapped file source differs')
    code={name:pin(ROOT/name) for name in CODE};tool=pin(SQLCMD)
    directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    receipt=dict(status='STARTED',owner=owner,setup=setup,code_pins=code,source_pins=SOURCES,
                 tool_sha256=tool,scope='12 required component exports; no day/engine or ordering qualification',cases=[])
    with output.open('x',encoding='utf-8') as stream:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                with isolation.connection('VFTEST_Importer') as raw:
                    receipt['native_context']=native_context(raw,isolation)
                    sql=BorFixtureSQL(raw,isolation);cases=list(fixtures())
                    touched={key for case in cases for key in case['tables']}
                    originals={key:sql.rows(*key) for key in touched}
                    scratch=sql.scratch()
                    expanded={case['name']:{key:expand(sql,*key,rows) for key,rows in case['tables'].items()} for case in cases}
                    for case in cases:
                        name=case['name'];native_path=directory/(name+'.native.csv')
                        variables=dict(IntermediateDatabase=mapping['VFTEST_Intermediate'],DBMDataBase=mapping['VFTEST_DBM'],
                            BPRDatabase=mapping['VFTEST_BPR'],DBMNormChangeReportHorizon='1',NormChangeLogHorizon='7',
                            ScriptExecutionFlagQuery='UPDATE '+mapping['VFTEST_Importer']+
                                '.dbo.ScriptExecutedFlag SET IsScriptExecuted=1 WHERE ScriptName=',**case['variables'])
                        statements=[':setvar '+key+' "'+value+'"' for key,value in variables.items()]
                        statements += ["EXECUTE AS LOGIN = '"+isolation.PRINCIPAL+"' WITH NO REVERT;",
                            'SET XACT_ABORT ON;','BEGIN TRANSACTION;']
                        for (role,table),(columns,rows) in expanded[name].items():
                            statements += ['USE ['+mapping['VFTEST_'+role]+'];',*_insert(table,columns,rows)]
                        statements += ['USE ['+mapping['VFTEST_'+case['role']]+'];','GO',':out "'+str(native_path)+'"',
                            ':r "'+str(sources[case['kind']])+'"','GO',':out stdout',
                            "IF @@TRANCOUNT<>1 THROW 51000,'File fixture transaction changed',1;",'ROLLBACK TRANSACTION;',
                            "IF @@TRANCOUNT<>0 THROW 51000,'File fixture rollback failed',1;"]
                        script=directory/(name+'.sql');script.write_text('\n'.join(statements)+'\n',encoding='utf-8')
                        command=[str(SQLCMD),'-C','-E','-S','localhost','-d',mapping['VFTEST_'+case['role']],
                            '-b','-r','1','-f','i:65001','-i',str(script),'-s',',','-W']
                        if case['kind']!='parent':command+=['-h-1']
                        result=subprocess.run(command,capture_output=True,timeout=90)
                        native=native_path.read_bytes() if native_path.exists() else b'';modern=case['modern']
                        item=dict(name=name,status='PASS' if result.returncode==0 and native==modern else 'FAIL',
                            returncode=result.returncode,stderr_hex=result.stderr.hex(),native_size=len(native),modern_size=len(modern),
                            native_sha256=hashlib.sha256(native).hexdigest(),modern_sha256=hashlib.sha256(modern).hexdigest())
                        receipt['cases'].append(item);(directory/(name+'.modern.csv')).write_bytes(modern)
                        if item['status']!='PASS':item['strict_diff']=_diff(directory,name,native,modern)
                        item['preservation']={role+'/'+table:strict_rows(sql,(role,table),rows) for (role,table),rows in originals.items()}
                        item['scratch_preservation']={table:strict_rows(sql,('Intermediate',table),rows) for table,rows in scratch.items()}
                        if any(v['status']!='PASS' for v in (*item['preservation'].values(),*item['scratch_preservation'].values())):
                            raise ValueError('Native file fixture preservation failed')
                        if item['status']!='PASS':raise ValueError('First native file mismatch: '+name)
                    receipt['filler_policy']=sql.fills
            receipt['status']='PASS' if len(receipt['cases'])==12 and all(c['status']=='PASS' for c in receipt['cases']) else 'FAIL'
        except Exception as error:receipt.update(status='FAIL',error=type(error).__name__+': '+str(error))
        finally:
            receipt['identities_unchanged']=code=={name:pin(ROOT/name) for name in CODE} and pin(SQLCMD)==tool and all(pin(sources[k])==v for k,(_,v) in SOURCES.items())
            if not receipt['identities_unchanged']:receipt['status']='FAIL'
            json.dump(storage(receipt),stream,indent=2,ensure_ascii=False)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--owner',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();result=run(args.owner,args.output)
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),error=result.get('error'))))
    raise SystemExit(result['status']!='PASS')
