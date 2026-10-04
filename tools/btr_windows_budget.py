"""Temporary Windows aggregate process budgets for the approved BTR benchmark.

No credentials, process termination, security setting or service restart. Clears
its own limits on stop/heartbeat loss/deadline, leaving target processes alive.
SQL Server needs an elevated launch because Windows denies PROCESS_SET_QUOTA to
the ordinary desktop account. A nested job never modifies an existing parent job;
its presence is recorded and must be assessed in matched-resource acceptance.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import time
import sys


class SqlBufferBudget:
    """Leave non-buffer headroom before applying the SQL process total ceiling."""
    def __init__(self, root, maximum_mb):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from tools.stage2_vm_dataset import connect
        self.connect = connect
        self.root = root
        self.maximum_mb = maximum_mb
        self.original = self.read()
        with (root / 'sql-buffer-original.json').open('x') as stream:
            json.dump(self.original, stream, indent=2)
        try:
            self.configure(maximum_mb)
        except BaseException:
            self.restore()
            raise

    def read(self):
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT name,CAST(value AS int),CAST(value_in_use AS int) FROM sys.configurations "
                           "WHERE name IN ('show advanced options','max server memory (MB)')")
            return {r[0]: dict(value=r[1], in_use=r[2]) for r in cursor}

    def configure(self, maximum):
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute("EXEC sp_configure 'show advanced options',1; RECONFIGURE")
            cursor.execute("EXEC sp_configure 'max server memory (MB)',?; RECONFIGURE", maximum)
            cursor.execute("EXEC sp_configure 'show advanced options',?; RECONFIGURE",
                           self.original['show advanced options']['value'])
        actual = self.read()
        assert actual['max server memory (MB)']['in_use'] == maximum
        return actual

    def wait_for_headroom(self, pid, total_bytes):
        # Changing max server memory releases buffer allocation asynchronously.
        # Refuse the total cap while existing committed memory already exceeds it.
        deadline = time.monotonic() + 120
        observations = []
        while True:
            private = int(subprocess.check_output(['powershell', '-NoProfile', '-Command',
                '(Get-Process -Id ' + str(int(pid)) + ').PrivateMemorySize64']))
            observations.append(dict(time=time.time(), private_bytes=private))
            if private <= total_bytes - 256 * 1024**2:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError('SQL committed memory leaves insufficient process-cap headroom')
            time.sleep(2)
        (self.root / 'sql-buffer-ready.json').write_text(json.dumps(dict(
            settings=self.read(), observations=observations, total_bytes=total_bytes,
            non_buffer_headroom_bytes=total_bytes-self.maximum_mb*1024**2), indent=2))

    def restore(self):
        actual = self.configure(self.original['max server memory (MB)']['value'])
        assert actual == self.original
        (self.root / 'sql-buffer-restored.json').write_text(json.dumps(actual, indent=2))
        return actual


class Basic(C.Structure):
    _fields_=[('ProcessTime',C.c_longlong),('JobTime',C.c_longlong),('Flags',W.DWORD),
              ('MinWorkingSet',C.c_size_t),('MaxWorkingSet',C.c_size_t),('ActiveProcesses',W.DWORD),
              ('Affinity',C.c_size_t),('Priority',W.DWORD),('Scheduling',W.DWORD)]


class IO(C.Structure):
    _fields_=[(n,C.c_ulonglong) for n in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]


class Extended(C.Structure):
    _fields_=[('Basic',Basic),('IO',IO),('ProcessMemory',C.c_size_t),('JobMemory',C.c_size_t),
              ('PeakProcessMemory',C.c_size_t),('PeakJobMemory',C.c_size_t)]


class CPU(C.Structure):
    _fields_=[('Flags',W.DWORD),('Rate',W.DWORD)]


class Memory(C.Structure):
    _fields_=[('Size',W.DWORD),('PageFaults',W.DWORD)]+[
        (name,C.c_size_t) for name in ('PeakWorkingSet','WorkingSet','PeakPagedPool',
        'PagedPool','PeakNonPagedPool','NonPagedPool','Pagefile','PeakPagefile','PrivateBytes')]


def api():
    k=C.WinDLL('kernel32',use_last_error=True)
    declarations={'OpenProcess':([W.DWORD,W.BOOL,W.DWORD],W.HANDLE),
       'CreateJobObjectW':([C.c_void_p,W.LPCWSTR],W.HANDLE),
       'SetInformationJobObject':([W.HANDLE,C.c_int,C.c_void_p,W.DWORD],W.BOOL),
       'QueryInformationJobObject':([W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.c_void_p],W.BOOL),
       'AssignProcessToJobObject':([W.HANDLE,W.HANDLE],W.BOOL),
       'IsProcessInJob':([W.HANDLE,W.HANDLE,C.POINTER(W.BOOL)],W.BOOL),
       'GetProcessTimes':([W.HANDLE,*([C.POINTER(W.FILETIME)]*4)],W.BOOL),
       'K32GetProcessMemoryInfo':([W.HANDLE,C.POINTER(Memory),W.DWORD],W.BOOL),
       'QueryFullProcessImageNameW':([W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)],W.BOOL),
       'CloseHandle':([W.HANDLE],W.BOOL)}
    for name,(args,result) in declarations.items():
        function=getattr(k,name);function.argtypes=args;function.restype=result
    return k


def checked(value):
    if not value:raise C.WinError(C.get_last_error())
    return value


def open_target(k,pid):
    handle=k.OpenProcess(0x100|0x1|0x1000,False,pid)
    if handle:return handle
    error=C.get_last_error()
    if error!=5:raise C.WinError(error)
    # Enable an already-held administrator privilege only while opening this
    # exact service-process handle, then restore the token immediately. This
    # grants no account rights and changes no persistent security setting.
    class LUID(C.Structure):_fields_=[('Low',W.DWORD),('High',W.LONG)]
    class Privilege(C.Structure):_fields_=[('Count',W.DWORD),('Luid',LUID),('Attributes',W.DWORD)]
    a=C.WinDLL('advapi32',use_last_error=True)
    a.OpenProcessToken.argtypes=[W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)];a.OpenProcessToken.restype=W.BOOL
    a.LookupPrivilegeValueW.argtypes=[W.LPCWSTR,W.LPCWSTR,C.POINTER(LUID)];a.LookupPrivilegeValueW.restype=W.BOOL
    a.AdjustTokenPrivileges.argtypes=[W.HANDLE,W.BOOL,C.c_void_p,W.DWORD,C.c_void_p,C.c_void_p];a.AdjustTokenPrivileges.restype=W.BOOL
    k.GetCurrentProcess.restype=W.HANDLE
    token=W.HANDLE();checked(a.OpenProcessToken(k.GetCurrentProcess(),0x20|0x8,C.byref(token)))
    previous=Privilege();requested=Privilege();requested.Count=1;requested.Attributes=2
    changed=False
    try:
        checked(a.LookupPrivilegeValueW(None,'SeDebugPrivilege',C.byref(requested.Luid)))
        length=W.DWORD();checked(a.AdjustTokenPrivileges(token,False,C.byref(requested),C.sizeof(previous),C.byref(previous),C.byref(length)))
        if C.get_last_error()==1300:raise PermissionError('Elevated token does not hold SeDebugPrivilege')
        changed=True
        return checked(k.OpenProcess(0x100|0x1|0x1000,False,pid))
    finally:
        if changed:checked(a.AdjustTokenPrivileges(token,False,C.byref(previous),0,None,None))
        k.CloseHandle(token)


class Budget:
    def __init__(self,pid,expected_executable,memory_bytes,cores,identity,*,allow_nested=False):
        self.k=api();self.process=None;self.job=None;self.pid=pid;self.applied=False
        self.process=open_target(self.k,pid)
        try:
            path=C.create_unicode_buffer(32768);length=W.DWORD(len(path))
            checked(self.k.QueryFullProcessImageNameW(self.process,0,path,C.byref(length)))
            if Path(path.value).resolve()!=Path(expected_executable).resolve():raise ValueError('Process executable identity differs')
            existing=W.BOOL();checked(self.k.IsProcessInJob(self.process,None,C.byref(existing)))
            self.parent_job_present=bool(existing.value)
            if existing.value and not allow_nested:raise ValueError('Existing parent job requires explicit nested-budget configuration')
            self.job=checked(self.k.CreateJobObjectW(None,'Local\\FreshBtr-'+identity))
            if C.get_last_error()==183:raise ValueError('Budget job identity already exists')
            # Configure before association. No kill-on-close or breakaway flags.
            limit=Extended();limit.Basic.Flags=0x200;limit.JobMemory=memory_bytes
            cpu=CPU(1|4,int(10000*cores/os.cpu_count()))
            if not 1<=cpu.Rate<=10000:raise ValueError('Invalid CPU budget')
            self.set(9,limit);self.set(15,cpu)
            checked(self.k.AssignProcessToJobObject(self.job,self.process));self.applied=True
            self.expected=(memory_bytes,cpu.Rate)
            self.verify()
        except BaseException:
            self.close();raise

    def set(self,kind,value):
        checked(self.k.SetInformationJobObject(self.job,kind,C.byref(value),C.sizeof(value)))

    def state(self):
        limit=Extended();cpu=CPU()
        checked(self.k.QueryInformationJobObject(self.job,9,C.byref(limit),C.sizeof(limit),None))
        checked(self.k.QueryInformationJobObject(self.job,15,C.byref(cpu),C.sizeof(cpu),None))
        times=[W.FILETIME() for _ in range(4)]
        checked(self.k.GetProcessTimes(self.process,*[C.byref(value) for value in times]))
        cpu_seconds=sum((value.dwHighDateTime<<32)|value.dwLowDateTime for value in times[2:])/10**7
        memory=Memory();memory.Size=C.sizeof(memory)
        checked(self.k.K32GetProcessMemoryInfo(self.process,C.byref(memory),C.sizeof(memory)))
        return dict(pid=self.pid,parent_job_present=self.parent_job_present,memory_flags=limit.Basic.Flags,memory_bytes=limit.JobMemory,
                    cpu_seconds=cpu_seconds,working_set_bytes=memory.WorkingSet,private_bytes=memory.PrivateBytes,
                    peak_commit_bytes=limit.PeakJobMemory,cpu_flags=cpu.Flags,cpu_rate=cpu.Rate)

    def verify(self):
        state=self.state()
        assert (state['memory_bytes'],state['cpu_rate'])==self.expected
        assert state['memory_flags']==0x200 and state['cpu_flags']==5
        return state

    def restore(self):
        if self.job:
            self.set(15,CPU());self.set(9,Extended())
            state=self.state()
            assert state['cpu_flags']==state['memory_flags']==0
            return state

    def close(self):
        try:
            if self.job:self.restore()
        finally:
            if self.job:self.k.CloseHandle(self.job);self.job=None
            if self.process:self.k.CloseHandle(self.process);self.process=None


class PostgresBudget:
    """Online limits only, with original container identity/config restored."""
    def __init__(self, root, memory_bytes=3*1024**3):
        self.pid='freshvcf-test-postgres-1'
        item=self.inspect()
        self.identity=item['Id']
        self.original=self.limits(item)
        self.expected=dict(memory_bytes=memory_bytes,memory_swap_bytes=memory_bytes,nano_cpus=2*10**9)
        # Write recovery instructions before any mutation; no container recreate.
        with (root/'postgres-original-budget.json').open('x') as output:
            json.dump(dict(container=self.pid,id=self.identity,original=self.original),output,indent=2)
        try:
            self.update(self.expected);self.verify()
        except BaseException:
            self.restore();raise

    def inspect(self):
        return json.loads(subprocess.check_output(['docker','inspect',self.pid]))[0]

    @staticmethod
    def limits(item):
        config=item['HostConfig']
        return dict(memory_bytes=config['Memory'],memory_swap_bytes=config['MemorySwap'],nano_cpus=config['NanoCpus'])

    def update(self,values):
        assert self.inspect()['Id']==self.identity,'PostgreSQL identity changed; do not mutate replacement'
        subprocess.run(['docker','update','--memory',str(values['memory_bytes']),
            '--memory-swap',str(values['memory_swap_bytes']),'--cpus',str(values['nano_cpus']/10**9),self.pid],
            check=True,stdout=subprocess.DEVNULL)

    def verify(self):
        item=self.inspect()
        assert item['Id']==self.identity and item['State']['Running']
        actual=self.limits(item);assert actual==self.expected
        return dict(container=self.pid,id=self.identity,**actual)

    def restore(self):
        self.update(self.original)
        actual=self.limits(self.inspect());assert actual==self.original
        return dict(container=self.pid,id=self.identity,**actual)

    def close(self):
        pass


def main(config_path):
    config=json.loads(Path(config_path).read_text());root=Path(config['evidence'])
    assert root.resolve().is_relative_to(Path('D:/freshvcf-build/evidence').resolve())
    assert config['max_seconds']<=7200
    budgets=[];sql_buffer=None;result=dict(status='FAILED',targets=config['targets']);start=time.monotonic()
    try:
        if config.get('sql_buffer_max_mb'):
            sql_target = next(t for t in config['targets'] if Path(t['executable']).name.lower() == 'sqlservr.exe')
            assert 128 <= config['sql_buffer_max_mb'] <= sql_target['memory_bytes']//1024**2-512
            sql_buffer = SqlBufferBudget(root, config['sql_buffer_max_mb'])
            sql_buffer.wait_for_headroom(sql_target['pid'], sql_target['memory_bytes'])
        for target in config['targets']:
            budgets.append(Budget(target['pid'],target['executable'],target['memory_bytes'],
                                  target['cores'],config['identity']+'-'+str(target['pid']),allow_nested=config.get('allow_nested',False)))
        if config.get('existing_postgres'):
            budgets.append(PostgresBudget(root,config.get('postgres_memory_bytes',3*1024**3)))
        (root/'budget-ready.json').write_text(json.dumps([b.verify() for b in budgets],indent=2))
        with (root/'budget-observations.jsonl').open('x') as output:
            while not (root/'budget-stop').exists():
                if time.monotonic()-start>=config['max_seconds']:break
                heartbeat=root/'budget-heartbeat'
                if not heartbeat.exists() or time.time()-heartbeat.stat().st_mtime>90:break
                output.write(json.dumps(dict(time=time.time(),targets=[b.verify() for b in budgets]))+'\n');output.flush()
                time.sleep(2)
        result['status']='RESTORED'
    except BaseException as exc:
        result['error']=repr(exc)
    finally:
        # One failed restoration must never prevent releasing another target.
        result['restored']=[]
        result['restoration_errors']=[]
        for b in budgets:
            try:
                result['restored'].append(b.restore())
            except BaseException as exc:
                result['restoration_errors'].append(dict(pid=b.pid,error=repr(exc)))
            finally:
                try:
                    b.close()
                except BaseException as exc:
                    result['restoration_errors'].append(dict(pid=b.pid,error=repr(exc)))
        if result['restoration_errors']:
            result['status']='RESTORATION_FAILED'
        if sql_buffer:
            try:
                result['sql_buffer_restored'] = sql_buffer.restore()
            except BaseException as exc:
                result['restoration_errors'].append(dict(sql_buffer=repr(exc)))
                result['status']='RESTORATION_FAILED'
        (root/'budget-result.json').write_text(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('config')
    main(parser.parse_args().config)
