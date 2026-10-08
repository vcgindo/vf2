"""Owned read-only sqlcmd literal formatting and four-file lifecycle proof.

This verifies serialization of already projected cells, not SQL business-query
ordering or producer parity. Four-report row parity has its separate receipt.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application.complete_daily_batch_files import sqlcmd_bytes, write_pick_reports, PICK_NAMES
from mta.application.complete_daily_pick_files import project_reports
from parity.verify_complete_daily_pick_files import fixture_cases, LOGISTIC, REMAINING
from parity.verify_complete_daily_producers import OWNER, guard_options
from parity.adapters.legacy.complete_daily_sql import namespace, data_directory

SQLCMD = Path('C:/Program Files/Microsoft SQL Server/Client SDK/ODBC/180/Tools/Binn/SQLCMD.EXE')
WRAPPER = Path('F:/VFlow_Local/local-runtime/mta-engine/Engine/PickListReports.bat')
WRAPPER_SHA = 'a47e9dc5ddb8e356ddaa121d320dd694d2aca44c58e0f51ecd60a3730d757b40'


def pin(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal_query(resultsets):
    # Only our validated projection types and literal values enter this query.
    sqlcmd_bytes(resultsets)
    statements = ["EXECUTE AS LOGIN = 'freshvcf_oracle_replay' WITH NO REVERT;", 'SET NOCOUNT ON;']
    for resultset in resultsets:
        for row in resultset['rows']:
            cells = []
            for value, kind in zip(row, resultset['types'], strict=True):
                literal = 'NULL' if value is None else ("N'" + value.replace("'", "''") + "'" if isinstance(value, str) else str(value))
                cells.append('CAST(' + literal + ' AS ' + kind + ')')
            statements.append('SELECT ' + ','.join(cells) + ';')
    return '\n'.join(statements) + '\n'


def run(owner, output):
    output = guard_options(owner, output)
    if os.name != 'nt' or ctypes.windll.kernel32.GetACP() != 1252:
        raise ValueError('This qualification requires the retained Windows CP1252 sqlcmd host')
    if pin(WRAPPER) != WRAPPER_SHA:
        raise ValueError('Canonical Pick file wrapper changed')
    from parity import legacy_isolation as isolation
    if isolation._lease is not None:
        raise ValueError('Cannot replace an active SQL lease')
    isolation.MAPPING.clear(); isolation.MAPPING.update(namespace(owner))
    isolation.DATA = data_directory(owner)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    root = output.with_suffix('')
    root.mkdir()
    output_dir, download_dir = root/'modern-output', root/'modern-download'
    output_dir.mkdir(); download_dir.mkdir()
    _, declared = fixture_cases()[0]
    reports = project_reports(logistic_pick_list=declared[LOGISTIC], pick_list_data_for_truck_formation=declared[REMAINING])
    for name in PICK_NAMES.values():
        (output_dir/name).write_bytes(b'old output')
        (download_dir/name).write_bytes(b'old download')
    receipt = dict(status='STARTED', owner=owner, wrapper_sha256=WRAPPER_SHA, sqlcmd_sha256=pin(SQLCMD),
        implementation_pins={name: pin(ROOT/name) for name in (
            'mta/application/complete_daily_batch_files.py', 'mta/application/complete_daily_pick_files.py',
            'parity/verify_batch_file_format.py', 'parity/verify_complete_daily_pick_files.py')},
        scope='literal typed-cell serialization and four-file delete/write/copy lifecycle; no business query/day',
        limitations=['direct CP1252 text and declared Pick result types only; best-fit/replacement and display truncation unqualified',
            'literal singleton SELECTs retain supplied cell order; no report-query ordering claim or new acceptance qualification'],
        cases=[])
    with output.open('x', encoding='utf-8') as stream:
        try:
            paths = write_pick_reports(reports, owned_root=root, output_folder=output_dir, download_folder=download_dir)
            with isolation.exclusive_replay(validate_schema=True):
                for item in paths:
                    kind = item['report']
                    query = root/(kind+'.sql')
                    query.write_bytes(literal_query(reports[kind]['resultsets']).encode('utf-16'))
                    native = root/(kind+'-native.csv')
                    command = [str(SQLCMD), '-C', '-E', '-S', 'localhost', '-d', namespace(owner)['VFTEST_BPR'],
                        '-i', str(query), '-o', str(native), '-s', ',', '-h-1', '-W']
                    result = subprocess.run(command, capture_output=True, timeout=30)
                    actual = native.read_bytes() if native.exists() else b''
                    modern, copied = Path(item['output']).read_bytes(), Path(item['download']).read_bytes()
                    passed = result.returncode == 0 and actual == modern == copied
                    receipt['cases'].append(dict(report=kind, status='PASS' if passed else 'FAIL',
                        query_sha256=pin(query), returncode=result.returncode, stdout_hex=result.stdout.hex(),
                        stderr_hex=result.stderr.hex(), native_sha256=hashlib.sha256(actual).hexdigest(),
                        modern_sha256=hashlib.sha256(modern).hexdigest(), copy_sha256=hashlib.sha256(copied).hexdigest(),
                        native_hex=actual.hex(), modern_hex=modern.hex()))
                    if not passed:
                        raise ValueError('Native batch bytes or download copy differ: ' + kind)
            receipt['status'] = 'PASS'
        except Exception as error:
            receipt.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
        finally:
            receipt['implementation_identity_unchanged'] = all(pin(ROOT/name) == sha for name, sha in receipt['implementation_pins'].items())
            if not receipt['implementation_identity_unchanged'] or pin(WRAPPER) != WRAPPER_SHA or pin(SQLCMD) != receipt['sqlcmd_sha256']:
                receipt.update(status='FAIL', failure='Implementation/tool/source identity changed')
            json.dump(receipt, stream, indent=2); stream.write('\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = run(args.owner, args.output)
    print(json.dumps(dict(status=report['status'], cases=len(report['cases']), output=str(args.output))))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)
