"""Fresh canonical SQL / pure modern comparison on retained, named fixtures.

The oracle owns only VFTEST_Fresh_* under one exclusive lease. No inputs are
generated, no failed attempt is overwritten, and no exception counts as parity.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time
import traceback

from mta.planning.engine import calculate_current_day
from mta.serialization import storage
from parity.current_day import compare
from parity.legacy_isolation import exclusive_replay, MAPPING
from parity.verify_raw import options
from parity.verify_current_day import checksum, file_hash

ROOT = Path(__file__).resolve().parents[1]


def replay(destination, fixtures):
    from parity.adapters.legacy.r1_runner import execute_r1_legacy
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    sources = {str(p.relative_to(ROOT)): file_hash(p) for folder in ('mta', 'parity')
               for p in sorted((ROOT / folder).rglob('*.py'))}
    source = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  files=sources, oracle_databases=MAPPING)
    (destination / 'source.json').write_text(json.dumps(source, indent=2), encoding='utf-8')
    summaries = []
    with exclusive_replay():
        for fixture in fixtures:
            if fixture == 'retained-sizeable':
                register=json.loads((ROOT/'baseline/manifest.json').read_text())
                resource=next(r for r in register['retained_resources'] if r['path'].endswith('block1-selected-consumers/input.json'))
                path=Path(resource['path'])
                if file_hash(path)!=resource['sha256']:raise ValueError('Retained sizeable artifact changed')
                payload=json.loads(path.read_text(encoding='utf-8'))['engine_input']
                fixture='retained-sizeable.json'
            else:
                path = ROOT / 'mta/fixtures' / fixture
                if path.parent != ROOT / 'mta/fixtures' or path.suffix != '.json':
                    raise ValueError('Select an existing named fixture, not another input path')
                payload = json.loads(path.read_text(encoding='utf-8'))
            evidence = dict(fixture=fixture, artifact_sha256=file_hash(path),
                            input_sha256=checksum(payload), input=payload,
                            scope='current-day engine; no temporal/API claim')
            started = time.monotonic()
            try:
                evidence['legacy'] = execute_r1_legacy(payload)
                evidence['modern'] = storage(calculate_current_day(payload))
                contracts = compare(evidence['legacy']['checkpoints'], evidence['modern'], **options(payload))
                evidence['contracts'] = contracts
                evidence['status'] = 'PASS' if all(c['status'] == 'PASS' for c in contracts.values()) else 'FAIL'
                evidence['failures'] = [k for k,v in contracts.items() if v['status'] != 'PASS']
            except Exception:
                evidence.update(status='ERROR', error=traceback.format_exc())
            evidence['seconds'] = round(time.monotonic()-started, 3)
            (destination / fixture).write_text(json.dumps(evidence, indent=2, default=str), encoding='utf-8')
            summary = {k:evidence[k] for k in ('fixture', 'status', 'seconds')}
            summary.update(comparisons=len(evidence.get('contracts', {})),
                           failures=evidence.get('failures', []),
                           populations={k:len(v) for k,v in evidence.get('modern',{}).items()},
                           error=evidence.get('error'))
            summaries.append(summary)
            (destination / 'summary.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
            print(json.dumps(summary), flush=True)
            if evidence['status'] != 'PASS':
                # Stop at earliest divergence; do not iterate fixtures to find
                # an easier passing substitute for the failed contract.
                return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination')
    parser.add_argument('fixtures', nargs='+')
    args = parser.parse_args()
    raise SystemExit(0 if replay(args.destination, args.fixtures) else 1)
