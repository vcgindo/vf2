"""Owned rollback-only native qualification of four required Pick reports.

Strict observed resultset/cell sequences remain in evidence. The direct human
four-file qualification allows only data-row bag equality for these unordered
batch exports; headers remain exact. No SQL ORDER BY or calculation change.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application import complete_daily_pick_files as projections
from mta.domain import complete_daily_scalars as scalars
from mta.domain.complete_daily_completion import mark_script_executed
from mta.serialization import storage
from parity.adapters.legacy.complete_daily_sql import namespace, data_directory, preflight_scripts
from parity.verify_complete_daily_completion import SETUP, execute_native
from parity.verify_complete_daily_producers import (OWNER, OUTPUT_ROOT, SOURCE,
    FixtureSQL, typed, compare_rows, guard_options, scalar_binding, native_context,
    NATIVE_COLLATION)

LOGISTIC = ('BPR', 'LogisticPickList')
REMAINING = ('BPR', 'PickListDataForTruckFormation')
FLAG = ('Importer', 'ScriptExecutedFlag')
SCRATCH = ('Intermediate', 'RemainingLogisticQtyDetails')
ORDER_APPROVAL = dict(question_id='call_5a75ffbc20224abb91987c31f6cb6ee7',
    answer='Approve this four-file ordering qualification',
    scope='four generic Pick batch files only; exact headers/cells/NULLs/duplicates; no sort; strict sequence evidence retained')
IMPLEMENTATION_FILES = ('mta/application/complete_daily_pick_files.py',
    'mta/domain/complete_daily_scalars.py', 'mta/domain/complete_daily_completion.py',
    'mta/serialization.py', 'parity/verify_complete_daily_pick_files.py',
    'parity/verify_complete_daily_completion.py', 'parity/verify_complete_daily_producers.py',
    'parity/adapters/legacy/complete_daily_sql.py', 'parity/legacy_isolation.py')


def implementation_pins():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in IMPLEMENTATION_FILES}


def fixture_cases():
    def picked(**overrides):
        row = dict(ParentWHCode='P', WHCode='W', LogisticLocation='L', TruckCount=1,
            VehicleName='V', TransportLoadType='Full', DispatchColor='Black', SKUCode='S',
            ColorWiseAlloction=2, TotalWeight=Decimal('1.250'), TotalVolume=Decimal('2.000'), IsTruckFormed=True)
        row.update(overrides)
        return row
    def residual(**overrides):
        row = dict(ParentWHCode='P', WHCode='W', LogisticLocation='L', DispatchColor='Black',
            SKUCode='S', ColorWiseAlloction=2, TotalWeight=Decimal('1.250'), TotalVolume=Decimal('2.000'))
        row.update(overrides)
        return row
    flags = [dict(ScriptName=Path(path).name, ModuleName='BPR', IsScriptExecuted=False,
                  IsScriptCritical=True) for path, _ in projections.SOURCES.values()]
    flags.append(dict(flags[0]))
    common = {FLAG: flags, SCRATCH: [dict(ParentWHCode='SCRATCH', WHCode='W', SKUCode='UNIT', Qty=1)]}
    mixed = dict(common)
    mixed[LOGISTIC] = [picked(), picked(), picked(DispatchColor='Red', ColorWiseAlloction=3),
        picked(VehicleName='V2', TransportLoadType='Partial', DispatchColor='Yellow', IsTruckFormed=False),
        picked(SKUCode='ZERO', ColorWiseAlloction=0, TotalWeight=Decimal('0.000'), TotalVolume=None, IsTruckFormed=None),
        picked(SKUCode='NULL-QTY', ColorWiseAlloction=None, TotalWeight=None, TotalVolume=None),
        picked(TruckCount=None, SKUCode='NULL-COUNTER'), picked(LogisticLocation=None, SKUCode='NULL-LOC'),
        picked(SKUCode='SIGNED', ColorWiseAlloction=-2, TotalWeight=Decimal('-1.250'), IsTruckFormed=False)]
    mixed[REMAINING] = [residual(), residual(), residual(DispatchColor='Red', ColorWiseAlloction=3),
        residual(WHCode='W2', SKUCode='SECOND', ColorWiseAlloction=0, TotalWeight=None),
        residual(SKUCode='NULL-QTY', ColorWiseAlloction=None, TotalWeight=None, TotalVolume=None),
        residual(ParentWHCode=None, SKUCode='NULL-PARENT'), residual(LogisticLocation=None, SKUCode='NULL-LOC'),
        residual(SKUCode='SIGNED', ColorWiseAlloction=-2, TotalWeight=Decimal('-1.250'))]
    empty = dict(common)
    empty.update({LOGISTIC: [], REMAINING: []})
    return [('mixed-native-null-duplicate-signed-and-count-false', mixed), ('explicit-empty-native-populations', empty)]


def preflight_fixtures(sql, cases):
    """Read-only whole-suite audit of declared generic tables, no site tables."""
    report = dict(status='PASS', scope='all declared generic fixtures before first mutation', populations=[], errors=[])
    for case, declared in cases:
        for (role, table), rows in declared.items():
            try:
                columns = [c for c in sql.schema(role, table) if not c['identity'] and not c['computed']
                           and c['type_name'] not in ('timestamp', 'rowversion')]
                checked = []
                for ordinal, row in enumerate(rows):
                    names = {name.casefold(): name for name in row}
                    if len(names) != len(row) or not set(names) <= {c['name'].casefold() for c in columns}:
                        raise ValueError('Unknown or repeated generic native fixture field')
                    cells = []
                    for column in columns:
                        value, reason = ((row[names[column['name'].casefold()]], 'explicit fixture declaration')
                            if column['name'].casefold() in names else sql.fill(column))
                        if value is None and not column['nullable']:
                            raise ValueError('NULL supplied for native NOT NULL field: ' + column['name'])
                        kind = column['type_name']
                        if value is not None:
                            if kind in ('nvarchar', 'nchar', 'varchar', 'char'):
                                if not isinstance(value, str):
                                    raise ValueError('Exact native text fixture required')
                                length = len(value.encode('utf-16-le' if kind in ('nvarchar', 'nchar') else 'cp1252'))
                                if column['max_length'] != -1 and length > column['max_length']:
                                    raise ValueError('Native text fixture exceeds schema')
                            elif kind in ('int', 'bigint', 'smallint', 'tinyint'):
                                lo, hi = {'int': (-2**31, 2**31-1), 'bigint': (-2**63, 2**63-1),
                                    'smallint': (-2**15, 2**15-1), 'tinyint': (0, 255)}[kind]
                                if type(value) is not int or not lo <= value <= hi:
                                    raise ValueError('Exact native integer fixture type/range required')
                            elif kind == 'bit' and type(value) is not bool:
                                raise ValueError('Exact native bit fixture required')
                            elif kind in ('decimal', 'numeric'):
                                if (not isinstance(value, Decimal) or not value.is_finite()
                                        or abs(value) >= Decimal(10)**(column['precision']-column['scale'])
                                        or value.as_tuple().exponent != -column['scale']):
                                    raise ValueError('Exact native decimal fixture type/precision/scale required')
                            typed(value, column)
                        cells.append(dict(field=column['name'], value=storage(value), reason=reason))
                    checked.append(dict(ordinal=ordinal, fields=cells))
                report['populations'].append(dict(case=case, role=role, table=table, rows=checked))
            except Exception as error:
                report['status'] = 'FAIL'
                report['errors'].append(dict(case=case, role=role, table=table, failure=str(error)))
    return report


def prepare(owner, isolation):
    if isolation._lease is not None:
        raise ValueError('Cannot bind during an active lease')
    mapping, directory = namespace(owner), data_directory(owner)
    setup = json.loads(SETUP.read_text())
    if (setup['owner_id'] != owner or setup['namespace'] != mapping
            or Path(setup['data_directory']).resolve() != directory.resolve()
            or setup.get('schema_only') is not True or setup.get('business_invocations') != 0):
        raise ValueError('Owned schema-only setup receipt differs')
    manifest_path = ROOT / 'baseline/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    registered = {row['path']: row['sha256'] for row in manifest['engine_sources']}
    for path, pin in projections.SOURCES.values():
        if registered.get((SOURCE / path).as_posix()) != pin:
            raise ValueError('Canonical Pick report source registration differs')
    isolation.MAPPING.clear()
    isolation.MAPPING.update(mapping)
    isolation.DATA = directory
    variables = dict(IntermediateDatabase=mapping['VFTEST_Intermediate'],
        ScriptExecutionFlagQuery='UPDATE ' + mapping['VFTEST_Importer']
            + '.dbo.ScriptExecutedFlag SET IsScriptExecuted=1 WHERE ScriptName=')
    scripts = preflight_scripts([dict(source_path=(SOURCE / path).as_posix(), source_sha256=pin,
        role='BPR', variables=variables) for path, pin in projections.SOURCES.values()],
        owner_id=owner, namespace=mapping)
    return dict(zip(projections.SOURCES, scripts)), dict(setup_path=str(SETUP),
        setup_sha256=hashlib.sha256(SETUP.read_bytes()).hexdigest(),
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest())


def restore_resultset(native):
    """Losslessly reconstitute shared executor's Decimal + type sidecar only."""
    rows, sidecar = native['rows'], native['python_types']
    if len(rows) != len(sidecar):
        raise ValueError('Native resultset type sidecar row count differs')
    restored = []
    for row, types in zip(rows, sidecar):
        if len(row) != len(types) or len(row) != len(native['fields']):
            raise ValueError('Native resultset ordinal cell roster differs')
        values = []
        for value, kind in zip(row, types):
            if kind == 'Decimal' and isinstance(value, str):
                value = Decimal(value)
            if type(value).__name__ != kind:
                raise ValueError('Native resultset value/type sidecar differs')
            values.append(value)
        restored.append(values)
    return restored


