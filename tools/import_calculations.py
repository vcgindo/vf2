"""One-time mechanical extraction of pure calculation functions, never old ORM.

The output is normal editable application source, not a runtime dependency on
the old checkout. Import only the transitive Python dependency closure needed
by the current-day producer. Record every originating Git blob and transformation.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'F:/vflow_integrated'
REVISION = '66a77735d3f3f9a9becf4c87a08ae7827900cf84'


def read(path):
    return subprocess.check_output(['git', '-C', SOURCE, 'show', f'{REVISION}:{path}']).decode('utf-8-sig')


def write_new(path, content):
    target = ROOT / path
    if target.exists():
        raise ValueError(f'Refusing to replace existing implementation: {path}')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.replace('\r\n', '\n'), encoding='utf-8')


def extract():
    manifest = []
    pending = ['mta.application.r1_input', 'mta.application.r1_calculation', 'mta.application.rrr',
               'mta.domain.r1_current_day', 'mta.domain.r1_requirement_bands',
               'mta.domain.remaining_capabilities']
    visited = set()
    while pending:
        module = pending.pop()
        if module in visited:
            continue
        visited.add(module)
        if not module.startswith(('mta.domain.', 'mta.application.')):
            raise ValueError(f'Non-pure dependency must be reviewed, not imported: {module}')
        path = module.replace('.', '/') + '.py'
        source = read(path)
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith('django'):
                    raise ValueError(f'Unexpected Django coupling: {path}:{node.lineno}')
                if node.module.startswith('mta.'):
                    pending.append(node.module)
        write_new(path, source)
        manifest.append({'path': path, 'source_path': path,
                         'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                         'transformation': 'UTF8/LF only; functions unchanged'})
    source = read('mta/application/r1_run.py')
    functions = {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body
                 if isinstance(n, ast.FunctionDef)}
    names = ['_as_json', '_pso_inputs', '_bifurcation_rows', '_bpp_order_rows',
             '_requirement_band_rows', '_source_bor_rows', '_pick_rows']
    selected = '\n\n\n'.join(functions[name] for name in names) + '\n'
    replacements = {
        'def _pso_inputs(prepared, requirement_rows: list[dict], run)':
            'def _pso_inputs(prepared, requirement_rows: list[dict], normal_rows)',
        'list(RrrAllocationRecord.objects.filter(run=run).order_by("sku_id", "parent_location_id", "location_code"))':
            'sorted(normal_rows, key=lambda r: (r.sku_id, r.parent_location_id, r.location_code))',
        'def _bifurcation_rows(prepared, requirement_rows: list[dict], run, pso_rows)':
            'def _bifurcation_rows(prepared, requirement_rows: list[dict], normal_rows, pso_rows)',
        'RrrAllocationRecord.objects.filter(run=run)': 'normal_rows',
        'def _source_bor_rows(prepared, payload: dict, requirement_rows: list[dict], run)':
            'def _source_bor_rows(prepared, payload: dict, requirement_rows: list[dict], band_rows)',
        '(row.result["sku_code"], row.result["location_code"]): row.result\n        for row in RunCapabilityOutputRecord.objects.filter(run=run, capability="r1_requirement_band")':
            '(row["sku_code"], row["location_code"]): row\n        for row in band_rows',
        'def _pick_rows(run, logistics: dict, *, remaining=False)':
            'def _pick_rows(bifurcation_rows, logistics: dict, *, remaining=False)',
        '(row.result["sku_code"], row.result["location_code"], row.result["parent_location_code"]): row.result\n        for row in RunCapabilityOutputRecord.objects.filter(run=run, capability="r1_ration_bifurcation")':
            '(row["sku_code"], row["location_code"], row["parent_location_code"]): row\n        for row in bifurcation_rows',
    }
    for before, after in replacements.items():
        if before not in selected:
            raise ValueError('Extraction boundary changed: ' + before)
        selected = selected.replace(before, after)
    if '.objects' in selected:
        raise ValueError('A persistence dependency remains in the pure calculation')
    header = '''"""Current-day projections extracted from pinned R1 functions.

Only ORM reads were replaced with explicit produced-row arguments. See
baseline/calculation-reuse.json. No copied persistence/audit framework.
"""
from datetime import date
from decimal import Decimal, ROUND_CEILING
from mta.application.r1_input import resolve_r1_vehicle_mappings
from mta.application.r1_importer_master import _sql_key
from mta.domain.r1_current_day import PsoRationInput, RationedRequirement, bifurcate_rationed_requirement
from mta.domain.r1_requirement_bands import RequirementBandInput, calculate_requirement_bands
from mta.domain.remaining_capabilities import calculate_bor, calculate_bor_oa, calculate_pick_list

'''
    write_new('mta/planning/projections.py', header + selected)
    manifest.append({'path': 'mta/planning/projections.py', 'source_path': 'mta/application/r1_run.py',
                     'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                     'functions': names, 'replacements': replacements})
    for package in ('mta/application', 'mta/domain', 'mta/planning'):
        write_new(package + '/__init__.py', '')
    write_new('baseline/calculation-reuse.json', json.dumps({
        'revision': REVISION, 'acceptance': 'NOT_CERTIFIED', 'files': manifest}, indent=2) + '\n')
    print(f'Extracted {len(visited)} pure dependency modules and7 projection functions; no old ORM')


if __name__ == '__main__':
    extract()
