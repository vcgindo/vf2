"""Transfer the pinned SQL-only oracle adapter, replacing its connection boundary.

No original runner is executed. Neither default VFTEST nor Block2 bindings are
available in this repository. Only explicit Fresh connections can be opened.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVISION = '66a77735d3f3f9a9becf4c87a08ae7827900cf84'


def extract():
    files = ['runner', 'r1_runner', 'r1_importer_master', 'r1_supplier_input', 'r1_daily_input']
    manifest = []
    for name in files:
        path = 'parity/adapters/legacy/' + name + '.py'
        original = subprocess.check_output(['git', '-C', 'F:/vflow_integrated', 'show', f'{REVISION}:{path}']).decode('utf-8-sig')
        text = original
        if name == 'runner':
            tree = ast.parse(original)
            function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'connection')
            old = ast.get_source_segment(original, function)
            text = text.replace(old, 'from parity.legacy_isolation import connection')
            text = text.replace('F:/VFlow_Source_Backup/deployed-demo/MTA/V6/Scripts',
                                'F:/VFlow_Local/local-runtime/mta-engine/Scripts')
        target = ROOT / path
        if target.exists():
            raise ValueError('Refusing overwrite: ' + path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text.replace('\r\n','\n'), encoding='utf-8')
        manifest.append({'path': path, 'sha256': hashlib.sha256(original.encode()).hexdigest(),
                         'transformation': 'Fresh-only connection and canonical runtime root' if name == 'runner' else 'LF only'})
    for path in ['parity/adapters/__init__.py', 'parity/adapters/legacy/__init__.py']:
        (ROOT / path).write_text('', encoding='utf-8')
    (ROOT / 'baseline/oracle-reuse.json').write_text(json.dumps({
        'revision': REVISION, 'files': manifest,
        'scope': 'SQL parity adapter only, never modern production engine'}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    extract()
