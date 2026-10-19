"""Exact approved BOR/report continuation of the preserved April8 benchmark.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import gzip
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import large_data_benchmark as b

OLD = b.BASE_EVIDENCE/'corrected-legacy-attempt-01'
DEST = OLD/'report-continuation'
PROPOSAL = OLD/'bor-report-compatibility-proposal'
PACKET_SHA = '6502ddaf2e3bf525e898c1954f4482f7a71d7ffd9179bea79425bc01b10120db'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def guard():
    if shutil.disk_usage('D:/').free < 20*1024**3:
        raise RuntimeError('20GiB free-space stop; preserve all evidence')


def plain(v):
    if isinstance(v,(date,datetime)): return v.isoformat()
    if isinstance(v,Decimal): return format(v,'f')
    if isinstance(v,bytes): return v.hex()
    return v


def reconcile_table(c, table, retained):
    with gzip.open(retained,'rt',encoding='utf-8') as stream:
        header=json.loads(next(stream))
        expected=Counter(tuple(r) for r in map(json.loads,stream))
    q=c.cursor();q.execute('SELECT * FROM dbo.['+table+']')
    if [x[0] for x in q.description]!=header['columns']: raise ValueError('Preserved column order changed')
    actual=Counter(tuple(plain(v) for v in row) for row in q);q.close()
    if actual!=expected: raise ValueError('Preserved table changed: '+table)
    return sum(actual.values())


def main():
    if b.sha(PROPOSAL/'decision.json') != PACKET_SHA: raise ValueError('Proposal changed')
    packet=json.loads((PROPOSAL/'decision.json').read_text())
    prior=json.loads((OLD/'day-attempt.json').read_text())
    calls=[json.loads(x) for x in (OLD/'sql-calls.jsonl').read_text().splitlines()]
    if prior['status']!='FAILED' or not calls[-1]['failed'] or not calls[-1]['source'].endswith('CollectBOR_OrderAllocationData.sql'):
        raise ValueError('Unexpected prior attempt/call boundary')
    if len([x for x in calls if x['approved_calculation_variant']])!=1: raise ValueError('Pick call count')
    if DEST.exists():
        # The only resumable preparation error is the external row-reader
        # TypeError, before ANY continuation SQL. No daily retry is permitted.
        previous=json.loads((DEST/'continuation-attempt.json').read_text())
        if (previous['status']!='FAILED' or previous['stages'] or previous['continuation_seconds']
                or previous['error'] not in ("TypeError('list indices must be integers or slices, not str')",
                                            'NameError("name \'calls\' is not defined")')
                or (DEST/'sql-calls.jsonl').exists()):
            raise ValueError('Continuation business work/error exists; no automatic retry')
        proof=json.loads((DEST/'native-failed-checkpoint-proof.json').read_text())
        if len(proof['databases'])!=8: raise ValueError('Incomplete failed checkpoint')
        for row in proof['databases']:
            if digest(row['path'])!=row['sha256']: raise ValueError('Failed checkpoint changed')
        b.EVIDENCE=OLD;_,isol=b.bindings()
        saved=json.loads((DEST/'execution-environment.json').read_text())
        env=os.environ.copy();env.update(saved['settings']);env['VF_LARGE_BENCHMARK_EVIDENCE']=str(DEST)
        n=1
        while (DEST/f'pre-business-error-{n}.json').exists(): n+=1
        (DEST/'continuation-attempt.json').rename(DEST/f'pre-business-error-{n}.json')
        if (DEST/'terminal.json').exists():
            (DEST/'terminal.json').rename(DEST/f'pre-business-terminal-{n}.json')
        return execute_remaining(prior,isol,env)
    DEST.mkdir()
    receipt={k:packet[k] for k in ('canonical_sha256','proposed_sha256','owner','restriction')}
    receipt.update(decision='APPROVE_REPORT_FIX_AND_REMAINING_STAGE_CONTINUATION',
        proposal_sha256=PACKET_SHA,question='call_80f221b6d63546a9a308957332ba04ce',
        human_answer='Approve report fix and remaining-stage continuation',
        recorded_utc=datetime.now(timezone.utc).isoformat())
    b.dump(DEST/'report-continuation-approval.json',receipt)
    b.EVIDENCE=OLD;case,isol=b.bindings()
    if dict(isol.MAPPING)!=packet['existing_target_bindings']: raise ValueError('Target mismatch')
    c=b.connect()
    try:
        rows=b.read(c.cursor(),"SELECT name,state_desc,is_read_only FROM sys.databases WHERE name LIKE 'VFTEST_Fresh_Benchmark_cb27310ddc744eb8b152624b9c1c5bc2[_]%' ORDER BY name")
        if len(rows)!=8 or any(r['state_desc']!='OFFLINE' or not r['is_read_only'] for r in rows): raise ValueError('Targets not offline/read-only')
        files=[]
        for db in isol.MAPPING.values():
            isol.validate_files(c,db)
            files.extend(b.read(c.cursor(),'SELECT DB_NAME(database_id) AS database_name,physical_name,size*CONVERT(bigint,8192) AS bytes FROM sys.master_files WHERE database_id=DB_ID(?)',db))
    finally: c.close()
    guard()
    if shutil.disk_usage('D:/').free-sum(r['bytes'] for r in files)<20*1024**3: raise ValueError('Cold copy cannot fit reserve')
    cold=DEST/'failed-cold-files';cold.mkdir()
    preserved={}
    for path in OLD.rglob('*'):
        if path.is_file() and not path.is_relative_to(DEST): preserved[str(path.relative_to(OLD))]=digest(path)
    b.dump(DEST/'failed-evidence-pins.json',preserved)
    try:
        for r in files:
            source=Path(r['physical_name']);target=cold/source.name
            guard();shutil.copy2(source,target)
            r['source_sha256']=digest(source);r['copy_sha256']=digest(target);r['copy']=str(target)
            if r['source_sha256']!=r['copy_sha256']: raise ValueError('Cold copy mismatch')
            print(json.dumps({'cold_copy':source.name,'bytes':source.stat().st_size}),flush=True)
        b.dump(DEST/'cold-copy-proof.json',files)
    except PermissionError as error:
        # SQL-created MDF ACLs deny this Windows user. Preserve the exact
        # database contents through SQL's own backup interface instead; do not
        # change ACLs, detach, reset, or adopt another database.
        backups=DEST/'failed-native-backups';backups.mkdir()
        proof=dict(method='COPY_ONLY CHECKSUM full backup; RESTORE VERIFYONLY',
            qualification='Content-restorable failed database checkpoint, not byte-identical MDF copy',
            preparation_error=repr(error),databases=[])
        c=b.connect();c.timeout=1800
        try:
            for db in isol.MAPPING.values():
                guard();path=backups/(db+'.bak')
                try:
                    c.execute('ALTER DATABASE ['+db+'] SET ONLINE')
                    q=c.execute('BACKUP DATABASE ['+db+"] TO DISK=N'"+str(path)+"' WITH COPY_ONLY, CHECKSUM, COMPRESSION")
                    while q.nextset():pass
                    q=c.execute("RESTORE VERIFYONLY FROM DISK=N'"+str(path)+"' WITH CHECKSUM")
                    while q.nextset():pass
                    header=b.read(c.cursor(),"RESTORE HEADERONLY FROM DISK=N'"+str(path)+"'")
                    row=dict(database=db,path=str(path),sha256=digest(path),header=header)
                    proof['databases'].append(row)
                    print(json.dumps({'preserved_native_backup':db,'bytes':path.stat().st_size}),flush=True)
                finally:
                    c.execute('ALTER DATABASE ['+db+'] SET OFFLINE')
        finally:c.close()
        b.dump(DEST/'native-failed-checkpoint-proof.json',proof)
    for name in ('case.json','execution-owner.json','correction-approval.json'):
        shutil.copy2(OLD/name,DEST/name)
    shutil.copytree(OLD/'canonical',DEST/'canonical')
    shutil.copytree(OLD/'report-tools',DEST/'report-tools')
    variant=PROPOSAL/'CollectBOR_OrderAllocationData.proposed.sql'
    if b.sha(variant)!=receipt['proposed_sha256']: raise ValueError('Variant changed')
    shutil.copy2(variant,DEST/'canonical/Scripts/BPR/OrderAllocationReports/CollectBOR_OrderAllocationData.sql')
    env=os.environ.copy()
    settings=json.loads((OLD/'execution-environment.json').read_text(encoding='utf-8-sig'))['settings']
    settings={k:v.replace(str(OLD),str(DEST)) for k,v in settings.items()}
    settings.update(RecordPenetrationExceptions='0',IsMTOEnvironment='0')
    env.update(settings);env['VF_LARGE_BENCHMARK_EVIDENCE']=str(DEST)
    for folder in ('logs','outputs','downloads','backups','upload-logs','sql'):
        (DEST/folder).mkdir(exist_ok=True)
    for k,v in settings.items():
        if k.endswith('FOLDER') or k.endswith('DOWNLOADLOC'): Path(v).mkdir(parents=True,exist_ok=True)
    b.dump(DEST/'execution-environment.json',dict(settings=settings,prior_active_seconds=prior['elapsed_seconds']))
    # Extract the unchanged original tail; no accepted BPR/Pick statements enter it.
    original=(DEST/'canonical/Engine/RunCoreBPR.bat').read_bytes().decode('cp1252')
    marker='\tcall %ROOT%\\Engine\\OrderAllocBasedReports.bat go'
    if original.count(marker)!=1: raise ValueError('BPR continuation boundary changed')
    tail='@echo off\r\n'+original[original.index(marker):]
    (DEST/'bpr-unexecuted-tail.cmd').write_bytes(tail.encode('cp1252'))
    execute_remaining(prior,isol,env)


def execute_remaining(prior,isol,env):
    calls=[json.loads(x) for x in (OLD/'sql-calls.jsonl').read_text().splitlines()]
    c=b.connect();online=False
    attempt=dict(status='RECONCILING',stages=[],prior_active_seconds=prior['elapsed_seconds'])
    start=None
    try:
        for db in isol.MAPPING.values(): c.execute('ALTER DATABASE ['+db+'] SET ONLINE')
        online=True
        q=b.connect(isol.MAPPING['VFTEST_BPR'])
        try:
            reconciled={table:reconcile_table(q,table,OLD/filename) for table,filename in (
                ('LogisticPickList','retained-LogisticPickList.jsonl.gz'),
                ('PickListDataForTruckFormation','retained-PickListDataForTruckFormation.jsonl.gz'),
                ('BORWithOrderAllocation','retained-BORWithOrderAllocation.jsonl.gz'))}
        finally: q.close()
        q=b.connect(isol.MAPPING['VFTEST_Importer'])
        try:
            flag=q.execute("SELECT CONVERT(int,IsScriptExecuted) FROM ScriptExecutedFlag WHERE ScriptName='CollectBOR_OrderAllocationData.sql'").fetchall()
            if len(flag)!=1 or flag[0][0]!=0: raise ValueError('BOR already executed')
            mto=q.execute("SELECT Value FROM VFSettings WHERE Parameter='IsMTOEnvironment'").fetchval()
            if str(mto)!='0': raise ValueError('Unexpected MTO branch')
        finally:q.close()
        b.dump(DEST/'prefix-reconciliation.json',dict(status='PASS',tables=reconciled,last_failed_call=calls[-1]))
        for db in isol.MAPPING.values(): c.execute('ALTER DATABASE ['+db+'] SET READ_WRITE')
        bridge=b.ROOT/'tools/large_data_legacy_sqlcmd.py';root=DEST/'canonical'
        def sql(role,rel):return '"'+sys.executable+'" "'+str(bridge)+'" -C -E -S localhost -d '+isol.MAPPING['VFTEST_'+role]+' -i "'+str(root/'Scripts'/rel)+'"'
        stages=[('bpr-unexecuted-tail','call "'+str(DEST/'bpr-unexecuted-tail.cmd')+'"'),
            ('post-bpr-attributes',sql('BPR','SiteSpecific/GulfOil/BPR/CalculatedAttributes.sql')),
            ('dbm-and-reports','call "'+str(root/'Engine/RunCoreDBM.bat')+'" go'),
            ('btr-guided-and-reports','call "'+str(root/'Engine/RunCoreBufferTrend.bat')+'" go'),
            ('post-btr-attributes',sql('BTR','SiteSpecific/GulfOil/BTR/CalculateAttributeBasedonBTR.sql'))]
        start=time.perf_counter();attempt['status']='RUNNING'
        for name,command in stages:
            guard();path=DEST/(name+'.cmd')
            if name!='bpr-unexecuted-tail': path.write_bytes(('@echo off\r\n'+command+'\r\n').encode('cp1252'))
            t=time.perf_counter()
            with (DEST/(name+'.log')).open('xb') as log:
                p=subprocess.Popen(['cmd.exe','/d','/c',str(path)],env=env,stdout=log,stderr=subprocess.STDOUT)
                while p.poll() is None:
                    if shutil.disk_usage('D:/').free<20*1024**3 or prior['elapsed_seconds']+time.perf_counter()-start>7200:
                        subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL)
                        raise RuntimeError('Owned continuation deadline/storage stop')
                    time.sleep(1)
            item=dict(stage=name,seconds=time.perf_counter()-t,exit_code=p.returncode)
            attempt['stages'].append(item)
            if p.returncode or (DEST/'day-failure.json').exists():raise RuntimeError('First new SQL failure: '+name)
            (DEST/'continuation-attempt.json').write_text(json.dumps(attempt,indent=2))
            print(json.dumps(item),flush=True)
        attempt['status']='EXECUTION_FINISHED_AWAITING_FULL_READBACK'
    except Exception as e:
        attempt.update(status='FAILED',error=repr(e));raise
    finally:
        attempt['continuation_seconds']=time.perf_counter()-start if start else 0
        attempt['combined_active_seconds']=prior['elapsed_seconds']+attempt['continuation_seconds']
        (DEST/'continuation-attempt.json').write_text(json.dumps(attempt,indent=2))
        if online:
            for db in isol.MAPPING.values():
                c.execute('ALTER DATABASE ['+db+'] SET READ_ONLY')
                c.execute('ALTER DATABASE ['+db+'] SET OFFLINE')
        b.dump(DEST/'terminal.json',b.read(c.cursor(),"SELECT name,state_desc,is_read_only FROM sys.databases WHERE name LIKE 'VFTEST_Fresh_Benchmark_cb27310ddc744eb8b152624b9c1c5bc2[_]%' ORDER BY name"))
        c.close()
    print(json.dumps(attempt,indent=2))


def finish_supplier(after_maintenance=False):
    """Second human-approved boundary; never replay the accepted BOR tail."""
    proposal=b.BASE_EVIDENCE/'stage6-admission-decision'
    if b.sha(proposal/'decision.json')!='dad787818997f4494006b11e45afb41236e4b8751e4f1a112bfb65fb5073236b':
        raise ValueError('Changed approved packet')
    approval=json.loads((proposal/'human-approval.json').read_text())
    if approval['decision']!='APPROVE_BOUNDED_ALIGNMENT_AND_CONTINUATION':raise ValueError('Missing actual approval')
    previous=OLD/'supplier-continuation' if after_maintenance else DEST
    root=OLD/('dbm-after-maintenance' if after_maintenance else 'supplier-continuation')
    if root.exists():raise ValueError('Supplier continuation exists; no automatic retry')
    failure=json.loads((previous/'day-failure.json').read_text())
    boundary='03.1 AcceptedNormsStockType.sql' if after_maintenance else 'GenSupplierWiseReq.sql'
    if not failure['source'].endswith(boundary):raise ValueError('Unexpected boundary')
    if after_maintenance:
        log=(previous/'logs/DBM.log').read_text(encoding='utf-8',errors='replace')
        native=Path(failure['source']).read_bytes()
        if ("User 'guest' does not have permission to run DBCC shrinkdatabase for database 'tempdb'." not in log
                or hashlib.sha256(native).hexdigest()!='80daf002096c427038c2db79c05fca4ed248abdec76b102e63891922bf6c74cc'
                or native.decode('cp1252').split("DBCC SHRINKDATABASE(N'tempdb')")[-1].strip() not in
                    ("print N''\r\nprint N'Finised - Suspend Accepted norms' + ' --> ' + convert(nvarchar(21), SYSDATETIME())",)):
            raise ValueError('Not the exact terminal shared-maintenance denial')
    calls=[json.loads(x) for x in (previous/'sql-calls.jsonl').read_text().splitlines()]
    if calls[-1]!=failure or any(x['failed'] for x in calls[:-1]):raise ValueError('Unexpected accepted prefix')
    b.EVIDENCE=OLD;_,isol=b.bindings();root.mkdir()
    receipt={**approval,**json.loads((proposal/'supplier-mapping-focused-proof.json').read_text())}
    b.dump(root/'supplier-continuation-approval.json',receipt)
    if after_maintenance:
        b.dump(root/'maintenance-disposition.json',dict(
            authority='Direct human routine-issue delegation and benchmark-throughstep7 release; no new human text invented',
            decision='Never grant tempdb/server rights or run shared shrink. Preserve/reconcile committed03.1business result; continue ONLY unexecuted03.2andlater stages.',
            failed_native_call=failure,business_retry=False,shared_tempdb_touched=False))
    c=b.connect();c.timeout=1800;p=None;start=None
    old_time=json.loads((previous/'continuation-attempt.json').read_text())['combined_active_seconds']
    attempt=dict(status='PRESERVING',stages=[],prior_active_seconds=old_time)
    try:
        state=b.read(c.cursor(),"SELECT name,state_desc,is_read_only FROM sys.databases WHERE name LIKE 'VFTEST_Fresh_Benchmark_cb27310ddc744eb8b152624b9c1c5bc2[_]%'")
        if len(state)!=8 or any(x['state_desc']!='OFFLINE' or not x['is_read_only'] for x in state):raise ValueError('Targets not stopped')
        # Reconcile every accepted typed Pick value and the precise script boundary.
        for db in isol.MAPPING.values():
            isol.validate_files(c,db);c.execute('ALTER DATABASE ['+db+'] SET ONLINE')
        q=b.connect(isol.MAPPING['VFTEST_BPR'])
        try:
            reconciled={table:reconcile_table(q,table,OLD/filename) for table,filename in (
                ('LogisticPickList','retained-LogisticPickList.jsonl.gz'),
                ('PickListDataForTruckFormation','retained-PickListDataForTruckFormation.jsonl.gz'))}
            reconciled['BOR_rows']=q.execute('SELECT COUNT_BIG(*) FROM BORWithOrderAllocation').fetchval()
            if reconciled['BOR_rows']!=3098:raise ValueError('BOR prefix changed')
        finally:q.close()
        q=b.connect(isol.MAPPING['VFTEST_Importer'])
        try:
            flags={name:int(value) for name,value in q.execute("SELECT ScriptName,IsScriptExecuted FROM ScriptExecutedFlag WHERE ScriptName IN ('GenSupplierWiseReq.sql','CollectBOR_OrderAllocationData.sql','UpdateBPR.sql','03.1 AcceptedNormsStockType.sql','03.2 AcceptedNormsConsumptionType.sql')")}
            expected={'GenSupplierWiseReq.sql':1 if after_maintenance else 0,'CollectBOR_OrderAllocationData.sql':1,'UpdateBPR.sql':1,
                '03.1 AcceptedNormsStockType.sql':1 if after_maintenance else 0,'03.2 AcceptedNormsConsumptionType.sql':0}
            if flags!=expected:raise ValueError(('Script boundary differs',flags))
        finally:q.close()
        b.dump(root/'prefix-reconciliation.json',dict(status='PASS',typed=reconciled,flags=flags))
        snapshots=root/'failed-checkpoint';snapshots.mkdir();preserved=[]
        for db in isol.MAPPING.values():
            guard();path=snapshots/(db+'.bak')
            q=c.execute('BACKUP DATABASE ['+db+"] TO DISK=N'"+str(path)+"' WITH COPY_ONLY,CHECKSUM,COMPRESSION")
            while q.nextset():pass
            q=c.execute("RESTORE VERIFYONLY FROM DISK=N'"+str(path)+"' WITH CHECKSUM")
            while q.nextset():pass
            preserved.append(dict(database=db,path=str(path),sha256=digest(path)))
            print(json.dumps({'preserved_post_BOR':db}),flush=True)
        b.dump(root/'failed-checkpoint-proof.json',preserved)
        for name in ('case.json','execution-owner.json','correction-approval.json','report-continuation-approval.json'):
            shutil.copy2(previous/name,root/name)
        shutil.copytree(previous/'canonical',root/'canonical');shutil.copytree(previous/'report-tools',root/'report-tools')
        variant=proposal/'GenSupplierWiseReq.proposed.sql'
        if b.sha(variant)!=receipt['proposed_sha256']:raise ValueError('Supplier proposal bytes changed')
        shutil.copy2(variant,root/'canonical/Scripts/BPR/Ration_Scripts/GenSupplierWiseReq.sql')
        settings=json.loads((previous/'execution-environment.json').read_text())['settings']
        settings={k:v.replace(str(previous),str(root)) for k,v in settings.items()}
        env=os.environ.copy();env.update(settings);env['VF_LARGE_BENCHMARK_EVIDENCE']=str(root)
        for name in ('logs','outputs','downloads','sql','backups','upload-logs'):(root/name).mkdir(exist_ok=True)
        for k,v in settings.items():
            if k.endswith('FOLDER') or k.endswith('DOWNLOADLOC'):Path(v).mkdir(parents=True,exist_ok=True)
        b.dump(root/'execution-environment.json',dict(settings=settings))
        b.dump(root/'operator-pins.json',{str(path.relative_to(b.ROOT)):digest(path) for path in
            (b.ROOT/'tools/large_data_legacy_continue.py',b.ROOT/'tools/large_data_legacy_sqlcmd.py',b.ROOT/'tools/large_data_benchmark.py')})
        canonical=root/'canonical';bridge=b.ROOT/'tools/large_data_legacy_sqlcmd.py'
        def sql(role,rel):return '"'+sys.executable+'" "'+str(bridge)+'" -C -E -S localhost -d '+isol.MAPPING['VFTEST_'+role]+' -i "'+str(canonical/'Scripts'/rel)+'"'
        original=(canonical/'Engine/RunCoreBPR.bat').read_bytes().decode('cp1252')
        marker='\tEcho Color based production requirement'
        if original.count(marker)!=1:raise ValueError('BPR remaining tail changed')
        tail=original[original.index(marker):]
        stages=[('supplier-and-remaining-bpr',sql('BPR','BPR/Ration_Scripts/GenSupplierWiseReq.sql')+'\r\n'+tail),
            ('post-bpr-attributes',sql('BPR','SiteSpecific/GulfOil/BPR/CalculatedAttributes.sql')),
            ('dbm-and-reports','call "'+str(canonical/'Engine/RunCoreDBM.bat')+'" go'),
            ('btr-guided-and-reports','call "'+str(canonical/'Engine/RunCoreBufferTrend.bat')+'" go'),
            ('post-btr-attributes',sql('BTR','SiteSpecific/GulfOil/BTR/CalculateAttributeBasedonBTR.sql'))]
        if after_maintenance:
            dbm=(canonical/'Engine/RunCoreDBM.bat').read_bytes().decode('cp1252')
            boundary='%CMDSTR% %SUSP3.1% >> %LogDBM%'
            if dbm.count(boundary)!=1:raise ValueError('DBM remaining boundary changed')
            pos=dbm.index(boundary)+len(boundary)
            assignments=[line for line in dbm[:pos].splitlines() if re.match(r'^\s*set\s',line,re.I)]
            if any('ERRORLEVEL' in line.upper() for line in assignments):raise ValueError('Unrestored dynamic DBM context')
            stages=[('dbm-unexecuted-after-maintenance','\r\n'.join(assignments)+'\r\n'+dbm[pos:]),*stages[-2:]]
        before_cpu=c.execute('SELECT process_kernel_time_ms,process_user_time_ms FROM sys.dm_os_sys_info').fetchone()
        b.dump(root/'resource-context.json',dict(cpu_before_seconds=sum(before_cpu)/1000,
            settings=b.read(c.cursor(),"SELECT name,CONVERT(int,value_in_use) AS value FROM sys.configurations WHERE name IN ('max server memory (MB)','max degree of parallelism')"),
            qualification='SharedSQLprocess; warmedcache/backgroundactivity included; no resource-setting change. Earlier14secondcontinuation lacksCPU/RSSsamples; no whole-daypeak/speedup claim.'))
        for db in isol.MAPPING.values():c.execute('ALTER DATABASE ['+db+'] SET READ_WRITE')
        start=time.perf_counter();attempt['status']='RUNNING'
        with (root/'resources.jsonl').open('x',encoding='utf-8') as metrics:
            for name,command in stages:
                script=root/(name+'.cmd');script.write_bytes(('@echo off\r\n'+command+'\r\n').encode('cp1252'))
                phase=time.perf_counter()
                with (root/(name+'.log')).open('xb') as log:
                    p=subprocess.Popen(['cmd.exe','/d','/c',str(script)],env=env,stdout=log,stderr=subprocess.STDOUT)
                    while p.poll() is None:
                        guard()
                        if old_time+time.perf_counter()-start>7200:raise RuntimeError('Combined active deadline')
                        rss=c.execute('SELECT physical_memory_in_use_kb FROM sys.dm_os_process_memory').fetchval()
                        cpu=c.execute('SELECT process_kernel_time_ms,process_user_time_ms FROM sys.dm_os_sys_info').fetchone()
                        metrics.write(json.dumps(dict(elapsed_seconds=time.perf_counter()-start,sql_rss_bytes=int(rss)*1024,sql_cpu_seconds=sum(cpu)/1000,disk_free_bytes=shutil.disk_usage('D:/').free))+'\n');metrics.flush()
                        time.sleep(1)
                item=dict(stage=name,seconds=time.perf_counter()-phase,exit_code=p.returncode);attempt['stages'].append(item)
                if p.returncode or (root/'day-failure.json').exists():raise RuntimeError('First new failure: '+name)
                (root/'continuation-attempt.json').write_text(json.dumps(attempt,indent=2),encoding='utf-8')
                print(json.dumps(item),flush=True)
        attempt['status']='EXECUTION_FINISHED_AWAITING_FULL_READBACK'
    except Exception as error:
        if p is not None and p.poll() is None:
            subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL);p.wait(timeout=30)
        attempt.update(status='FAILED',error=repr(error));raise
    finally:
        attempt['continuation_seconds']=time.perf_counter()-start if start else 0
        attempt['combined_active_seconds']=old_time+attempt['continuation_seconds']
        (root/'continuation-attempt.json').write_text(json.dumps(attempt,indent=2),encoding='utf-8')
        for db in isol.MAPPING.values():
            if c.execute('SELECT state_desc FROM sys.databases WHERE name=?',db).fetchval()=='ONLINE':
                c.execute('ALTER DATABASE ['+db+'] SET READ_ONLY');c.execute('ALTER DATABASE ['+db+'] SET OFFLINE')
        b.dump(root/'terminal.json',b.read(c.cursor(),"SELECT name,state_desc,is_read_only FROM sys.databases WHERE name LIKE 'VFTEST_Fresh_Benchmark_cb27310ddc744eb8b152624b9c1c5bc2[_]%' ORDER BY name"));c.close()
    print(json.dumps(attempt,indent=2))


if __name__=='__main__':
    if sys.argv[1:]==['--supplier']:finish_supplier()
    elif sys.argv[1:]==['--after-tempdb-maintenance']:finish_supplier(after_maintenance=True)
    else:main()
