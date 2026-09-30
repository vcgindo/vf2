"""Read-only memory observations around the unchanged day12 production boundary.

No tracemalloc heap copy, GC manipulation, row sampling or calculation patching.
Only selected production frames emit bounded scalar summaries, flushed before
the next allocation so a killed worker leaves usable diagnostic evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def summary(value):
    if isinstance(value, (list, tuple)):
        result = {'kind': type(value).__name__, 'length': len(value),
                  'shallow_bytes': sys.getsizeof(value)}
        if value and isinstance(value[-1], tuple) and len(value[-1]) == 2:
            last = value[-1][1]
            if isinstance(last, dict):
                result['last_stage'] = value[-1][0]
                result['last_table_rows'] = {k: len(v) for k, v in last.items() if isinstance(v, list)}
        return result
    if isinstance(value, dict):
        return {'kind': 'dict', 'keys': len(value), 'shallow_bytes': sys.getsizeof(value),
                'table_rows': {str(k): len(v) for k, v in value.items() if isinstance(v, (list, tuple))}}
    return {'kind': type(value).__name__}


def main(options):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
    import django
    django.setup()
    from mta.runtime import temporal, services, relational_state
    from mta.temporal import chain
    from tools.temporal_worker import run_one

    options.memory_profile.parent.mkdir(parents=True, exist_ok=True)
    observed = set()
    targets = {function.__code__ for function in (
        temporal.execute_day, chain.calculate_day, services.finish_run,
        relational_state.save_daily)}
    started = time.monotonic()
    with options.memory_profile.open('x', encoding='utf-8', buffering=1) as stream:
        stream.write(json.dumps(dict(kind='diagnostic-not-parity', day=options.day,
            artifact_sha256=options.sha256, cap=int(Path('/sys/fs/cgroup/memory.max').read_text()),
            profiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))+'\n')

        def trace(frame, event, arg):
            if frame.f_code not in targets:
                return None
            key = (frame.f_code.co_filename, frame.f_lineno, event)
            if event in ('line', 'return', 'exception') and key not in observed:
                observed.add(key)
                status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
                record = dict(seconds=round(time.monotonic()-started, 3),
                    file=str(Path(frame.f_code.co_filename).relative_to(ROOT)),
                    function=frame.f_code.co_name, line=frame.f_lineno, event=event,
                    rss=status['VmRSS'].strip(), peak=status['VmHWM'].strip(),
                    cgroup_current=int(Path('/sys/fs/cgroup/memory.current').read_text()),
                    cgroup_peak=int(Path('/sys/fs/cgroup/memory.peak').read_text()),
                    retained={name: summary(value) for name, value in frame.f_locals.items()
                              if isinstance(value, (dict, list, tuple))})
                stream.write(json.dumps(record, separators=(',', ':'))+'\n')
            return trace

        original = temporal.execute_day
        def profiled(**kwargs):
            sys.settrace(trace)
            try:
                return original(**kwargs)
            finally:
                sys.settrace(None)
        temporal.execute_day = profiled
        try:
            run_one(options)
        finally:
            temporal.execute_day = original


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('artifact', 'previous', 'destination', 'memory-profile'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--day', type=int, choices=[11], required=True)
    parser.add_argument('--attempt-revision', required=True)
    main(parser.parse_args())
