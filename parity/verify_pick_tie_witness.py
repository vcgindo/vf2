"""Native proof for both permissible orders of one approved two-row Pick tie.

The baseline runs the pinned source unchanged.  A derived test batch inserts one
rank swap after initial staging and before the native truck loop.  All canonical
calculation statements remain unchanged; the derived batch is never an oracle.
"""
import argparse
import base64
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application.complete_daily_pick_files import project_reports
from mta.application.complete_daily_pick import calculate_native_pick
from mta.domain.remaining_capabilities import calculate_pick_list_state
from mta.serialization import storage
from parity.verify_pick_stage_state import (
    LOGISTIC, PICK, REMAINING, FixtureSQL, compare_rows, execute_native,
    fixture, guard_options, implementation_pins, preflight_fixtures, prepare,
)

CANONICAL_PIN = 'b5044bcb979e57c270d944fdcf3a7998bee33484a384dae89aaaf414c7d05dfb'
SAFE_ANCHOR = '\tdeclare @maxNo as int'
SAFE_PREDECESSOR = 'from CteTruckFormation A'
STAGE_FIELDS = ('NewSRNo', 'SKUCode', 'WHCode', 'ParentWHCode', 'TotalWeight',
    'TotalVolume', 'VehicleWeightCapacity', 'VehicleVolumeCapacity',
    'RemainingWeight', 'RemainingVolume', 'DispatchColor', 'VehicleName',
    'Priority', 'ColorWiseAlloction', 'LogisticLocation', 'NoTruckFlag')
STABLE_IDENTITY = ('SKUCode', 'WHCode', 'ParentWHCode', 'LogisticLocation',
                   'VehicleName', 'Priority')
LEGACY_TIE_KEY = ('ParentWHCode', 'LogisticLocation', 'Priority')
BEFORE_MARKER, AFTER_MARKER = 'PICK_TIE_STAGE_BEFORE', 'PICK_TIE_STAGE_AFTER'


def _stage_select(marker):
    fields = ','.join('[' + field + ']' for field in STAGE_FIELDS)
    return (f"SELECT N'{marker}' AS WitnessMarker,{fields} "
        "FROM PickListDataForTruckFormation WHERE ParentWHCode=N'P' "
        "AND LogisticLocation=N'L1' AND Priority=2 ORDER BY SKUCode")


# Five top-level statements; only the UPDATE mutates data.
INSERTED_STATEMENTS = (
    _stage_select(BEFORE_MARKER),
    "IF (SELECT COUNT_BIG(1) FROM PickListDataForTruckFormation WHERE "
    "ParentWHCode=N'P' AND LogisticLocation=N'L1' AND Priority=2)<>2 OR "
    "(SELECT COUNT_BIG(1) FROM PickListDataForTruckFormation WHERE "
    "ParentWHCode=N'P' AND LogisticLocation=N'L1' AND Priority=2 AND "
    "((SKUCode=N'A' AND WHCode=N'W1' AND NewSRNo=1) OR "
    "(SKUCode=N'B' AND WHCode=N'W2' AND NewSRNo=2)))<>2 "
    "THROW 51000,N'Pick tie witness precondition differs',1",
    "UPDATE PickListDataForTruckFormation SET NewSRNo=CASE "
    "WHEN SKUCode=N'A' AND WHCode=N'W1' THEN 2 "
    "WHEN SKUCode=N'B' AND WHCode=N'W2' THEN 1 ELSE NewSRNo END "
    "WHERE ParentWHCode=N'P' AND LogisticLocation=N'L1' AND Priority=2 "
    "AND ((SKUCode=N'A' AND WHCode=N'W1') OR (SKUCode=N'B' AND WHCode=N'W2'))",
    "IF @@ROWCOUNT<>2 THROW 51001,N'Pick tie witness mutation count differs',1",
    _stage_select(AFTER_MARKER),
)
INSERTION_SQL = '\r\n' + ';\r\n'.join(INSERTED_STATEMENTS) + ';\r\n\t'


