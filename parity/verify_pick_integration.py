"""Finite rollback-native qualification of the complete Pick input adapter.

Modern calculation consumes the five source table images read back from the
owned fixture database.  The pinned SQL is unchanged.  Full 21/16 table images
require complete typed bags under approved D1, retaining raw sequences; the four
downstream reports use approved D2 data-row bags with exact headers/types.  The known underfilled single-NULL
queue is excluded because canonical SQL does not terminate for that input.
"""
import argparse
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application.complete_daily_pick import calculate_native_pick
from mta.application.complete_daily_pick_files import project_reports
from mta.serialization import storage
from parity.verify_complete_daily_pick_files import compare_resultsets
from parity.verify_pick_stage_state import (
    FLAG, LOGISTIC, PICK, REMAINING, SCRATCH, FixtureSQL, compare_rows,
    execute_native, fixture, guard_options, preflight_fixtures, prepare,
)

SKU = ('BPR', 'SkuAttributeData')
LOCATION = ('BPR', 'LocationAttributeData')
VEHICLE = ('BPR', 'VehicleMaster')
LOCATION_VEHICLE = ('BPR', 'LocationVehicleMaster')
SOURCE_KEYS = (PICK, SKU, LOCATION, VEHICLE, LOCATION_VEHICLE)
CASE_NAMES = (
    'original-weight', 'original-volume', 'concurrent-active-queues',
    'duplicate-pick-sticky-flag', 'duplicate-pick-and-location',
    'identical-duplicate-sku-attribute', 'distinct-logistics-locations',
    'both-null-excluded', 'both-zero-residual', 'single-null-exact-fit',
    'single-null-overshoot-capacity-flaw', 'zero-boundary-after-prefix',
    'mixed-null-sku-duplicate', 'equal-capacity-multiple-vehicles',
    'different-capacity-multiple-vehicles', 'differing-sku-dimensions',
)
AMBIGUOUS_CASES = {
    'mixed-null-sku-duplicate': 'differing dimension candidates',
    'different-capacity-multiple-vehicles': 'differing candidate values',
    'differing-sku-dimensions': 'differing dimension candidates',
}
IMPLEMENTATION_FILES = (
    'mta/application/complete_daily_pick.py',
    'mta/application/complete_daily_pick_files.py',
    'mta/domain/remaining_capabilities.py',
    'mta/domain/complete_daily_scalars.py',
    'mta/serialization.py',
    'parity/verify_pick_integration.py',
    'parity/verify_pick_stage_state.py',
    'parity/verify_complete_daily_producers.py',
    'parity/verify_complete_daily_completion.py',
    'parity/adapters/legacy/complete_daily_sql.py',
    'parity/legacy_isolation.py',
)


class StopFirstFailure(RuntimeError):
    pass


def implementation_pins():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in IMPLEMENTATION_FILES}


def _set_quantity(row, quantity, band='TOR_B'):
    for field in ('TOR_B', 'TOR_R', 'TOY', 'TOG', 'TOBlue'):
        row[field] = 0
    row[band] = quantity
    row['RationedReq'] = quantity


def _only(declared, skus):
    declared[PICK] = [row for row in declared[PICK] if row['SKUCode'] in skus]
    declared[SKU] = [row for row in declared[SKU] if row['SKUCode'] in skus]
    wh_codes = {row['WhCode'] for row in declared[PICK]}
    declared[LOCATION] = [row for row in declared[LOCATION] if row['WHCode'] in wh_codes]
    return declared


def _a_only(*, quantity=3, weight='1.000', volume='1.000', weight_cap='4.000', volume_cap='100.000'):
    _, declared = fixture('weight')
    _only(declared, {'A'})
    _set_quantity(declared[PICK][0], quantity)
    declared[SKU][0].update(Weight=None if weight is None else Decimal(weight),
                            Volume=None if volume is None else Decimal(volume))
    declared[VEHICLE][0].update(Weight=Decimal(weight_cap), Volume=Decimal(volume_cap))
    return declared