def compare_resultsets(native, expected, *, file_report=None):
    if file_report is not None and file_report not in projections.SOURCES:
        raise ValueError('Ordering qualification is restricted to four approved Pick batch files')
    report = dict(status='PASS', policy='strict observed resultset/column/cell sequence; bags diagnostic only',
                  resultsets=[], native_resultset_count=len(native), modern_resultset_count=len(expected),
                  unaccepted_file_order_gap=False, qualified_file_order_difference=False,
                  strict_sequence_status='PASS')
    if file_report is not None:
        report.update(policy='approved typed data-row bags; exact headers and column order; strict sequences retained',
                      ordering_qualification=ORDER_APPROVAL, file_report=file_report)
    if len(native) != len(expected):
        report['status'] = 'FAIL'
    for ordinal, (actual, wanted) in enumerate(zip(native, expected)):
        columns = [dict(name=str(i), type_name=kind.split('(')[0]) for i, kind in enumerate(wanted['types'])]
        native_rows = restore_resultset(actual)
        def sequence(rows):
            result = []
            for row in rows:
                if len(row) != len(columns):
                    raise ValueError('Projected resultset ordinal cell roster differs')
                result.append([typed(value, column) for value, column in zip(row, columns)])
            return result
        left, right = sequence(native_rows), sequence(wanted['rows'])
        encode = lambda row: json.dumps(row, separators=(',', ':'), ensure_ascii=False)
        bag_left, bag_right = Counter(map(encode, left)), Counter(map(encode, right))
        fields_match = list(actual['fields']) == list(wanted['fields'])
        sequence_match = left == right
        bag_match = bag_left == bag_right
        item = dict(ordinal=ordinal, native_fields=actual['fields'], modern_fields=list(wanted['fields']),
            expected_native_types=wanted['types'], fields_status='PASS' if fields_match else 'FAIL',
            strict_sequence_status='PASS' if sequence_match else 'FAIL',
            typed_bag_status='PASS' if bag_match else 'FAIL', native_sequence=left, modern_sequence=right,
            missing=[dict(cells=json.loads(k), occurrences=v) for k, v in (bag_left - bag_right).items()],
            extra=[dict(cells=json.loads(k), occurrences=v) for k, v in (bag_right - bag_left).items()])
        qualified = file_report is not None and ordinal == 1 and len(native) == len(expected) == 2
        item['status'] = 'PASS' if fields_match and (bag_match if qualified else sequence_match) else 'FAIL'
        item['acceptance'] = 'approved typed data-row bag' if qualified else 'strict sequence'
        report['resultsets'].append(item)
        if item['status'] != 'PASS':
            report['status'] = 'FAIL'
        if fields_match and bag_match and not sequence_match:
            report['qualified_file_order_difference' if qualified else 'unaccepted_file_order_gap'] = True
        if not fields_match or not sequence_match:
            report['strict_sequence_status'] = 'FAIL'
    return report


