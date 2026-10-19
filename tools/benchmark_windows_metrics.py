"""Read-only native Windows process counters for the external benchmark."""
import ctypes
from ctypes import wintypes


class Memory(ctypes.Structure):
    _fields_ = [('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
        (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
        'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage',
        'PagefileUsage','PeakPagefileUsage','PrivateUsage')]


class HostMemory(ctypes.Structure):
    _fields_ = [('dwLength',wintypes.DWORD),('dwMemoryLoad',wintypes.DWORD)]+[
        (name,ctypes.c_ulonglong) for name in ('ullTotalPhys','ullAvailPhys','ullTotalPageFile',
        'ullAvailPageFile','ullTotalVirtual','ullAvailVirtual','ullAvailExtendedVirtual')]


def sample(pid):
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    api = ctypes.WinDLL('psapi',use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    api.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,ctypes.POINTER(Memory),wintypes.DWORD]
    host = HostMemory();host.dwLength=ctypes.sizeof(host)
    kernel.GlobalMemoryStatusEx(ctypes.byref(host))
    result = dict(host_physical_bytes=host.ullTotalPhys,host_available_bytes=host.ullAvailPhys)
    handle = kernel.OpenProcess(0x0400|0x0010,False,pid)
    if not handle:
        result['process_counter_error'] = ctypes.get_last_error()
        return result
    try:
        memory=Memory();memory.cb=ctypes.sizeof(memory)
        if api.GetProcessMemoryInfo(handle,ctypes.byref(memory),memory.cb):
            result.update(sql_rss_bytes=memory.WorkingSetSize,sql_private_bytes=memory.PrivateUsage)
        times=[wintypes.FILETIME() for _ in range(4)]
        if kernel.GetProcessTimes(handle,*(ctypes.byref(t) for t in times)):
            result['sql_cpu_seconds']=sum((t.dwHighDateTime<<32)+t.dwLowDateTime for t in times[2:])/10_000_000
    finally:
        kernel.CloseHandle(handle)
    return result