def fixture_cases():
    cases = []
    for variant in ('weight', 'volume'):
        _, declared = fixture(variant)
        cases.append(('original-' + variant, declared))

    _, concurrent = fixture('weight')
    _set_quantity(next(row for row in concurrent[PICK] if row['SKUCode'] == 'D'), 12)
    cases.append(('concurrent-active-queues', concurrent))

    duplicate_pick = _a_only(quantity=7, weight='1.000', weight_cap='4.000')
    duplicate_pick[PICK].append(deepcopy(duplicate_pick[PICK][0]))
    cases.append(('duplicate-pick-sticky-flag', duplicate_pick))

    duplicate_location = deepcopy(duplicate_pick)
    duplicate_location[LOCATION].append(deepcopy(duplicate_location[LOCATION][0]))
    cases.append(('duplicate-pick-and-location', duplicate_location))

    duplicate_sku = _a_only(quantity=3, weight='1.000', weight_cap='4.000')
    duplicate_sku[SKU].append(deepcopy(duplicate_sku[SKU][0]))
    cases.append(('identical-duplicate-sku-attribute', duplicate_sku))

    distinct_locations = _a_only(quantity=3, weight='1.000', weight_cap='4.000')
    distinct_locations[LOCATION].append(dict(distinct_locations[LOCATION][0], LogisticsLocation='L2'))
    cases.append(('distinct-logistics-locations', distinct_locations))

    cases.append(('both-null-excluded', _a_only(quantity=3, weight=None, volume=None)))
    cases.append(('both-zero-residual', _a_only(quantity=3, weight='0.000', volume='0.000')))
    cases.append(('single-null-exact-fit', _a_only(quantity=5, weight=None, volume='1.000',
                                                   weight_cap='100.000', volume_cap='5.000')))
    cases.append(('single-null-overshoot-capacity-flaw', _a_only(quantity=6, weight=None, volume='1.000',
                                                                 weight_cap='100.000', volume_cap='5.000')))

    _, zero_boundary = fixture('weight')
    _only(zero_boundary, {'A', 'B'})
    _set_quantity(next(row for row in zero_boundary[PICK] if row['SKUCode'] == 'A'), 4, 'TOR_B')
    _set_quantity(next(row for row in zero_boundary[PICK] if row['SKUCode'] == 'B'), 1, 'TOR_R')
    cases.append(('zero-boundary-after-prefix', zero_boundary))
    mixed = _a_only(quantity=2, weight_cap='2.000')
    extra = dict(mixed[PICK][0], WhCode='W2')
    _set_quantity(extra, 1)
    mixed[PICK].append(extra)
    mixed[LOCATION].append(dict(mixed[LOCATION][0], WHCode='W2', LogisticsLocation='L2'))
    mixed[SKU].append(dict(mixed[SKU][0], Weight=None, Volume=None))
    cases.append(('mixed-null-sku-duplicate', mixed))
    equal = _a_only(quantity=2, weight_cap='4.000')
    equal[VEHICLE][0]['VehicleName']='V_EQ_1'
    equal[VEHICLE].append(dict(equal[VEHICLE][0], VehicleID=2, VehicleName='V_EQ_2'))
    equal[LOCATION_VEHICLE].append(dict(equal[LOCATION_VEHICLE][0], VehicleID=2))
    cases.append(('equal-capacity-multiple-vehicles', equal))
    different = deepcopy(equal)
    different[VEHICLE][0].update(Weight=Decimal('3.000'), VehicleName='V_DIFF_1')
    different[VEHICLE][1]['VehicleName']='V_DIFF_2'
    cases.append(('different-capacity-multiple-vehicles', different))
    dimensions = _a_only(quantity=2, weight_cap='6.000')
    dimensions[SKU].append(dict(dimensions[SKU][0], Weight=Decimal('2.000')))
    cases.append(('differing-sku-dimensions', dimensions))
    validate_fixture_cases(cases)
    return cases


