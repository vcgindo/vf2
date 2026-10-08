"""Rollback-only native completion qualification; never a complete-day run.

Small declared relational fixtures use exact typed bags since native SELECT *
has no ordering contract. All observed sequences/columns/cells are retained.
This does not change full31 acceptance and uses the qualified bounded standalone Python scalar adapters.
"""
import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.domain import complete_daily_completion as completion
from mta.domain import complete_daily_scalars as scalars
from mta.serialization import storage
from parity.adapters.legacy.complete_daily_sql import namespace, data_directory, preflight_scripts
from parity.verify_complete_daily_producers import (FixtureSQL, compare_rows, scalar_binding,
    native_context, NATIVE_COLLATION, preflight_fixture_suite)

OWNER = 'fdc5bc5e-4d68-4b3a-b8e6-d2754df0e2f4'
OUTPUT_ROOT = Path('D:/freshvcf-build/complete-daily-assessment')
SETUP = OUTPUT_ROOT / 'sql-setup-production-a001.json'
SOURCE = Path('F:/VFlow_Local/local-runtime/mta-engine')
NOW = datetime(2026, 6, 6)
PATHS = {
    'reset': ('Importer', 'Scripts/Importer/ResetBatchExecutionFlag.sql'),
    'BPR': ('Importer', 'Scripts/BPR/ValidateBPRBatchExecutionFlags.sql'),
    'ALL': ('Importer', 'Scripts/Importer/ValidateBatchExecutionFlags.sql'),
    'history': ('BPR', 'Scripts/BPR/ClearHistoryData_BPR.sql'),
    'failure-clear': ('BPR', 'Scripts/BPR/ClearTableForBPRBatchExecutionFailure.sql'),
}
FLAG_TABLES = (('Importer', 'ScriptExecutedFlag'), ('Importer', 'ImporterSettingsTbl'))
HISTORY = {'DailyConsumption': 'ReportDate', 'BPRReport_RemarkDetails': 'RemarkDate',
           'OpenExpeditRequestRemarksHistory': 'RemarkDate', 'InTransitWhereAboutsRemarks': 'RemarksDate'}
CLEAR = ('BPR_Table', 'SupplierDispatchReq', 'vf_PickListReport', 'vf_RationedReqReport')


IMPLEMENTATION_FILES = ('mta/domain/complete_daily_completion.py',
    'mta/domain/complete_daily_scalars.py',
    'mta/serialization.py', 'parity/verify_complete_daily_completion.py',
    'parity/verify_complete_daily_producers.py', 'parity/adapters/legacy/complete_daily_sql.py',
    'parity/legacy_isolation.py')


def implementation_pins():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in IMPLEMENTATION_FILES}


def guard_options(owner, output):
    if owner != OWNER:
        raise ValueError('Only the approved new complete-day qualification owner is permitted')
    output = Path(output).resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()) or output.suffix != '.json':
        raise ValueError('Completion qualification requires an owned JSON evidence path')
    if output.exists():
        raise FileExistsError('Refusing to overwrite qualification evidence')
    return output


def prepare(owner, isolation):
    """All source/configuration identity checks precede any fixture mutation."""
    if isolation._lease is not None:
        raise ValueError('Cannot bind an owner during an active replay lease')
    mapping, directory = namespace(owner), data_directory(owner)
    setup = json.loads(SETUP.read_text())
    if (setup['owner_id'] != owner or setup['namespace'] != mapping
            or Path(setup['data_directory']).resolve() != directory.resolve()
            or setup.get('schema_only') is not True or setup.get('business_invocations') != 0):
        raise ValueError('Explicit owned schema-only setup receipt differs')
    manifest_path = ROOT / 'baseline/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    pins = {row['path']: row['sha256'] for row in manifest['engine_sources']}
    isolation.MAPPING.clear()
    isolation.MAPPING.update(mapping)
    isolation.DATA = directory
    variables = dict(RunDateTime=NOW.isoformat(), DailyConsumptionHorizonBPR=2,
                     BPR_RemarkHorizon=1,
                     ScriptExecutionFlagQuery='UPDATE ' + mapping['VFTEST_Importer']
                        + '.dbo.ScriptExecutedFlag SET IsScriptExecuted=1 WHERE ScriptName=')
    entries = []
    for role, path in PATHS.values():
        canonical = (SOURCE / path).as_posix()
        if canonical not in pins:
            raise ValueError('Canonical completion source is not registered: ' + path)
        entries.append(dict(source_path=canonical, source_sha256=pins[canonical],
                            role=role, variables=variables))
    prepared = preflight_scripts(entries, owner_id=owner, namespace=mapping)
    return dict(zip(PATHS, prepared)), dict(setup_path=str(SETUP),
        setup_sha256=hashlib.sha256(SETUP.read_bytes()).hexdigest(),
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        implementation_path=str(Path(completion.__file__).resolve()),
        implementation_sha256=hashlib.sha256(Path(completion.__file__).read_bytes()).hexdigest())


