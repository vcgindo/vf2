"""Bound a fresh local Python worker before permitting any task code to execute."""
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys


def run(arguments, *, stdout, cwd):
    if os.name!='nt':
        raise ValueError('The local SQL oracle worker requires Windows job limits')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    size=ctypes.c_size_t

    class Basic(ctypes.Structure):
        _fields_=[('PerProcessUserTimeLimit',ctypes.c_int64),('PerJobUserTimeLimit',ctypes.c_int64),
            ('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',size),('MaximumWorkingSetSize',size),
            ('ActiveProcessLimit',wintypes.DWORD),('Affinity',size),('PriorityClass',wintypes.DWORD),
            ('SchedulingClass',wintypes.DWORD)]

    class IO(ctypes.Structure):
        _fields_=[(name,ctypes.c_uint64) for name in ('ReadOperationCount','WriteOperationCount',
            'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]

    class Extended(ctypes.Structure):
        _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',size),
            ('JobMemoryLimit',size),('PeakProcessMemoryUsed',size),('PeakJobMemoryUsed',size)]

    kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype=wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
    kernel.GetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.POINTER(size),ctypes.POINTER(size)]
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.QueryInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p]

    def check(value):
        if not value:
            raise ctypes.WinError(ctypes.get_last_error())
        return value

    job=check(kernel.CreateJobObjectW(None,None))
    process=None
    try:
        permitted=size();system=size()
        check(kernel.GetProcessAffinityMask(kernel.GetCurrentProcess(),ctypes.byref(permitted),ctypes.byref(system)))
        bits=[1<<i for i in range(ctypes.sizeof(size)*8) if permitted.value&(1<<i)]
        if len(bits)<2:
            raise ValueError('Two permitted CPUs are required for the bounded oracle worker')
        limits=Extended()
        # Affinity + per-job committed-memory limit + kill descendants on close.
        limits.BasicLimitInformation.LimitFlags=0x10|0x200|0x2000
        limits.BasicLimitInformation.Affinity=bits[0]|bits[1]
        limits.JobMemoryLimit=4*1024**3
        check(kernel.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)))
        gate=("import sys,runpy; token=sys.stdin.readline(); "
              "assert token=='go\\n','Bounded worker gate denied'; "
              "sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')")
        process=subprocess.Popen([str(arguments[0]),'-c',gate,*map(str,arguments[1:])],
            cwd=cwd,stdin=subprocess.PIPE,stdout=stdout,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,text=True)
        check(kernel.AssignProcessToJobObject(job,wintypes.HANDLE(int(process._handle))))
        process.stdin.write('go\n');process.stdin.flush();process.stdin.close()
        code=process.wait()
        measured=Extended()
        check(kernel.QueryInformationJobObject(job,9,ctypes.byref(measured),ctypes.sizeof(measured),None))
        return dict(returncode=code,memory_limit_bytes=limits.JobMemoryLimit,
            affinity_mask=limits.BasicLimitInformation.Affinity,cpu_count=2,
            peak_job_memory_bytes=measured.PeakJobMemoryUsed)
    finally:
        kernel.CloseHandle(job)
        if process is not None and process.poll() is None:
            process.kill();process.wait()