def table_compare(sql, key, wanted):
    return compare_rows(sql.rows(*key), wanted, sql.schema(*key))


def qualify(raw, isolation, scripts, name, declared):
    sql = FixtureSQL(raw, isolation)
    report = dict(name=name, status='STARTED', declared=storage([
        dict(role=k[0], table=k[1], rows=v) for k, v in declared.items()]),
        fixture_scope='explicit small native report-stage unit populations, not daily facts',
        filler_policy=sql.fills, endpoints=[], sql_receipts=[])
    try:
        for key, rows in declared.items():
            sql.load(*key, rows)
        inputs = {key: sql.rows(*key) for key in declared}
        report['inputs'] = storage([dict(role=k[0], table=k[1], schema=sql.schema(*k), rows=v) for k, v in inputs.items()])
        for key in (LOGISTIC, REMAINING, FLAG):
            for column in sql.schema(*key):
                if column['type_name'] in ('nvarchar', 'varchar') and column['collation'] != NATIVE_COLLATION:
                    raise ValueError('Report fixture text collation differs from qualified scalar domain')
        expected = projections.project_reports(logistic_pick_list=inputs[LOGISTIC],
                                                pick_list_data_for_truck_formation=inputs[REMAINING])
        flags = inputs[FLAG]
        for kind, projection in expected.items():
            scratch_before = sql.scratch()
            before = len(report['sql_receipts'])
            execute_native(raw, scripts[kind], isolation, report['sql_receipts'])
            observed = report['sql_receipts'][before:]
            if len(observed) != 1:
                raise ValueError('Expected exactly one canonical script attempt')
            endpoint = dict(kind=kind, projection=storage(projection), comparisons={})
            report['endpoints'].append(endpoint)
            endpoint['resultsets'] = compare_resultsets(observed[0]['resultsets'], projection['resultsets'], file_report=kind)
            if projection['script_marker'] is not None:
                flags = mark_script_executed(flags, projection['script_marker'], equal=scalars.ascii_equal)
            for key, rows in ((LOGISTIC, inputs[LOGISTIC]), (REMAINING, inputs[REMAINING]), (FLAG, flags)):
                endpoint['comparisons']['.'.join(key)] = table_compare(sql, key, rows)
            scratch_after = sql.scratch()
            if set(scratch_after) != set(scratch_before):
                raise ValueError('Native scratch table roster changed')
            for table, rows in scratch_before.items():
                endpoint['comparisons']['scratch:' + table] = compare_rows(scratch_after[table],
                    [] if projection['scratch_truncate_after'] else rows, sql.schema('Intermediate', table))
            if any(c['status'] != 'PASS' for c in endpoint['comparisons'].values()):
                raise ValueError('Native report side effect differs')
            if endpoint['resultsets']['status'] != 'PASS':
                if endpoint['resultsets']['unaccepted_file_order_gap']:
                    raise ValueError('UNACCEPTED_FILE_ORDER_GAP: typed bags agree but strict observed sequence differs')
                raise ValueError('Native report resultset contract differs')
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
        try:
            report['native_after_failure'] = storage([dict(role=k[0], table=k[1], rows=sql.rows(*k)) for k in declared])
            report['scratch_after_failure'] = storage(sql.scratch())
        except Exception as read_error:
            report['failure_readback_error'] = str(read_error)
    return report