def execute_native(raw, script, isolation, observations):
    """Pinned nested script scope inside caller's rollback-only transaction."""
    if hashlib.sha256(Path(script.source_path).read_bytes()).hexdigest() != script.source_sha256:
        raise ValueError('Canonical source drift after completion preflight')
    receipt = dict(path=script.source_path, sha256=script.source_sha256, role=script.role,
                   status='STARTED', resultsets=[])
    observations.append(receipt)
    raw.execute('USE ' + isolation.MAPPING['VFTEST_' + script.role])
    try:
        for batch in re.split(r'^\s*GO\s*$', script.sql, flags=re.M | re.I):
            if not batch.strip():
                continue
            cursor = raw.cursor()
            try:
                cursor.execute('EXEC sys.sp_executesql ?', batch)
                caught = False
                while True:
                    if cursor.description:
                        fields = [column[0] for column in cursor.description]
                        rows = [list(row) for row in cursor.fetchall()]
                        # Resultsets retain ordinal labels, including duplicates.
                        receipt['resultsets'].append(dict(fields=fields, rows=storage(rows),
                            python_types=[[type(value).__name__ for value in row] for row in rows]))
                        caught |= bool(rows) and any(str(field).lower() in
                            ('error', 'errornumber', 'errormessage') for field in fields)
                    if not cursor.nextset():
                        break
                if caught:
                    raise ValueError('Canonical completion SQL returned a CATCH error resultset')
            finally:
                cursor.close()
        receipt['status'] = 'SUCCEEDED'
    except Exception as error:
        receipt.update(status='FAILED', failure_type=type(error).__name__, failure=str(error))
        raise


def callbacks(raw, sql, probes):
    compared_fields = {('ScriptExecutedFlag', 'ScriptName'), ('ScriptExecutedFlag', 'ModuleName'),
                       ('ImporterSettingsTbl', 'Parameter')}
    for table, field in compared_fields:
        native = next(c for c in sql.schema('Importer', table) if c['name'] == field)
        if native['collation'] != NATIVE_COLLATION:
            raise ValueError('Fixture field collation differs from qualified scalar domain: ' + field)
    return scalars.ascii_equal, scalars.parse_datetime, scalars.datetime_to_nvarchar


def flag_cases():
    flag = lambda name, critical=True, executed=True, module='BPR': dict(
        ScriptName=name, IsScriptCritical=critical, IsScriptExecuted=executed, ModuleName=module)
    settings = lambda stamp=NOW.isoformat(): [dict(Parameter='BatchFileExecutionDate', Value=stamp),
        dict(Parameter='IsBatchFileExecuted', Value='stale'),
        dict(Parameter='IsBPRBatchFileExecuted', Value='stale')]
    markers = [flag('ResetBatchExecutionFlag.sql', False),
               flag('ValidateBPRBatchExecutionFlags', False, False),
               flag('VALIDATEBPRBATCHEXECUTIONFLAGS ', False, False),
               flag('ValidateBPRBatchExecutionFlags.sql', False, False),
               flag('ValidateBatchExecutionFlags.sql', False, False)]
    common = [flag('required.sql'), flag('optional.sql', False, False),
              flag('null-execution.sql', True, None), flag('null-critical.sql', None, False),
              flag(None, None, None, None)] + markers
    yield 'reset-null-duplicate-native-marker', ('reset', 'BPR', 'ALL'), common + [dict(common[0])], settings() + [dict(Parameter='IsBatchFileExecuted', Value='duplicate')]
    yield 'current-optional-null-and-literal-marker', ('BPR', 'ALL'), common, settings()
    yield 'stale-date', ('BPR', 'ALL'), common, settings('2026-06-05T00:00:00')
    yield 'missing-date-and-settings', ('BPR', 'ALL'), common, [dict(Parameter='IsBatchFileExecuted', Value='stale')]
    yield 'module-pending-only', ('BPR', 'ALL'), common + [flag('ImporterPending.sql', True, False, 'Importer')], settings()
    yield 'critical-bpr-pending', ('BPR', 'ALL'), common + [flag('BPRPending.sql', True, False)], settings()
    yield 'null-module-pending', ('BPR', 'ALL'), common + [flag('NULLMODULE.sql', True, False, None)], settings()
    yield 'duplicate-date-exists-current', ('BPR', 'ALL'), common, settings() + [dict(Parameter='BatchFileExecutionDate', Value='2026-06-05T00:00:00')]
    yield 'missing-marker-no-insertion', ('reset', 'BPR', 'ALL'), [], settings()


