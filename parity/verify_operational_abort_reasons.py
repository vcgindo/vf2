"""Mapped GetUnavailableFiles producer proof; rollback only, no client hooks."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from mta.domain.complete_daily_fullkit import unavailable_file_reasons
from mta.domain.complete_daily_scalars import ascii_equal
from mta.serialization import storage
from parity.verify_operational_bor import BorFixtureSQL, strict_rows, EVIDENCE, pin
from parity.verify_complete_daily_pick_files import prepare
from parity.verify_complete_daily_producers import OWNER, SOURCE, native_context
from parity.verify_complete_daily_completion import execute_native
from parity.adapters.legacy.complete_daily_sql import namespace, preflight_scripts


def run(owner, output):
    output = Path(output).resolve()
    if owner != OWNER or not output.is_relative_to(EVIDENCE.resolve()) or output.exists():
        raise ValueError('New owned evidence path and exact fixture owner required')
    from parity import legacy_isolation as isolation
    _, setup = prepare(owner, isolation)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    path = SOURCE / 'Scripts/Importer/GetUnavailableFiles.sql'
    manifest = json.loads((ROOT / 'baseline/manifest.json').read_text())
    expected = next(row['sha256'] for row in manifest['engine_sources'] if row['path'] == path.as_posix())
    mapping = namespace(owner)
    script = preflight_scripts([dict(source_path=path.as_posix(), source_sha256=expected,
        role='Importer', variables=dict(RunDateTime='2026-06-06T00:00:00', FileType='DataFiles',
            ScriptExecutionFlagQuery='UPDATE '+mapping['VFTEST_Importer']+
            '.dbo.ScriptExecutedFlag SET IsScriptExecuted=1 WHERE ScriptName='))],
        owner_id=owner, namespace=mapping)[0]
    files = ('mta/domain/complete_daily_fullkit.py', 'parity/verify_operational_abort_reasons.py')
    code = {name: pin(ROOT / name) for name in files}
    report = dict(status='STARTED', setup=setup, owner=owner, source_sha256=expected,
                  code_pins=code, cases=[])
    missing = dict(Path='owned', FileName='daily.csv', Type='DataFiles', Exists=False,
                   ResolvedPath='owned', ResolvedFileName='daily.csv')
    cases = [('empty', []), ('filtered', [missing, missing | dict(Exists=True),
              missing | dict(Type='GoAheadFiles')]),
             ('null-concatenation', [missing, missing | dict(ResolvedPath=None)])]
    with output.open('x', encoding='utf-8') as stream:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                with isolation.connection('VFTEST_Importer') as raw:
                    report['native_context'] = native_context(raw, isolation)
                    sql = BorFixtureSQL(raw, isolation)
                    tables = ('CriticalFiles', 'RunAbortReasons', 'ScriptExecutedFlag')
                    originals = {name: sql.rows('Importer', name) for name in tables}
                    for name, rows in cases:
                        item = dict(name=name, sql=[])
                        report['cases'].append(item)
                        raw.raw.autocommit = False
                        try:
                            sql.load('Importer', 'CriticalFiles', rows)
                            sql.load('Importer', 'RunAbortReasons', [dict(FileId=99,
                                RunDateTime=datetime(2026, 6, 5), Reason='retained')]*2)
                            sql.load('Importer', 'ScriptExecutedFlag', [dict(
                                ScriptName='GetUnavailableFiles.sql', ModuleName='Importer',
                                IsScriptExecuted=False, IsScriptCritical=True)])
                            opening = sql.rows('Importer', 'RunAbortReasons')
                            resolved = sql.rows('Importer', 'CriticalFiles')
                            item['opening'], item['resolved'] = storage(opening), storage(resolved)
                            native_error = modern_error = None
                            try:
                                execute_native(raw, script, isolation, item['sql'])
                            except ValueError as error:
                                native_error = str(error)
                            try:
                                wanted = unavailable_file_reasons(opening, resolved, 'DataFiles',
                                    '2026-06-06T00:00:00', equal=ascii_equal)
                            except ValueError as error:
                                modern_error = str(error)
                                wanted = opening
                            item.update(native_error=native_error, modern_error=modern_error)
                            item['comparison'] = strict_rows(sql, ('Importer', 'RunAbortReasons'), wanted)
                            errors = [row for result in item['sql'][0]['resultsets']
                                      for row in result['rows'] if 'ErrorNumber' in result['fields']]
                            error_ok = (not native_error and not modern_error) if name != 'null-concatenation' else (
                                native_error is not None and modern_error is not None
                                and any(row[1] == 515 for row in errors))
                            item['status'] = 'PASS' if error_ok and item['comparison']['status'] == 'PASS' else 'FAIL'
                        finally:
                            raw.rollback()
                            raw.raw.autocommit = True
                        item['preservation'] = {table: strict_rows(sql, ('Importer', table), old)
                                                for table, old in originals.items()}
                        if any(value['status'] != 'PASS' for value in item['preservation'].values()):
                            raise ValueError('Rollback changed retained populations')
            report['status'] = 'PASS' if all(item['status'] == 'PASS' for item in report['cases']) else 'FAIL'
        except Exception as error:
            report.update(status='FAIL', error=type(error).__name__+': '+str(error))
        finally:
            report['pins_unchanged'] = pin(path) == expected and code == {name: pin(ROOT / name) for name in files}
            if not report['pins_unchanged']:
                report['status'] = 'FAIL'
            json.dump(storage(report), stream, indent=2)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = run(args.owner, args.output)
    print(json.dumps(dict(status=report['status'], cases=len(report['cases']), error=report.get('error'))))
    raise SystemExit(report['status'] != 'PASS')
