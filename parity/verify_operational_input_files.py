"""Exact four-table native export byte proof on retained raw-feed fixtures."""
import argparse
from copy import deepcopy
from decimal import Decimal
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from mta.application.operational_inputs import PHYSICAL_TABLES, typed_value
from mta.application.operational_sqlcmd import input_table_bytes
from mta.application.operational_upload_logs import SCHEMA_SHA256
from mta.serialization import storage
from parity.verify_operational_bor import EVIDENCE, strict_rows
from parity.verify_operational_upload_files import SQLCMD, _insert, _diff, pin
from parity.verify_complete_daily_pick_files import prepare
from parity.verify_complete_daily_producers import OWNER, SOURCE, FixtureSQL, native_context
from parity.adapters.legacy.complete_daily_sql import namespace

SOURCE_PATH='Scripts/Importer/ExportInputTable.sql'
SOURCE_SHA='022e622c60b7dee6e1921a54fdf778c53a6334f5bc1d78c76b28e04892aeaf07'
INPUT=Path('D:/freshvcf-build/evidence/pick-closure-20261008-001/positive/input-v1.json')
INPUT_SHA='7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d'
CODE=('parity/verify_operational_input_files.py','parity/verify_operational_bor.py',
    'parity/verify_operational_upload_files.py','parity/verify_complete_daily_producers.py',
    'parity/verify_complete_daily_pick_files.py','parity/legacy_isolation.py',
    'mta/application/operational_inputs.py','mta/application/operational_sqlcmd.py')


