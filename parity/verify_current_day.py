"""Fresh modern calculation against the retained, source-pinned legacy receipt."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from mta.planning.engine import calculate_current_day
from parity.current_day import compare


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(output_directory, persisted_output=None):
    root = Path(__file__).resolve().parents[1]
    baseline = json.loads((root / 'baseline/manifest.json').read_text())
    parent = next(r for r in baseline['retained_resources']
                  if r['path'].endswith('block1-selected-consumers/input.json'))
    artifact_path = Path(parent['path'])
    if file_hash(artifact_path) != parent['sha256']:
        raise ValueError('Retained input changed')
    artifact = json.loads(artifact_path.read_text(encoding='utf-8'))
    legacy_path = Path('F:/vflow_integrated/.local-stage7/block2-3004/fresh-legacy.json')
    legacy = json.loads(legacy_path.read_text(encoding='utf-8'))
    if checksum(artifact) != legacy['input_sha256']:
        raise ValueError('Retained legacy receipt has a different logical input')
    # Source files must still match both the frozen fresh baseline and the
    # retained oracle's embedded script identities. Missing provenance fails.
    engine_scripts = legacy['engine']['scripts']
    if not engine_scripts:
        raise ValueError('Missing legacy script provenance')
    for row in engine_scripts:
        path = Path(row['path'])
        if file_hash(path).lower() != row['sha256'].lower():
            raise ValueError(f'Retained oracle source changed: {path}')
        relative = path.relative_to(Path('F:/VFlow_Source_Backup/deployed-demo/MTA/V6/Scripts'))
        deployed = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts') / relative
        if file_hash(deployed).lower() != row['sha256'].lower():
            raise ValueError(f'Local deployed SQL differs: {deployed}')
    started = time.monotonic()
    if persisted_output:
        persisted_output = Path(persisted_output)
        receipt = json.loads((persisted_output.parent / 'receipt.json').read_text())
        modern = json.loads(persisted_output.read_text())
        if (receipt['artifact_digest'] != checksum(artifact)
                or receipt['input_digest'] != checksum(artifact['engine_input'])
                or receipt['output_digest'] != checksum(modern)):
            raise ValueError('Persisted output provenance mismatch')
    else:
        modern = calculate_current_day(artifact['engine_input'])
    comparison = compare(legacy['engine']['checkpoints'], modern, master_state_required=True)
    result = {
        'schema': 'freshvcf-current-day-comparison-v1',
        'status': 'PASS' if len(comparison) == 20 and all(r['status'] == 'PASS' for r in comparison.values()) else 'FAIL',
        'scope': 'sizeable processed-input current-day engine; no raw/temporal/API claim',
        'oracle': 'retained canonical execution; not a fresh legacy replay',
        'modern_execution': 'POSTGRESQL_READBACK' if persisted_output else 'PURE_CALCULATION',
        'input_path': str(artifact_path), 'input_sha256': parent['sha256'],
        'logical_input_sha256': checksum(artifact), 'legacy_receipt_sha256': file_hash(legacy_path),
        'modern_source': {str(p.relative_to(root)): file_hash(p)
                          for p in sorted((root / 'mta').rglob('*.py'))},
        'seconds': round(time.monotonic() - started, 3), 'contracts': comparison,
    }
    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'modern.json').write_text(json.dumps(modern, sort_keys=True, indent=2), encoding='utf-8')
    (destination / 'comparison.json').write_text(json.dumps(result, sort_keys=True, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'contracts': len(comparison),
                      'failures': [k for k,v in comparison.items() if v['status'] != 'PASS'],
                      'seconds': result['seconds'], 'evidence': str(destination)}))
    return result['status'] == 'PASS'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output_directory')
    parser.add_argument('--persisted-output')
    args = parser.parse_args()
    raise SystemExit(0 if verify(args.output_directory, args.persisted_output) else 1)