def _encoding(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        return 'utf-16'
    if raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    return 'cp1252'


def _insert_once(source, anchor, insertion):
    if source.count(anchor) != 1:
        raise ValueError('Canonical Pick safe split anchor must occur exactly once')
    offset = source.index(anchor)
    predecessor = SAFE_PREDECESSOR if isinstance(source, str) else SAFE_PREDECESSOR.encode('ascii')
    position = source.rfind(predecessor, 0, offset)
    if position < 0 or offset - position > 512:
        raise ValueError('Pick safe split is not immediately after initial staging')
    return source[:offset] + insertion + source[offset:], offset


def instrument_source_bytes(canonical):
    if hashlib.sha256(canonical).hexdigest() != CANONICAL_PIN:
        raise ValueError('Canonical Pick source identity differs')
    encoding = _encoding(canonical)
    inserted = INSERTION_SQL.encode(encoding)
    derived, offset = _insert_once(canonical, SAFE_ANCHOR.encode(encoding), inserted)
    receipt = dict(classification='test-only-post-rank-permutation-witness',
        unmodified_native_oracle=False, canonical_sha256=CANONICAL_PIN,
        derived_sha256=hashlib.sha256(derived).hexdigest(), encoding=encoding,
        insertion_offset=offset, insertion_length=len(inserted),
        inserted_bytes_base64=base64.b64encode(inserted).decode('ascii'),
        inserted_sha256=hashlib.sha256(inserted).hexdigest(),
        inserted_statement_count=len(INSERTED_STATEMENTS), mutation_statement_count=1,
        prefix_sha256=hashlib.sha256(canonical[:offset]).hexdigest(),
        suffix_sha256=hashlib.sha256(canonical[offset:]).hexdigest(),
        safe_split='after initial PickListDataForTruckFormation insert; before @maxNo/native loop')
    validate_source_instrumentation(canonical, derived, receipt)
    return derived, receipt


def recover_original_bytes(derived, receipt):
    offset, length = receipt['insertion_offset'], receipt['insertion_length']
    inserted = base64.b64decode(receipt['inserted_bytes_base64'])
    if len(inserted) != length or derived[offset:offset + length] != inserted:
        raise ValueError('Derived Pick witness insertion bytes differ')
    return derived[:offset] + derived[offset + length:]


def validate_source_instrumentation(canonical, derived, receipt):
    if receipt.get('classification') != 'test-only-post-rank-permutation-witness':
        raise ValueError('Derived Pick witness classification differs')
    if receipt.get('unmodified_native_oracle') is not False:
        raise ValueError('Derived Pick witness must never be labelled unmodified')
    if receipt.get('inserted_statement_count') != len(INSERTED_STATEMENTS):
        raise ValueError('Derived Pick inserted statement count differs')
    if receipt.get('mutation_statement_count') != 1:
        raise ValueError('Derived Pick must contain exactly one mutation statement')
    expected_insertion = INSERTION_SQL.encode(receipt.get('encoding', ''))
    recorded_insertion = base64.b64decode(receipt.get('inserted_bytes_base64', ''))
    if recorded_insertion != expected_insertion:
        raise ValueError('Derived Pick inserted SQL differs from the bounded witness')
    if hashlib.sha256(recorded_insertion).hexdigest() != receipt.get('inserted_sha256'):
        raise ValueError('Derived Pick inserted SQL hash differs')
    if hashlib.sha256(canonical).hexdigest() != receipt.get('canonical_sha256'):
        raise ValueError('Canonical Pick attribution hash differs')
    if hashlib.sha256(derived).hexdigest() != receipt.get('derived_sha256'):
        raise ValueError('Derived Pick attribution hash differs')
    if recover_original_bytes(derived, receipt) != canonical:
        raise ValueError('Canonical Pick bytes are not exactly recoverable')
    offset, length = receipt['insertion_offset'], receipt['insertion_length']
    if hashlib.sha256(derived[:offset]).hexdigest() != receipt.get('prefix_sha256'):
        raise ValueError('Derived Pick prefix differs')
    if hashlib.sha256(derived[offset + length:]).hexdigest() != receipt.get('suffix_sha256'):
        raise ValueError('Canonical Pick suffix changed after witness insertion')
    return True


def instrument_prepared_script(script):
    canonical = Path(script.source_path).read_bytes()
    _, receipt = instrument_source_bytes(canonical)
    sql, _ = _insert_once(script.sql, SAFE_ANCHOR, INSERTION_SQL)
    receipt['compiled_canonical_sha256'] = hashlib.sha256(script.sql.encode()).hexdigest()
    receipt['compiled_derived_sha256'] = hashlib.sha256(sql.encode()).hexdigest()
    return replace(script, sql=sql), receipt


def tied_fixture():
    """Exact unique-join/one-vehicle witness; no NULL or duplicate claim."""
    case, declared = fixture()
    case['vehicle']['weight_capacity'] = Decimal('4.000')
    case['items'] = case['items'][:2]
    declared[PICK] = declared[PICK][:2]
    declared[('BPR', 'SkuAttributeData')] = declared[('BPR', 'SkuAttributeData')][:2]
    declared[('BPR', 'LocationAttributeData')] = declared[('BPR', 'LocationAttributeData')][:2]
    declared[('BPR', 'VehicleMaster')][0]['Weight'] = Decimal('4.000')
    for item, pick, attribute in zip(case['items'], declared[PICK],
            declared[('BPR', 'SkuAttributeData')], strict=True):
        item.update(weight=Decimal('1.000'), logistics_location='L1', dispatch_color='Red',
            buckets=dict(to_black=0, to_red=3, to_yellow=0, to_green=0, to_blue=0))
        pick.update(RationedReq=3, TOR_B=0, TOR_R=3, TOY=0, TOG=0, TOBlue=0,
                    DispatchColor='Red')
        attribute['Weight'] = Decimal('1.000')
    for location in declared[('BPR', 'LocationAttributeData')]:
        location['LogisticsLocation'] = 'L1'
    validate_tied_fixture(case, declared)
    return case, declared


def validate_tied_fixture(case, declared):
    items = case.get('items')
    if not isinstance(items, list) or len(items) != 2 or len(declared.get(PICK, ())) != 2:
        raise ValueError('Tie witness requires exactly two modern/native Pick rows')
    if len(declared.get(('BPR', 'VehicleMaster'), ())) != 1 or len(declared.get(
            ('BPR', 'LocationVehicleMaster'), ())) != 1:
        raise ValueError('Tie witness requires exactly one applicable vehicle')
    if {(r['sku'], r['to_location']) for r in items} != {('A', 'W1'), ('B', 'W2')}:
        raise ValueError('Tie witness identities differ')
    if {(r['from_location'], r['logistics_location']) for r in items} != {('P', 'L1')}:
        raise ValueError('Tie witness legacy partition differs')
    bands = {'to_black': 0, 'to_red': 3, 'to_yellow': 0, 'to_green': 0, 'to_blue': 0}
    if any(r['buckets'] != bands for r in items):
        raise ValueError('Tie witness quantities or priority differ')
    for key, field in ((('BPR', 'SkuAttributeData'), 'SKUCode'),
                       (('BPR', 'LocationAttributeData'), 'WHCode')):
        rows = declared.get(key, ())
        if len(rows) != 2 or len({r[field] for r in rows}) != 2:
            raise ValueError('Tie witness requires unique native attribute joins')
    return True


def _by_identity(rows):
    result = {}
    for row in rows:
        identity = tuple(row[field] for field in STABLE_IDENTITY)
        if identity in result:
            raise ValueError('Tie witness staged identity multiplicity differs')
        result[identity] = row
    return result


def validate_rank_permutation(before, after):
    if len(before) != 2 or len(after) != 2:
        raise ValueError('Tie witness staged multiplicity differs')
    if any(set(row) != set(STAGE_FIELDS) for row in before + after):
        raise ValueError('Tie witness staged column roster differs')
    left, right = _by_identity(before), _by_identity(after)
    if set(left) != set(right):
        raise ValueError('Tie witness staged row eligibility differs')
    keys = {tuple(row[field] for field in LEGACY_TIE_KEY) for row in before + after}
    if keys != {('P', 'L1', 2)}:
        raise ValueError('Tie witness moved an untied rank or another partition')
    before_ranks, after_ranks = {}, {}
    for identity in left:
        for field in STAGE_FIELDS:
            if field != 'NewSRNo' and left[identity][field] != right[identity][field]:
                raise ValueError('Tie witness changed non-rank field: ' + field)
        item = (left[identity]['SKUCode'], left[identity]['WHCode'])
        before_ranks[item] = left[identity]['NewSRNo']
        after_ranks[item] = right[identity]['NewSRNo']
    if before_ranks != {('A', 'W1'): 1, ('B', 'W2'): 2}:
        raise ValueError('Tie witness baseline ranks differ')
    if after_ranks != {('A', 'W1'): 2, ('B', 'W2'): 1}:
        raise ValueError('Tie witness did not apply the sole opposite permutation')
    return dict(status='PASS', legacy_tie_key=['P', 'L1', 2],
                changed_fields=['NewSRNo'], row_count=2)


def extract_staged_images(receipt):
    images = {}
    expected = ['WitnessMarker', *STAGE_FIELDS]
    for resultset in receipt.get('resultsets', []):
        if resultset.get('fields') != expected or not resultset.get('rows'):
            continue
        marker = resultset['rows'][0][0]
        if marker not in (BEFORE_MARKER, AFTER_MARKER) or marker in images:
            continue
        if any(row[0] != marker for row in resultset['rows']):
            raise ValueError('Tie witness staged marker resultset is mixed')
        images[marker] = [dict(zip(STAGE_FIELDS, row[1:], strict=True))
                          for row in resultset['rows']]
    if set(images) != {BEFORE_MARKER, AFTER_MARKER}:
        raise ValueError('Tie witness staged before/after resultsets are missing')
    return images


def compare_complete_state(native, modern, sql):
    comparisons = {}
    for key in (LOGISTIC, REMAINING):
        comparison = compare_rows(native[key[1]], modern[key[1]], sql.schema(*key))
        comparison['strict_sequence_status'] = ('PASS' if
            comparison['native_sequence'] == comparison['modern_sequence'] else 'FAIL')
        comparisons[key[1]] = comparison
        if comparison['status'] != 'PASS' or comparison['strict_sequence_status'] != 'PASS':
            raise ValueError('Tie witness complete strict state differs: ' + key[1])
    return comparisons


def compare_downstream(native, modern):
    native_reports = storage(project_reports(logistic_pick_list=native['LogisticPickList'],
        pick_list_data_for_truck_formation=native['PickListDataForTruckFormation']))
    modern_reports = storage(project_reports(logistic_pick_list=modern['LogisticPickList'],
        pick_list_data_for_truck_formation=modern['PickListDataForTruckFormation']))
    if native_reports != modern_reports:
        raise ValueError('Tie witness downstream Pick projections differ')
    return dict(status='PASS', native=native_reports, modern=modern_reports)


def _execute_case(raw, sql, isolation, script, declared, modern, classification, instrumentation=None):
    receipts = []
    for key, rows in declared.items():
        sql.load(*key, rows)
    execute_native(raw, script, isolation, receipts)
    receipt = receipts[-1]
    receipt.update(classification=classification,
        unmodified_native_oracle=classification == 'unmodified-native-baseline')
    if instrumentation is not None:
        receipt['instrumentation'] = instrumentation
    native = {key[1]: sql.rows(*key) for key in (LOGISTIC, REMAINING)}
    result = dict(classification=classification,
        unmodified_native_oracle=receipt['unmodified_native_oracle'], sql_receipts=receipts,
        native_state=storage(native), state_comparisons=compare_complete_state(native, modern, sql),
        downstream=compare_downstream(native, modern))
    if instrumentation is not None:
        images = extract_staged_images(receipt)
        result.update(staged_before=images[BEFORE_MARKER], staged_after=images[AFTER_MARKER])
        result['rank_permutation'] = validate_rank_permutation(result['staged_before'], result['staged_after'])
    return result


def run(owner, output):
    output = guard_options(owner, output)
    from parity import legacy_isolation as isolation
    canonical, identities = prepare(owner, isolation)
    if canonical.source_sha256 != CANONICAL_PIN:
        raise ValueError('Prepared canonical Pick source differs')
    derived, attribution = instrument_prepared_script(canonical)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    case, declared = tied_fixture()
    sources = dict(pick_rows=declared[PICK], sku_attributes=declared['BPR', 'SkuAttributeData'],
        location_attributes=declared['BPR', 'LocationAttributeData'], vehicles=declared['BPR', 'VehicleMaster'],
        location_vehicles=declared['BPR', 'LocationVehicleMaster'])
    forward = calculate_native_pick(**sources)
    reverse = calculate_native_pick(**{**sources, 'pick_rows': list(reversed(sources['pick_rows']))})
    report = dict(schema='pick-tie-post-rank-witness-v1', status='STARTED', identities=identities,
        scope='one unique two-row tie; unmodified baseline and test-only opposite rank permutation',
        exclusions=['NULL dimensions', 'duplicate joins', 'multiple vehicles', 'production tie-break',
                    'business formula changes', 'business-day execution'],
        canonical_source_sha256=CANONICAL_PIN, instrumentation=attribution,
        business_day_calls=0, implementation_pins=implementation_pins(), cases=[])
    report['witness_implementation_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['input_adapter_sha256'] = hashlib.sha256((ROOT/'mta/application/complete_daily_pick.py').read_bytes()).hexdigest()
    report['native_input_rows'] = storage(sources)
    try:
        with isolation.exclusive_replay(validate_schema=True), isolation.connection('VFTEST_BPR') as raw:
            sql = FixtureSQL(raw, isolation)
            report['fixture_preflight'] = preflight_fixtures(sql, [('two-row-tie', declared)])
            if report['fixture_preflight']['status'] != 'PASS':
                raise ValueError('Tie witness fixture schema preflight failed')
            originals, scratch = {k: sql.rows(*k) for k in declared}, sql.scratch()
            for script, modern, label, instrument in (
                    (canonical, forward, 'unmodified-native-baseline', None),
                    (derived, reverse, 'test-only-post-rank-permutation-witness', attribution)):
                raw.raw.autocommit = False
                try:
                    result = _execute_case(raw, sql, isolation, script, declared, modern, label, instrument)
                    report['cases'].append(result)
                finally:
                    raw.rollback(); raw.raw.autocommit = True
                result['outer_rollback'] = raw.execute('SELECT @@TRANCOUNT').fetchval() == 0
                result['seed_preservation'] = {'.'.join(k): compare_rows(sql.rows(*k), rows, sql.schema(*k))
                                               for k, rows in originals.items()}
                restored = sql.scratch()
                result['scratch_preservation'] = {name: compare_rows(restored[name], rows,
                    sql.schema('Intermediate', name)) for name, rows in scratch.items()}
                if (not result['outer_rollback'] or set(restored) != set(scratch) or
                        any(v['status'] != 'PASS' for v in result['seed_preservation'].values()) or
                        any(v['status'] != 'PASS' for v in result['scratch_preservation'].values())):
                    raise ValueError('Tie witness owned rollback restoration failed')
        if [c['classification'] for c in report['cases']] != [
                'unmodified-native-baseline', 'test-only-post-rank-permutation-witness']:
            raise ValueError('Tie witness baseline/derived classification differs')
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(storage(report), stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True); parser.add_argument('--output', required=True, type=Path)
    options = parser.parse_args(); result = run(options.owner, options.output)
    print(json.dumps({k: result[k] for k in ('status', 'failure') if k in result}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