def run(owner,output):
    output=Path(output).resolve()
    if owner!=OWNER or not output.is_relative_to(EVIDENCE.resolve()) or output.suffix!='.json' or output.exists():
        raise ValueError('Exact owned evidence path and SQL owner required')
    schema_path=ROOT/'baseline/cohort2-native-source-schema.json'
    if pin(schema_path)!=SCHEMA_SHA256 or pin(INPUT)!=INPUT_SHA or pin(SOURCE/SOURCE_PATH)!=SOURCE_SHA:
        raise ValueError('Pinned schema/input/export source differs')
    schema=json.loads(schema_path.read_bytes())['tables']
    case=json.loads(INPUT.read_bytes())['case']
    populations=dict(MasterDataRaw=case['static_day']['raw_master'],DailyDataRaw=case['days'][0]['raw_daily'],
        SOBDataRaw=case['static_day']['supplier_feeds']['SOBDataRaw'],
        MOQDataRaw1=case['static_day']['supplier_feeds']['MOQDataRaw1'])
    from parity import legacy_isolation as isolation
    _,setup=prepare(owner,isolation);os.environ['VFTEST_PROFILE']='fresh'
    database=namespace(owner)['VFTEST_Importer']
    code={name:pin(ROOT/name) for name in CODE};tool=pin(SQLCMD)
    directory=output.with_suffix('');directory.mkdir(exist_ok=False)
    receipt=dict(status='STARTED',owner=owner,setup=setup,namespace=namespace(owner),
        source_sha256=SOURCE_SHA,input_sha256=INPUT_SHA,schema_sha256=SCHEMA_SHA256,code_pins=code,
        tool_sha256=tool,scope='empty and retained raw-row export component fixtures; no stage-source or engine parity claim',cases=[])
    with output.open('x',encoding='utf-8') as stream:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                with isolation.connection('VFTEST_Importer') as raw:
                    receipt['native_context']=native_context(raw,isolation)
                    sql=FixtureSQL(raw,isolation)
                    originals={name:sql.rows('Importer',name) for name in (*PHYSICAL_TABLES,'InputTableList')}
                    for table in PHYSICAL_TABLES:
                        columns=schema['Importer/'+table]
                        native_columns=sql.schema('Importer',table)
                        if [c['name'] for c in native_columns]!=[c['name'] for c in columns]:
                            raise ValueError('Physical native export column order differs')
                        typed=[]
                        for row in populations[table]:
                            converted={c['name']:typed_value(row[c['name']],c) for c in columns}
                            for col in columns:
                                value=converted[col['name']]
                                if isinstance(value,Decimal):
                                    converted[col['name']]=value.quantize(Decimal(1).scaleb(-int(col['parameters'].split(',')[1])))
                            typed.append(converted)
                        for case_name,rows in (('empty',[]),('retained-plus-duplicate',typed+[deepcopy(typed[0])])):
                            stem=table+'-'+case_name;native_path=directory/(stem+'.native.csv')
                            roster=[dict(DatabaseName=database,TableName=name,Condition=None) for name in PHYSICAL_TABLES]
                            roster_columns=[dict(name=name,type='nvarchar',parameters='max',nullable=True)
                                            for name in ('DatabaseName','TableName','Condition')]
                            statements=[':setvar InputTableName "'+table+'"',':setvar DatabaseName "'+database+'"',
                                ':setvar ImporterDatabase "'+database+'"',
                                "EXECUTE AS LOGIN = '"+isolation.PRINCIPAL+"' WITH NO REVERT;",
                                'SET XACT_ABORT ON;','BEGIN TRANSACTION;',*_insert('InputTableList',roster_columns,roster),
                                *_insert(table,columns,[{key:value.isoformat() if isinstance(value,(date,datetime)) else value
                                    for key,value in row.items()} for row in rows]),'GO',':out "'+str(native_path)+'"',
                                ':r "'+str(SOURCE/SOURCE_PATH)+'"','GO',':out stdout',
                                "IF @@TRANCOUNT<>1 THROW 51000,'Input fixture transaction changed',1;",'ROLLBACK TRANSACTION;']
                            script=directory/(stem+'.sql');script.write_text('\n'.join(statements)+'\n',encoding='utf-8')
                            result=subprocess.run([str(SQLCMD),'-C','-E','-S','localhost','-d',database,
                                '-b','-f','i:65001','-i',str(script),'-h-1','-W','-s',','],
                                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60,check=False)
                            native=native_path.read_bytes() if native_path.exists() else b''
                            modern=input_table_bytes(columns,rows)
                            (directory/(stem+'.modern.csv')).write_bytes(modern)
                            item=dict(table=table,case=case_name,status='PASS' if result.returncode==0 and native==modern else 'FAIL',
                                source_rows=storage(rows),script_sha256=pin(script),returncode=result.returncode,
                                stdout_hex=result.stdout.hex(),stderr_hex=result.stderr.hex(),native_size=len(native),modern_size=len(modern),
                                native_sha256=hashlib.sha256(native).hexdigest(),modern_sha256=hashlib.sha256(modern).hexdigest())
                            receipt['cases'].append(item)
                            if item['status']!='PASS':item['strict_diff']=_diff(directory,stem,native,modern)
                            item['preservation']={name:strict_rows(sql,('Importer',name),prior) for name,prior in originals.items()}
                            if any(check['status']!='PASS' for check in item['preservation'].values()):
                                raise ValueError('Input-export rollback preservation failed')
            receipt['status']='PASS' if all(case['status']=='PASS' for case in receipt['cases']) else 'FAIL'
        except Exception as error:
            receipt.update(status='FAIL',error=type(error).__name__+': '+str(error))
        finally:
            receipt['identities_unchanged']=(pin(SOURCE/SOURCE_PATH)==SOURCE_SHA and pin(INPUT)==INPUT_SHA and
                pin(SQLCMD)==tool and code=={name:pin(ROOT/name) for name in CODE})
            if not receipt['identities_unchanged']:receipt.update(status='FAIL',error='Source/input/tool/code changed')
            json.dump(storage(receipt),stream,indent=2,ensure_ascii=False,allow_nan=False)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',required=True);parser.add_argument('--output',required=True)
    options=parser.parse_args();result=run(options.owner,options.output)
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),error=result.get('error'))))
    raise SystemExit(result['status']!='PASS')