def validate_fixture_cases(cases):
    if not isinstance(cases, list) or tuple(name for name, _ in cases) != CASE_NAMES:
        raise ValueError('Exact finite Pick integration case roster required')
    for name, declared in cases:
        if name == 'single-null-underfilled' or 'underfilled' in name:
            raise ValueError('Canonical nonterminating single-NULL case must not execute')
        if not isinstance(declared, dict) or any(key not in declared for key in
                (*SOURCE_KEYS, LOGISTIC, REMAINING, FLAG, SCRATCH)):
            raise ValueError('Complete declared Pick fixture populations required: ' + name)
        if declared[LOGISTIC] or declared[REMAINING]:
            raise ValueError('Pick output tables must begin empty: ' + name)
    return True


def source_arguments(images):
    if set(images) != set(SOURCE_KEYS):
        raise ValueError('Exactly five loaded native Pick source images required')
    return dict(pick_rows=images[PICK], sku_attributes=images[SKU],
        location_attributes=images[LOCATION], vehicles=images[VEHICLE],
        location_vehicles=images[LOCATION_VEHICLE])


def compare_full_state(native, modern, sql):
    result = {}
    overall = 'PASS'
    for key, count in ((LOGISTIC, 21), (REMAINING, 16)):
        columns = sql.schema(*key)
        if len(columns) != count:
            raise ValueError('Required full native Pick column count differs: ' + key[1])
        comparison = compare_rows(native[key[1]], modern[key[1]], columns)
        comparison['typed_bag_status'] = comparison['status']
        comparison['strict_sequence_status'] = ('PASS' if
            comparison['native_sequence'] == comparison['modern_sequence'] else 'FAIL')
        comparison['status'] = comparison['typed_bag_status']
        if comparison['status'] != 'PASS':
            overall = 'FAIL'
        result[key[1]] = comparison
    return dict(status=overall, tables=result,
                policy='approved D1 complete typed multiset; raw sequences diagnostic; modern storage ordinals exact')


def compare_downstream(native, modern):
    left = project_reports(logistic_pick_list=native['LogisticPickList'],
        pick_list_data_for_truck_formation=native['PickListDataForTruckFormation'])
    right = project_reports(logistic_pick_list=modern['LogisticPickList'],
        pick_list_data_for_truck_formation=modern['PickListDataForTruckFormation'])
    comparisons = {}
    for name in left:
        observed = [dict(fields=list(r['fields']), rows=storage(r['rows']),
                         python_types=[[type(v).__name__ for v in row] for row in r['rows']])
                    for r in left[name]['resultsets']]
        comparisons[name] = compare_resultsets(observed, right[name]['resultsets'], file_report=name)
    return dict(status='PASS' if all(r['status']=='PASS' for r in comparisons.values()) else 'FAIL',
                native=storage(left), modern=storage(right), comparisons=comparisons,
                policy='approved D2 four-export typed data-row bags; exact headers/types; raw sequences retained')


def qualify(raw, isolation, script, declared, name, result=None):
    sql = FixtureSQL(raw, isolation)
    result = result if result is not None else {}
    result.update(name=name, status='STARTED', sql_receipts=[], native_inputs=[],
                  modern_state=None, native_full_rows=None, full_images={}, downstream={})
    for key, rows in declared.items():
        sql.load(*key, rows)
    loaded = {key: sql.rows(*key) for key in SOURCE_KEYS}
    result['native_inputs'] = storage([dict(role=key[0], table=key[1],
        schema=sql.schema(*key), rows=loaded[key]) for key in SOURCE_KEYS])
    if name in AMBIGUOUS_CASES:
        try:
            calculate_native_pick(**source_arguments(loaded))
        except ValueError as error:
            if AMBIGUOUS_CASES[name] not in str(error):
                raise
            result['modern_denial'] = str(error)
        else:
            raise ValueError('Ambiguous native UPDATE must not invent a winner: '+name)
        execute_native(raw, script, isolation, result['sql_receipts'])
        result['native_full_rows'] = storage({key[1]: sql.rows(*key) for key in (LOGISTIC, REMAINING)})
        result.update(status='DENIED_APPROVED', approval='human controller turn01a11a92-4215-7273-a398-45ace82cff36',
            acceptance='native observation only; conflicting UPDATE candidates have no unique canonical winner')
        return result
    modern = calculate_native_pick(**source_arguments(loaded))
    result['modern_state'] = storage(modern)
    execute_native(raw, script, isolation, result['sql_receipts'])
    native = {key[1]: sql.rows(*key) for key in (LOGISTIC, REMAINING)}
    result['native_full_rows'] = storage(native)
    result['full_images'] = compare_full_state(native, modern, sql)
    result['downstream'] = compare_downstream(native, modern)
    if result['full_images']['status'] != 'PASS':
        raise ValueError('Pick integration full state/strict sequence differs: ' + name)
    if result['downstream']['status'] != 'PASS':
        raise ValueError('Pick integration downstream projections differ: ' + name)
    result['status'] = 'PASS'
    return result


