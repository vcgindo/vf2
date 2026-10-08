"""At most one owned native Pick-stage call for one pinned modern-produced date."""
import argparse,hashlib,json,os,sys
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from parity.verify_pick_integration import SOURCE_KEYS,compare_full_state,compare_downstream
from parity.verify_pick_stage_state import LOGISTIC,REMAINING,FLAG,SCRATCH,FixtureSQL,prepare,preflight_fixtures,compare_rows,execute_native,guard_options
from mta.serialization import storage,digest
from parity import legacy_isolation as isolation

def restore(rows,columns):
    values=[]
    for row in rows:
        copy=dict(row)
        unused_vehicle={'Length','Width','Height','ToleranceInWeight','ToleranceInVolume','TransportLoadTypeCutOff'}
        missing={c['name'] for c in columns} - set(copy)
        if not missing <= unused_vehicle: raise ValueError('Unexpected omitted native source column')
        for c in columns:
            if c['name'] in missing:
                if not c['nullable']: raise ValueError('Unused native column is not nullable')
                copy[c['name']]=None
        for c in columns:
            n=c['name']
            if n in copy and copy[n] is not None and c['type_name'] in ('decimal','numeric'):
                original=Decimal(str(copy[n]))
                scaled=original.quantize(Decimal(1).scaleb(-c['scale']))
                if scaled != original: raise ValueError('Native decimal scale would change the value')
                copy[n]=scaled
        values.append(copy)
    return values

def run(a):
    raw_input=Path(a.input).read_bytes()
    if hashlib.sha256(raw_input).hexdigest()!=a.sha256:raise ValueError('Pinned modern readback proof differs')
    report_source=json.loads(raw_input)
    if report_source['status']!='PASS':raise ValueError('Successful actual modern readback required')
    chosen=report_source['days'][a.day_index]
    if {k:digest(v) for k,v in chosen['sources'].items()}!=chosen['source_digests']:raise ValueError('Produced source digest differs')
    output=guard_options(a.owner,Path(a.output))
    # Reserve this exact owned date before native execution. An uncertain attempt
    # cannot silently consume a second stage invocation by overwriting a receipt.
    with output.open('x',encoding='utf-8') as f:json.dump(dict(status='STARTED',date=chosen['date'],run_id=chosen['run_id']),f)
    script,identities=prepare(a.owner,isolation);os.environ['VFTEST_PROFILE']='fresh'
    result=dict(status='STARTED',scope='matched-input Pick-stage parity, not independent full daily parity',
        date=chosen['date'],run_id=chosen['run_id'],modern_input_sha256=a.sha256,identities=identities,
        canonical_sha256=script.source_sha256,business_day_calls=0,native_pick_invocations=0)
    try:
        with isolation.exclusive_replay(validate_schema=True),isolation.connection('VFTEST_BPR') as raw:
            sql=FixtureSQL(raw,isolation)
            names=('pick_rows','sku_attributes','location_attributes','vehicles','location_vehicles')
            declared={k:restore(chosen['sources'][name],sql.schema(*k)) for k,name in zip(SOURCE_KEYS,names)}
            declared.update({LOGISTIC:[],REMAINING:[],SCRATCH:[],FLAG:[dict(ScriptName='GenerateLogisticPickList.sql',ModuleName='BPR',IsScriptExecuted=False,IsScriptCritical=True)]})
            result['unused_vehicle_columns']={'Length':None,'Width':None,'Height':None,'ToleranceInWeight':None,'ToleranceInVolume':None,'TransportLoadTypeCutOff':None}
            result['preflight']=preflight_fixtures(sql,[(chosen['date'],declared)])
            if result['preflight']['status']!='PASS':raise ValueError('Matched-input fixture preflight failed')
            originals={k:sql.rows(*k) for k in declared};scratch=sql.scratch()
            raw.raw.autocommit=False
            try:
                for k,rows in declared.items():sql.load(*k,rows)
                result['loaded_sources']=[dict(role=k[0],table=k[1],rows=storage(sql.rows(*k))) for k in SOURCE_KEYS]
                result['source_readback']={'.'.join(k):compare_rows(sql.rows(*k),declared[k],sql.schema(*k)) for k in SOURCE_KEYS}
                if any(c['status']!='PASS' for c in result['source_readback'].values()):raise ValueError('Native source load differs')
                result['sql_receipts']=[];result['native_pick_invocations']=1
                execute_native(raw,script,isolation,result['sql_receipts'])
                native={k[1]:sql.rows(*k) for k in (LOGISTIC,REMAINING)}
                modern={k[1]:restore(chosen['modern_state'][k[1]],sql.schema(*k)) for k in (LOGISTIC,REMAINING)}
                result['native_rows']=storage(native);result['modern_rows']=storage(modern)
                result['tables']=compare_full_state(native,modern,sql)
                result['reports']=compare_downstream(native,modern)
                if result['tables']['status']!='PASS' or result['reports']['status']!='PASS':raise ValueError('Matched-input Pick stage differs')
                result['status']='PASS'
            finally:
                raw.rollback();raw.raw.autocommit=True
                result['rollback']=raw.execute('SELECT @@TRANCOUNT').fetchval()==0
                result['restoration']={'.'.join(k):compare_rows(sql.rows(*k),rows,sql.schema(*k)) for k,rows in originals.items()}
                after=sql.scratch()
                result['scratch_restoration']={n:compare_rows(after[n],rows,sql.schema('Intermediate',n)) for n,rows in scratch.items()}
                if not result['rollback'] or set(after)!=set(scratch) or any(c['status']!='PASS' for c in [*result['restoration'].values(),*result['scratch_restoration'].values()]):raise ValueError('Owned native rollback differs')
    except Exception as e:
        result.update(status='FAIL',error_type=type(e).__name__,error=str(e))
    output.write_text(json.dumps(storage(result),indent=2),encoding='utf-8')
    print(json.dumps(dict(status=result['status'],native_pick_invocations=result['native_pick_invocations'],output=str(output))))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--owner',required=True);p.add_argument('--input',required=True);p.add_argument('--sha256',required=True);p.add_argument('--day-index',type=int,choices=(0,1),required=True);p.add_argument('--output',required=True)
    raise SystemExit(run(p.parse_args()))