def histories():
    cutoff = NOW - timedelta(days=1)
    rows = {}
    for name, field in HISTORY.items():
        if name == 'DailyConsumption':
            dates = [(NOW - timedelta(days=d)).date() for d in (3, 2, 1)]
        else:
            dates = [cutoff - timedelta(seconds=1), cutoff, cutoff + timedelta(hours=12), NOW]
            if name in ('OpenExpeditRequestRemarksHistory', 'InTransitWhereAboutsRemarks'):
                dates.append(None)
        rows[name] = [dict(SKUCode='UNIT', WhCode='W', **{field: value}) for value in dates]
        rows[name].append(dict(rows[name][-1]))
    return rows


def population_snapshot(sql, keys):
    return {key: sql.rows(*key) for key in keys}


def compare(sql, wanted, reports):
    for key, rows in wanted.items():
        report = compare_rows(sql.rows(*key), rows, sql.schema(*key))
        reports['.'.join(key)] = report
        if report['status'] != 'PASS':
            raise ValueError('Exact typed fixture population mismatch: ' + '.'.join(key))


def qualify(raw, isolation, prepared, name, kind, declared, actions=()):
    sql = FixtureSQL(raw, isolation)
    report = dict(name=name, kind=kind, status='STARTED',
        fixture_declaration='small synthetic unit contract tables, not frozen daily facts',
        declared=[dict(role=k[0], table=k[1], rows=storage(v)) for k, v in declared.items()],
        inputs=[], filler_policy=sql.fills, probes=[], checkpoints=[], sql_receipts=[])
    try:
        for key, rows in declared.items():
            sql.load(*key, rows)
        before = population_snapshot(sql, declared)
        report['inputs'] = [dict(role=k[0], table=k[1], schema=sql.schema(*k), rows=storage(v)) for k, v in before.items()]
        equal, parse, format_datetime = callbacks(raw, sql, report['probes'])
        wanted = before
        if kind == 'flags':
            for action in actions:
                flags, settings = wanted[FLAG_TABLES[0]], wanted[FLAG_TABLES[1]]
                if action == 'reset':
                    modern = completion.reset_batch_flags(flags, settings, NOW, equal=equal, format_datetime=format_datetime)
                else:
                    modern = completion.validate_batch_flags(flags, settings, NOW, kind=action, equal=equal, parse_datetime=parse)
                wanted = {FLAG_TABLES[0]: modern['ScriptExecutedFlag'], FLAG_TABLES[1]: modern['ImporterSettingsTbl']}
                execute_native(raw, prepared[action], isolation, report['sql_receipts'])
                checkpoint = dict(action=action, comparisons={})
                report['checkpoints'].append(checkpoint)
                compare(sql, wanted, checkpoint['comparisons'])
        else:
            populations = {k[1]: v for k, v in before.items() if k[0] == 'BPR'}
            if kind == 'history':
                modern = completion.prune_bpr_history(populations, populations['LastBatchRunTbl'], consumption_days=2, remark_days=1)
                marker = 'ClearHistoryData_BPR.sql'
            else:
                modern = completion.clear_failed_bpr_reports(populations)
                marker = 'ClearTableForBPRBatchExecutionFailure.sql'
            wanted = {('BPR', k): v for k, v in modern.items()}
            wanted[FLAG_TABLES[0]] = completion.mark_script_executed(before[FLAG_TABLES[0]], marker, equal=equal)
            execute_native(raw, prepared[kind], isolation, report['sql_receipts'])
            checkpoint = dict(action=kind, comparisons={})
            report['checkpoints'].append(checkpoint)
            compare(sql, wanted, checkpoint['comparisons'])
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
        # No retry: retain native partial effects before the mandatory rollback.
        try:
            report['native_after_error'] = [dict(role=k[0], table=k[1], rows=storage(sql.rows(*k))) for k in declared]
        except Exception as read_error:
            report['failure_readback_error'] = str(read_error)
    return report