def run(owner, output, selected=None):
    output = guard_options(owner, output)
    from parity import legacy_isolation as isolation
    script, identities = prepare(owner, isolation)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    cases = fixture_cases()
    if selected:
        if len(set(selected)) != len(selected) or set(selected)-set(CASE_NAMES):
            raise ValueError('Selected cases must belong to fixed Pick roster')
        cases = [(n,d) for n,d in cases if n in selected]
    report = dict(schema='pick-native-input-integration-v1', status='STARTED', owner=owner,
        identities=identities, canonical_source=script.source_path,
        canonical_source_sha256=script.source_sha256, canonical_sql_unchanged=True,
        scope=[name for name, _ in cases], fixed_roster=list(CASE_NAMES), exclusions=['single-null-underfilled: canonical nontermination; never executed'],
        business_day_calls=0, implementation_pins=implementation_pins(), cases=[])
    try:
        with isolation.exclusive_replay(validate_schema=True), isolation.connection('VFTEST_BPR') as raw:
            sql = FixtureSQL(raw, isolation)
            report['fixture_preflight'] = preflight_fixtures(sql, cases)
            if report['fixture_preflight']['status'] != 'PASS':
                raise StopFirstFailure('Pick integration fixture preflight failed')
            for name, declared in cases:
                originals = {key: sql.rows(*key) for key in declared}
                original_scratch = sql.scratch()
                raw.raw.autocommit = False
                case = dict(name=name, status='STARTED')
                report['cases'].append(case)
                failure = None
                try:
                    qualify(raw, isolation, script, declared, name, case)
                except Exception as error:
                    case.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
                    failure = error
                finally:
                    raw.rollback()
                    raw.raw.autocommit = True
                case['outer_rollback'] = raw.execute('SELECT @@TRANCOUNT').fetchval() == 0
                case['seed_preservation'] = {'.'.join(key): compare_rows(
                    sql.rows(*key), rows, sql.schema(*key)) for key, rows in originals.items()}
                restored_scratch = sql.scratch()
                case['scratch_preservation'] = {table: compare_rows(restored_scratch[table], rows,
                    sql.schema('Intermediate', table)) for table, rows in original_scratch.items()}
                restored = (case['outer_rollback'] and set(restored_scratch) == set(original_scratch) and
                    all(item['status'] == 'PASS' for item in case['seed_preservation'].values()) and
                    all(item['status'] == 'PASS' for item in case['scratch_preservation'].values()))
                if not restored:
                    failure = ValueError('Pick integration owned rollback restoration failed: ' + name)
                    case.update(status='FAIL', failure_type=type(failure).__name__, failure=str(failure))
                if failure is not None:
                    raise StopFirstFailure(str(failure)) from failure
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(storage(report), stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cases', nargs='+', choices=CASE_NAMES)
    options = parser.parse_args()
    result = run(options.owner, options.output, options.cases)
    print(json.dumps(dict(status=result['status'], cases=len(result['cases']),
                          output=str(options.output), failure=result.get('failure'))))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
