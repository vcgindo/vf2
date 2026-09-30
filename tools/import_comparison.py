"""Extract existing declared field/type contracts without the old execution harness."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVISION = '66a77735d3f3f9a9becf4c87a08ae7827900cf84'


def source(path):
    return subprocess.check_output(['git', '-C', 'F:/vflow_integrated', 'show', f'{REVISION}:{path}']).decode('utf-8-sig')


def main():
    original = source('parity/run_r1.py')
    tree = ast.parse(original)
    names = {'number', 'colour', '_rows', 'normalize_legacy', 'normalize_modern',
             'normalize_master_checkpoints', 'compare'}
    exclude = {'ROOT', 'FIXTURE_ROOT', 'DEMO_FIXTURE_ROOT', 'R1_FIXTURE_EXPECTATIONS', 'LEGACY_FLAWS', 'R1_OPEN_GAPS'}
    parts = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            parts.append(ast.get_source_segment(original, node))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            assigned = {v.id for v in ast.walk(node) if isinstance(v, ast.Name) and isinstance(v.ctx, ast.Store)}
            if assigned.isdisjoint(exclude):
                parts.append(ast.get_source_segment(original, node))
        elif isinstance(node, ast.FunctionDef) and node.name in names:
            parts.append(ast.get_source_segment(original, node))
    files = {'parity/current_day.py': '\n\n'.join(parts) + '\n',
             'parity/models.py': source('parity/models.py'),
             'parity/comparators/exact.py': source('parity/comparators/exact.py'),
             'parity/__init__.py': '', 'parity/comparators/__init__.py': ''}
    for path, content in files.items():
        target = ROOT / path
        if target.exists():
            raise ValueError(f'Refusing to overwrite {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.replace('\r\n', '\n'), encoding='utf-8')
    (ROOT / 'baseline/comparison-reuse.json').write_text(json.dumps({
        'revision': REVISION, 'source_path': 'parity/run_r1.py',
        'source_sha256': hashlib.sha256(original.encode()).hexdigest(),
        'functions': sorted(names), 'transformation': 'Pure comparison and constants only; no runner/oracle execution'}, indent=2))


def extract_raw():
    selected = {
        'run_r1_master_validation': {'_bag', 'compare_master_validation'},
        'run_r1_supplier_validation': {'compare_supplier_validation', 'compare_supplier_state'},
        'run_r1_daily_validation': {'compare_daily_validation'},
    }
    receipts = []
    for module, names in selected.items():
        text = source('parity/' + module + '.py')
        nodes = ast.parse(text).body
        imports = [ast.get_source_segment(text, n) for n in nodes if
                   isinstance(n, ast.ImportFrom) and (n.module or '').startswith('mta.application')]
        functions = [ast.get_source_segment(text, n) for n in nodes
                     if isinstance(n, ast.FunctionDef) and n.name in names]
        target = ROOT / 'parity' / (module + '.py')
        if target.exists():
            raise ValueError('Already extracted ' + str(target))
        target.write_text('from collections import Counter\nimport json\n' + '\n'.join(imports + functions) + '\n', encoding='utf-8')
        receipts.append({'source': 'parity/' + module + '.py',
                         'sha256': hashlib.sha256(text.encode()).hexdigest(), 'functions': sorted(names)})
    (ROOT / 'baseline/raw-comparison-reuse.json').write_text(json.dumps({
        'revision': REVISION, 'sources': receipts}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    import sys
    extract_raw() if '--raw' in sys.argv else main()
