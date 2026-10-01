"""Emit a reviewable patch for pure consumers from the registered Git snapshot.

No execution of the old application, ORM, generators or serving checkout.
Consumer reuse is provenance, not a claim of deployed API parity.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVISION = '66a77735d3f3f9a9becf4c87a08ae7827900cf84'
SOURCES = {}


def source(name):
    raw = subprocess.check_output(['git', '-C', 'F:/vflow_integrated', 'show', f'{REVISION}:{name}'])
    SOURCES[name] = hashlib.sha256(raw).hexdigest()
    return raw.decode('utf-8-sig').replace('\r\n', '\n')


def functions(original, names):
    nodes = [n for n in ast.parse(original).body if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise ValueError('Missing selected consumer function')
    return '\n\n'.join(ast.get_source_segment(original, n) for n in nodes) + '\n'


def main():
    delivery = source('mta/application/dbm_delivery.py')
    api = source('mta/api/legacy_compatibility.py')
    fulfillment = source('mta/application/planning_fulfillment_grid.py')
    fulfillment_constants = [n for n in ast.parse(fulfillment).body if isinstance(n,ast.Assign)
                            and any(isinstance(t,ast.Name) and t.id in ('ALIASES','COLUMNS') for t in n.targets)]
    custom = source('mta/application/planning_custom_grid.py')
    header = next(n for n in ast.parse(custom).body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'HEADERS' for t in n.targets))
    constants = [n for n in ast.parse(api).body if 68 <= n.lineno < 498]
    content = ('"""Pinned existing UI metadata and pure payload helpers; no old ORM."""\n'
               'from __future__ import annotations\nimport json\nfrom pathlib import Path\n\n'
               + ast.get_source_segment(custom, header).replace('HEADERS =', 'PLANNING_CUSTOM_HEADERS =', 1)
               + '\n\n' + '\n\n'.join(ast.get_source_segment(api, n) for n in constants)
               + '\n\n' + functions(api, {'_no_active_filters', '_filter_rows', '_pagination', '_page'}))
    files = {
        'mta/presentation/__init__.py': '"""Consumer adapters; calculated truth remains in mta.runtime."""\n',
        'mta/presentation/dbm.py': ('"""Pinned pure DBM consumer joins, not a second calculation engine."""\n'
            'from itertools import product\n\n' + functions(delivery, {'key', 'delivery_history', 'daily_graph', 'dbm_rows'})),
        'mta/presentation/btr.py': source('mta/domain/btr_views.py'),
        'mta/presentation/insights.py': source('mta/domain/dbm_insights.py'),
        'mta/presentation/rrr_types.py': source('mta/application/rrr_selected_response.py'),
        'mta/presentation/excess_grid.py': source('mta/application/planning_inventory_grid.py'),
        'mta/presentation/excess_charts.py': source('mta/application/planning_excess_charts.py'),
        'mta/presentation/fulfillment_grid.py': ('"""Pinned deployed-shaped Fulfilment aliases and nested order projection."""\n'
            'from collections import defaultdict\nfrom decimal import Decimal\n'
            'from mta.presentation.rrr import sql_key as _key\n\n'
            + '\n\n'.join(ast.get_source_segment(fulfillment,n) for n in fulfillment_constants)
            + '\n\n' + functions(fulfillment,{'fulfillment_grid_rows','fulfillment_grid_config'})),
        'mta/presentation/history.py': ('"""Pinned pure history aggregations for the existing frontend."""\n'
            'from collections import Counter, defaultdict\nfrom datetime import date\nfrom decimal import Decimal\n\n'
            + functions(api, {'_colour_counts', '_historical_availability', '_buffer_trend_graph'})),
        'mta/presentation/permissions.py': source('mta/application/legacy_permission_hierarchy.py'),
        'mta/presentation/legacy_ui.py': content,
    }
    for filename in ('rrr_selected_ui.json', 'expedite_selected_ui.json', 'git_selected_ui.json',
                     'excess_selected_ui.json', 'btr_selected_ui.json',
                     'mta_environment_configuration.json', 'mta_report_paths.json'):
        files['mta/config/' + filename] = source('mta/config/' + filename)
    files['baseline/consumer-reuse.json'] = json.dumps(dict(
        revision=REVISION, sources=SOURCES,
        outputs={name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()},
        transformation='Pure functions/configuration only; no old ORM, publication, calculation, authentication or generators',
        acceptance='NOT_YET_F3_ACCEPTED; deployed API/configuration and fresh runtime comparisons still required'), indent=2) + '\n'
    print('*** Begin Patch')
    for name, text in files.items():
        target = ROOT / name
        if target.exists():
            current = target.read_text(encoding='utf-8')
            if current == text:
                continue
            if name != 'baseline/consumer-reuse.json':
                raise ValueError('Refusing to overwrite changed consumer ' + name)
            prior = json.loads(current)
            for existing, expected in prior['outputs'].items():
                if hashlib.sha256((ROOT/existing).read_bytes().replace(b'\r\n',b'\n')).hexdigest() != expected:
                    raise ValueError('Existing reuse bytes changed: ' + existing)
            print('*** Update File: ' + target.as_posix())
            print('@@')
            print('\n'.join('-' + line for line in current.splitlines()))
            print('\n'.join('+' + line for line in text.splitlines()))
            continue
        print('*** Add File: ' + (ROOT / name).as_posix())
        print('\n'.join('+' + line for line in text.splitlines()))
    print('*** End Patch')


if __name__ == '__main__':
    main()