def fixture_cases():
    for name, actions, flags, settings in flag_cases():
        yield name, 'flags', {FLAG_TABLES[0]: flags, FLAG_TABLES[1]: settings}, actions
    marker = lambda name: {FLAG_TABLES[0]: [dict(ScriptName=name, IsScriptExecuted=False,
                              IsScriptCritical=True, ModuleName='BPR')]}
    for name, last in [('history-inclusive-midnight-null-dates', [dict(LastRunDate=NOW)]),
                       ('history-empty-scalar-null-cutoff', [])]:
        declared = {('BPR', k): v for k, v in histories().items()}
        declared[('BPR', 'LastBatchRunTbl')] = last
        declared.update(marker('ClearHistoryData_BPR.sql'))
        yield name, 'history', declared, ()
    declared = {('BPR', name): [dict(SKUCode='UNIT', WhCode='W')] * 2 for name in CLEAR}
    declared[('BPR', 'ProdOrderSuggestions')] = [dict(SKUCode='KEEP', PlantCode='P')]
    declared.update(marker('ClearTableForBPRBatchExecutionFailure.sql'))
    yield 'failure-clear-four-only-duplicate-populations', 'failure-clear', declared, ()


def run(owner, output):
    output = guard_options(owner, output)
    from parity import legacy_isolation as isolation
    prepared, identities = prepare(owner, isolation)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    receipt = dict(schema='complete-daily-completion-qualification-v1', owner=owner,
        namespace=namespace(owner), data_directory=str(data_directory(owner)), status='STARTED',
        identities=identities, implementation_pins=implementation_pins(),
        scalar_adapters=scalar_binding(), sources={key: dict(path=value.source_path, sha256=value.source_sha256)
            for key, value in prepared.items()}, cases=[],
        scope='rollback-only small completion fixtures; zero full business-day invocations',
        comparison_policy='all columns, NULLs, duplicate occurrences and native types; exact relational bag',
        limitations=['does not alter full31 positional acceptance',
            'standalone adapters qualified only for their declared bounded ASCII/date domain',
            'native NOT NULL settings/LastRunDate do not permit NULL row fixtures; empty scalar tests NULL cutoff',
            'resource envelope enforced externally by controller'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as file:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                receipt['schema_receipts'] = [json.loads((data_directory(owner) / (db + '-schema.json')).read_text())
                    for db in namespace(owner).values()]
                with isolation.connection('VFTEST_BPR') as raw:
                    receipt['native_context'] = native_context(raw, isolation)
                    cases = list(fixture_cases())
                    receipt['fixture_preflight'] = preflight_fixture_suite(FixtureSQL(raw, isolation),
                        [(name, kind, kind, declared) for name, kind, declared, _ in cases])
                    if receipt['fixture_preflight']['status'] != 'PASS':
                        raise ValueError('Entire completion fixture suite failed native schema audit before mutation')
                    for name, kind, declared, actions in cases:
                        sql = FixtureSQL(raw, isolation)
                        baseline = population_snapshot(sql, declared)
                        original_scratch = sql.scratch()
                        raw.raw.autocommit = False
                        try:
                            case = qualify(raw, isolation, prepared, name, kind, declared, actions)
                            receipt['cases'].append(case)
                        finally:
                            raw.rollback()
                            raw.raw.autocommit = True
                        case['outer_rollback'] = raw.execute('SELECT @@TRANCOUNT').fetchval() == 0
                        case['seed_preservation'] = {}
                        compare(sql, baseline, case['seed_preservation'])
                        restored_scratch = sql.scratch()
                        if set(restored_scratch) != set(original_scratch):
                            raise ValueError('Completion scratch roster changed')
                        case['scratch_preservation'] = {}
                        compare(sql, {('Intermediate', key): rows for key, rows in original_scratch.items()},
                                case['scratch_preservation'])
                        if case['status'] != 'PASS' or not case['outer_rollback']:
                            raise ValueError('Stopped at first completion qualification failure: ' + name)
            receipt['status'] = 'PASS'
        except Exception as error:
            receipt.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
        finally:
            receipt['implementation_identity_unchanged'] = implementation_pins() == receipt['implementation_pins']
            if not receipt['implementation_identity_unchanged']:
                receipt.update(status='FAIL', failure='Modern implementation changed during qualification')
            json.dump(storage(receipt), file, indent=2, ensure_ascii=False, allow_nan=False)
            file.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    options = parser.parse_args()
    result = run(options.owner, options.output)
    print(json.dumps(dict(status=result['status'], cases=len(result['cases']), output=str(options.output))))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
