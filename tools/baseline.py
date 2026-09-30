"""Inventory approved local sources without loading customer rows or credentials."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LEGACY = Path('F:/VFlow_Local/local-runtime')
PRESERVED = Path('F:/VFlow_Source_Backup/deployed-demo/MTA')
PREVIOUS = Path('F:/vflow_integrated')
REVISION = '66a77735d3f3f9a9becf4c87a08ae7827900cf84'
DLL_HASH = '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346'
RESOURCES = (
    ('.local-stage7/block1-selected-consumers/input.json', 'sizeable processed/report metadata parent'),
    ('.local-demo/input/integrated_current_day.json', 'sizeable processed current-day input'),
    ('.local-stage7/block1-selected-consumers/permission-input-v1.json', 'retained permission scopes'),
    ('.local-stage7/block3-sizeable/v1/manifest.json', 'approved temporal extension manifest'),
    ('.local-stage7/block3-sizeable/v1/sizeable-input.json', 'full-depth external facts and opening state'),
    ('.local-stage7/block3-sizeable/v1/representative-bridge-input.json', 'shallow connected temporal facts'),
    ('.local-stage7/block3-sizeable/v1/full-depth-12day-replay.json', 'historical parity receipt, not fresh acceptance'),
    ('.local-stage7/block3/contract-freeze/effective-dbm-settings.json', 'captured effective DBM profile'),
    ('.local-stage7/block3/contract-freeze/effective-VFSettings.json', 'captured effective BPR profile'),
    ('.local-stage7/block3/contract-freeze/effective-ImporterSettingsTbl.json', 'captured effective importer profile'),
)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def describe(path, role):
    return dict(path=path.as_posix(), role=role, sha256=digest(path), bytes=path.stat().st_size)


def capture():
    destination = ROOT / 'baseline/manifest.json'
    if destination.exists():
        raise ValueError('Baseline already frozen; do not overwrite it to bless changes')
    runtime_dll = describe(LEGACY / 'mta-latest/VectorFlowAPIs.dll', 'canonical deployed API')
    preserved_dll = describe(PRESERVED / 'BackEndAPI/VectorFlowAPIs.dll', 'preserved deployed API')
    if runtime_dll['sha256'] != DLL_HASH or preserved_dll['sha256'] != DLL_HASH:
        raise ValueError('Canonical API identity mismatch')
    engine = LEGACY / 'mta-engine'
    source = []
    for folder, suffix in [('Engine', '.bat'), ('Scripts', '.sql')]:
        for path in sorted((engine / folder).rglob('*')):
            if path.is_file() and path.suffix.lower() == suffix:
                source.append(describe(path, 'canonical source; activation must be reconciled'))
    resources = [describe(PREVIOUS / path, role) for path, role in RESOURCES]
    trees = {p: subprocess.check_output(
        ['git', '-C', str(PREVIOUS), 'rev-parse', f'{REVISION}:{p}'], text=True).strip()
        for p in ('frontend', 'mto', 'user-service', 'mta')}
    value = dict(schema='freshvcf-baseline-v1', canonical_api=[runtime_dll, preserved_dll],
                 engine_sources=source, retained_resources=resources,
                 reuse={'revision': REVISION, 'git_trees': trees,
                        'status': 'reference implementation, not fresh-build acceptance'})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(f'Pinned {len(source)} source files and {len(resources)} retained resources')


def verify():
    value = json.loads((ROOT / 'baseline/manifest.json').read_text(encoding='utf-8'))
    rows = value['canonical_api'] + value['engine_sources'] + value['retained_resources']
    errors = [r['path'] for r in rows if not Path(r['path']).is_file() or digest(Path(r['path'])) != r['sha256']]
    if errors:
        raise ValueError('Baseline differs: ' + ', '.join(errors))
    print(f'PASS: {len(rows)} pinned resources unchanged (identity only, not parity)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['capture', 'verify'])
    args = parser.parse_args()
    {'capture': capture, 'verify': verify}[args.command]()