def run(owner, output):
    output = guard_options(owner, output)
    from parity import legacy_isolation as isolation
    scripts, identities = prepare(owner, isolation)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    receipt = dict(schema='complete-daily-pick-files-qualification-v1', owner=owner,
        namespace=namespace(owner), data_directory=str(data_directory(owner)), status='STARTED',
        identities=identities, implementation_pins=implementation_pins(), scalar_adapters=scalar_binding(),
        sources={k: dict(path=s.source_path, sha256=s.source_sha256) for k, s in scripts.items()}, cases=[],
        scope='small rollback report-stage fixtures; zero full business-day invocations',
        missing_input_materializers=projections.MISSING_INPUT_MATERIALIZERS,
        ordering_qualification=ORDER_APPROVAL,
        limitations=['strict observed sequences retained separately; four-file typed-bag qualification only',
            'header order exact; calculation/table ordinal/API/paged-grid assertions unchanged',
            'native report-stage input materializers and production file delivery are outside this fixture proof',
            'only qualified ASCII/no ambiguous group representatives, native scale3 and nonoverflow domain'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as file:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                receipt['schema_receipts'] = [json.loads((data_directory(owner) / (db + '-schema.json')).read_text())
                    for db in namespace(owner).values()]
                with isolation.connection('VFTEST_BPR') as raw:
                    receipt['native_context'] = native_context(raw, isolation)
                    sql = FixtureSQL(raw, isolation)
                    cases = fixture_cases()
                    receipt['fixture_preflight'] = preflight_fixtures(sql, cases)
                    if receipt['fixture_preflight']['status'] != 'PASS':
                        raise ValueError('Entire report fixture suite failed schema preflight before mutation')
                    for name, declared in cases:
                        originals = {key: sql.rows(*key) for key in declared}
                        original_scratch = sql.scratch()
                        raw.raw.autocommit = False
                        try:
                            case = qualify(raw, isolation, scripts, name, declared)
                            receipt['cases'].append(case)
                        finally:
                            raw.rollback()
                            raw.raw.autocommit = True
                        case['outer_rollback'] = raw.execute('SELECT @@TRANCOUNT').fetchval() == 0
                        restored_scratch = sql.scratch()
                        if set(restored_scratch) != set(original_scratch):
                            raise ValueError('Rollback scratch roster changed')
                        case['seed_preservation'] = {'.'.join(k): table_compare(sql, k, rows) for k, rows in originals.items()}
                        case['scratch_preservation'] = {name: compare_rows(restored_scratch[name], rows,
                            sql.schema('Intermediate', name)) for name, rows in original_scratch.items()}
                        restored = all(c['status'] == 'PASS' for c in (
                            *case['seed_preservation'].values(), *case['scratch_preservation'].values()))
                        if case['status'] != 'PASS' or not case['outer_rollback'] or not restored:
                            raise ValueError('Stopped at first report qualification failure: ' + name)
            receipt['status'] = 'PASS'
        except Exception as error:
            receipt.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
        finally:
            receipt['implementation_identity_unchanged'] = implementation_pins() == receipt['implementation_pins']
            if not receipt['implementation_identity_unchanged']:
                receipt.update(status='FAIL', failure='Implementation identity changed during qualification')
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
