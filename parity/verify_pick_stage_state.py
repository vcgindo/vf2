"""Restricted rollback-native full truck-state proof; not a generic-day proof.

One unambiguous fixture family with weight/volume variants. Full typed21/16 images check observed sequence
separately from relational-bag component checks; both must pass. Allocation output and
the original ordered narrow checkpoint projections remain exact assertions.
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

from mta.domain import remaining_capabilities as producer
from mta.domain import complete_daily_scalars as scalars
from mta.domain.complete_daily_completion import mark_script_executed
from mta.runtime.relational_state import CATALOG
from mta.serialization import storage
from parity.adapters.legacy.complete_daily_sql import namespace, data_directory, preflight_scripts
from parity.verify_complete_daily_completion import SETUP, execute_native
from parity.verify_complete_daily_producers import (OWNER, OUTPUT_ROOT, SOURCE, FixtureSQL,
    compare_rows, guard_options, scalar_binding, native_context, NATIVE_COLLATION)
from parity.verify_complete_daily_pick_files import preflight_fixtures

PATH = 'Scripts/BPR/Ration_Scripts/GenerateLogisticPickList.sql'
PIN = 'b5044bcb979e57c270d944fdcf3a7998bee33484a384dae89aaaf414c7d05dfb'
LOGISTIC = ('BPR', 'LogisticPickList')
REMAINING = ('BPR', 'PickListDataForTruckFormation')
FLAG = ('Importer', 'ScriptExecutedFlag')
SCRATCH = ('Intermediate', 'RemainingLogisticQtyDetails')
PICK = ('BPR', 'vf_PickListReport')
NARROW = {
    'logistic_pick': ('SELECT SKUCode,WHCode,ParentWHCode,Priority,ColorWiseAlloction,VehicleName,TruckCount,LogisticLocation,TotalWeight,TotalVolume FROM LogisticPickList ORDER BY NewSRNo',
        ('sku_code', 'location_code', 'parent_location_code', 'priority', 'picked_quantity', 'vehicle', 'truck', 'logistics_location', 'total_weight', 'total_volume')),
    'pick_remaining': ('SELECT SKUCode,WhCode,ParentWhCode,LogisticLocation,Priority,ColorWiseAlloction,VehicleName FROM PickListDataForTruckFormation ORDER BY NewSrNo',
        ('sku', 'to_location', 'from_location', 'logistics_location', 'priority', 'remaining_quantity', 'vehicle')),
}
IMPLEMENTATION_FILES = ('mta/domain/remaining_capabilities.py', 'mta/domain/complete_daily_scalars.py',
    'mta/domain/complete_daily_completion.py', 'mta/serialization.py', 'mta/runtime/relational_state.py',
    'baseline/production-state-schema.json', 'parity/verify_pick_stage_state.py',
    'parity/verify_complete_daily_pick_files.py', 'parity/verify_complete_daily_completion.py',
    'parity/verify_complete_daily_producers.py', 'parity/adapters/legacy/complete_daily_sql.py',
    'parity/adapters/legacy/r1_runner.py', 'parity/legacy_isolation.py')


def implementation_pins():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in IMPLEMENTATION_FILES}


def fixture(variant='weight'):
    if variant not in ('weight', 'volume'):
        raise ValueError('Only the two approved restricted fixture variants are permitted')
    vehicle = dict(name='fixture-vehicle', weight_capacity=Decimal('5.000' if variant == 'weight' else '100.000'),
                   volume_capacity=Decimal('100.000' if variant == 'weight' else '2.500'))
    ab_weight = '2.000' if variant == 'weight' else '4.500'
    items = []
    for sku, wh, logistic, colour, bucket, qty, weight in (
            ('A', 'W1', 'L1', 'Black', 'to_black', 1, ab_weight),
            ('B', 'W2', 'L1', 'Red', 'to_red', 4, ab_weight),
            ('D', 'W3', 'L2', 'Black', 'to_black', 2, '1.000')):
        items.append(dict(case=sku, sku=sku, from_location='P', to_location=wh,
            logistics_location=logistic, dispatch_color=colour, pack_size=1,
            weight=Decimal(weight), volume=Decimal('1.000'),
            buckets={key: qty if key == bucket else 0 for key in
                     ('to_black', 'to_red', 'to_yellow', 'to_green', 'to_blue')}))
    case = dict(vehicle=vehicle, items=items)
    declared = {LOGISTIC: [], REMAINING: [],
        FLAG: [dict(ScriptName='GenerateLogisticPickList.sql', ModuleName='BPR',
                    IsScriptExecuted=False, IsScriptCritical=True)],
        SCRATCH: [dict(ParentWHCode='SCRATCH', WHCode='W', SKUCode='UNIT', Qty=1)],
        ('BPR', 'VehicleMaster'): [dict(VehicleID=1, VehicleName=vehicle['name'],
            Weight=vehicle['weight_capacity'], Volume=vehicle['volume_capacity'])],
        ('BPR', 'LocationVehicleMaster'): [dict(LocationID='P', VehicleID=1)],
        ('BPR', 'SkuAttributeData'): [], ('BPR', 'LocationAttributeData'): [], PICK: []}
    for item in items:
        report = {field: Decimal('0.00') if kind == 'decimal' else False if kind == 'bit'
                  else 0 if kind == 'int' else None for field, kind in CATALOG['tables']['BPR/vf_RationedReqReport']}
        report.update(SKUCode=item['sku'], WhCode=item['to_location'], ParentWhCode=item['from_location'],
            Norm=9, VirtualNorm=9, PackSize=1, ParentPackSize=1, RationedReq=sum(item['buckets'].values()),
            DispatchColor=item['dispatch_color'], PostPipelineInventoryPen=None, PostPipelineInventoryColor=None)
        report.update({native: item['buckets'][modern] for native, modern in zip(
            ('TOR_B', 'TOR_R', 'TOY', 'TOG', 'TOBlue'), ('to_black', 'to_red', 'to_yellow', 'to_green', 'to_blue'))})
        declared[PICK].append(report)
        declared[('BPR', 'SkuAttributeData')].append(dict(SKUCode=item['sku'], Weight=item['weight'], Volume=item['volume']))
        declared[('BPR', 'LocationAttributeData')].append(dict(WHCode=item['to_location'], LogisticsLocation=item['logistics_location']))
    return case, declared


def fixture_cases():
    return [(variant + '-boundary-two-logistics-queues', *fixture(variant)) for variant in ('weight', 'volume')]


def validate_fixture(case, declared):
    """Refuse accidental expansion into unresolved join/rank branches."""
    vehicle = case['vehicle']
    if set(vehicle) != {'name', 'weight_capacity', 'volume_capacity'}:
        raise ValueError('Exactly one explicit vehicle required')
    seen_sku, seen_location, ranks = set(), set(), set()
    for item in case['items']:
        if item['sku'] in seen_sku or item['to_location'] in seen_location:
            raise ValueError('Unique fixture SKU/location joins required')
        seen_sku.add(item['sku'])
        seen_location.add(item['to_location'])
        if any(not isinstance(item[field], Decimal) or item[field] <= 0 for field in ('weight', 'volume')):
            raise ValueError('Positive non-NULL fixture dimensions required')
        for priority, bucket in enumerate(('to_black', 'to_red', 'to_yellow', 'to_green', 'to_blue'), 1):
            if item['buckets'][bucket] > 0:
                rank = (item['from_location'], item['logistics_location'], priority)
                if rank in ranks:
                    raise ValueError('Unambiguous positive native priority ranks required')
                ranks.add(rank)
    if len(declared[('BPR', 'LocationVehicleMaster')]) != 1 or len(declared[('BPR', 'VehicleMaster')]) != 1:
        raise ValueError('Exactly one applicable native vehicle required')
    for key, field in ((('BPR', 'SkuAttributeData'), 'SKUCode'), (('BPR', 'LocationAttributeData'), 'WHCode')):
        if len({r[field] for r in declared[key]}) != len(declared[key]):
            raise ValueError('Unique native attribute joins required')
    if len(declared[PICK]) != len(case['items']):
        raise ValueError('Exact fixture Pick source occurrence roster required')
    native_vehicle = declared[('BPR', 'VehicleMaster')][0]
    if (native_vehicle['VehicleName'], native_vehicle['Weight'], native_vehicle['Volume']) != (
            vehicle['name'], vehicle['weight_capacity'], vehicle['volume_capacity']):
        raise ValueError('Native/modern fixture vehicle facts differ')
    mapping = declared[('BPR', 'LocationVehicleMaster')][0]
    if mapping['VehicleID'] != native_vehicle['VehicleID']:
        raise ValueError('Native fixture vehicle identity differs')
    for item, report, sku, location in zip(case['items'], declared[PICK],
            declared[('BPR', 'SkuAttributeData')], declared[('BPR', 'LocationAttributeData')], strict=True):
        if (report['SKUCode'], report['WhCode'], report['ParentWhCode'], report['DispatchColor']) != (
                item['sku'], item['to_location'], item['from_location'], item['dispatch_color']):
            raise ValueError('Native/modern fixture Pick identities differ')
        if (sku['SKUCode'], sku['Weight'], sku['Volume'], location['WHCode'], location['LogisticsLocation']) != (
                item['sku'], item['weight'], item['volume'], item['to_location'], item['logistics_location']):
            raise ValueError('Native/modern fixture attribute facts differ')
        if mapping['LocationID'] != item['from_location']:
            raise ValueError('Native/modern fixture parent vehicle mapping differs')
        if report['RationedReq'] != sum(item['buckets'].values()) or any(report[native] != item['buckets'][modern]
                for native, modern in zip(('TOR_B', 'TOR_R', 'TOY', 'TOG', 'TOBlue'),
                    ('to_black', 'to_red', 'to_yellow', 'to_green', 'to_blue'))):
            raise ValueError('Native/modern fixture source band quantities differ')


def original_allocations(variant='weight'):
    """Frozen full output from the existing modern owner for this new fixture.

    This is modern regression evidence, not a native answer supplied to a
    producer. It binds every original field and its original sequence.
    """
    def row(sku, wh, logistic, truck, priority, qty, remaining, weight, volume):
        return dict(case=sku, sku=sku, from_location='P', to_location=wh, logistics_location=logistic,
            truck=truck, priority=priority, picked_quantity=qty, remaining_quantity=remaining,
            total_weight=weight, total_volume=volume)
    if variant not in ('weight', 'volume'):
        raise ValueError('Unknown allocation regression variant')
    one, two = ('2.000', '4.000') if variant == 'weight' else ('4.500', '9.000')
    return [row('A', 'W1', 'L1', 1, 1, '1', '0', one, '1.000'),
            row('B', 'W2', 'L1', 1, 2, '1', '0', one, '1.000'),
            row('B', 'W2', 'L1', 2, 2, '2', '0', two, '2.000'),
            row('D', 'W3', 'L2', None, 1, '0', '2', '0', '0'),
            row('B', 'W2', 'L1', None, 2, '0', '1', '0', '0')]


def modern_state(case):
    original = producer.calculate_pick_list(deepcopy(case))
    if original != original_allocations(variant_for(case)):
        raise ValueError('Original current allocation regression changed before state qualification')
    calculate = getattr(producer, 'calculate_pick_list_state', None)
    if not callable(calculate):
        raise ValueError('Planned calculate_pick_list_state producer is not implemented; no fixture mutation permitted')
    state = calculate(deepcopy(case))
    if not isinstance(state, dict) or set(state) != {'allocations', 'LogisticPickList', 'PickListDataForTruckFormation'}:
        raise ValueError('Exact declared modern full-state API required')
    if state['allocations'] != original:
        raise ValueError('Additive state capture changed original allocation output/sequence')
    for name in ('LogisticPickList', 'PickListDataForTruckFormation'):
        if not isinstance(state[name], list) or any(not isinstance(row, dict) for row in state[name]):
            raise ValueError('Full native row dictionaries required')
    return state


def variant_for(case):
    capacities = (case['vehicle']['weight_capacity'], case['vehicle']['volume_capacity'])
    if capacities == (Decimal('5.000'), Decimal('100.000')):
        return 'weight'
    if capacities == (Decimal('100.000'), Decimal('2.500')):
        return 'volume'
    raise ValueError('Unapproved restricted fixture capacities')


def wire(value):
    # Exact existing legacy r1_runner._rows numeric checkpoint representation.
    return format(Decimal(value), 'f') if isinstance(value, (Decimal, int, float)) else value


def modern_narrow(allocations, vehicle):
    picked, residual = [], []
    for row in allocations:
        if row['truck'] is not None:
            values = (row['sku'], row['to_location'], row['from_location'], row['priority'],
                row['picked_quantity'], vehicle['name'], row['truck'], row['logistics_location'], row['total_weight'], row['total_volume'])
            picked.append(dict(zip(NARROW['logistic_pick'][1], map(wire, values))))
        else:
            values = (row['sku'], row['to_location'], row['from_location'], row['logistics_location'],
                      row['priority'], row['remaining_quantity'], vehicle['name'])
            residual.append(dict(zip(NARROW['pick_remaining'][1], map(wire, values))))
    return dict(logistic_pick=picked, pick_remaining=residual)


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
    registered = {r['path']: r['sha256'] for r in manifest['engine_sources']}
    if registered.get((SOURCE / PATH).as_posix()) != PIN:
        raise ValueError('Canonical truck-state source registration differs')
    isolation.MAPPING.clear()
    isolation.MAPPING.update(mapping)
    isolation.DATA = directory
    variables = dict(IntermediateDatabase=mapping['VFTEST_Intermediate'], ScriptExecutionFlagQuery=
        'UPDATE ' + mapping['VFTEST_Importer'] + '.dbo.ScriptExecutedFlag SET IsScriptExecuted=1 WHERE ScriptName=')
    script, = preflight_scripts([dict(source_path=(SOURCE / PATH).as_posix(), source_sha256=PIN,
        role='BPR', variables=variables)], owner_id=owner, namespace=mapping)
    return script, dict(setup_sha256=hashlib.sha256(SETUP.read_bytes()).hexdigest(),
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest())


def qualify(raw, isolation, script, case, declared, state):
    sql = FixtureSQL(raw, isolation)
    report = dict(status='STARTED', modern_case=storage(case), modern_state=storage(state),
        original_allocations=original_allocations(variant_for(case)), filler_policy=sql.fills,
        sql_receipts=[], full_images={}, narrow={}, side_effects={})
    try:
        for key, rows in declared.items():
            sql.load(*key, rows)
        inputs = {key: sql.rows(*key) for key in declared}
        report['inputs'] = storage([dict(role=k[0], table=k[1], schema=sql.schema(*k), rows=v) for k, v in inputs.items()])
        for key in declared:
            for column in sql.schema(*key):
                if column['type_name'] in ('nvarchar', 'varchar') and column['collation'] != NATIVE_COLLATION:
                    raise ValueError('Native fixture text collation differs from scalar qualification')
        scratch_before = sql.scratch()
        execute_native(raw, script, isolation, report['sql_receipts'])
        for key, expected_count in ((LOGISTIC, 21), (REMAINING, 16)):
            columns = sql.schema(*key)
            if len(columns) != expected_count:
                raise ValueError('Required full native truck-state column count differs')
            comparison = compare_rows(sql.rows(*key), state[key[1]], columns)
            comparison['strict_observed_sequence_status'] = ('PASS' if comparison['native_sequence'] == comparison['modern_sequence'] else 'FAIL')
            comparison['order_scope'] = 'strict observed state/table ordinals; no report-bag approval transfer'
            report['full_images']['.'.join(key)] = comparison
            if comparison['status'] != 'PASS':
                raise ValueError('Complete typed native truck-state image differs: ' + key[1])
            if comparison['strict_observed_sequence_status'] != 'PASS':
                raise ValueError('UNACCEPTED_STATE_TABLE_ORDER_GAP: complete typed bags agree but state/table ordinals differ')
        expected_narrow = modern_narrow(state['allocations'], case['vehicle'])
        for name, (query, fields) in NARROW.items():
            cursor = raw.execute(query)
            native_rows = [list(row) for row in cursor.fetchall()]
            actual = [dict(zip(fields, map(wire, row), strict=True)) for row in native_rows]
            comparison = dict(query=query, fields=fields, native_cells=storage(native_rows),
                native_python_types=[[type(v).__name__ for v in row] for row in native_rows],
                native_sequence=actual, modern_sequence=expected_narrow[name],
                policy='unchanged original ORDER BY NewSRNo; exact narrow fields/sequence',
                status='PASS' if actual == expected_narrow[name] else 'FAIL')
            report['narrow'][name] = comparison
            if comparison['status'] != 'PASS':
                raise ValueError('Existing ordered narrow allocation projection differs: ' + name)
        wanted_flags = mark_script_executed(inputs[FLAG], 'GenerateLogisticPickList.sql', equal=scalars.ascii_equal)
        for key, rows in inputs.items():
            if key in (LOGISTIC, REMAINING, SCRATCH):
                continue
            expected = wanted_flags if key == FLAG else rows
            comparison = compare_rows(sql.rows(*key), expected, sql.schema(*key))
            report['side_effects']['.'.join(key)] = comparison
            if comparison['status'] != 'PASS':
                raise ValueError('Unexpected native fixture side effect')
        scratch_after = sql.scratch()
        if set(scratch_after) != set(scratch_before):
            raise ValueError('Native scratch table roster changed')
        for table in scratch_before:
            comparison = compare_rows(scratch_after[table], [], sql.schema('Intermediate', table))
            report['side_effects']['scratch:' + table] = comparison
            if comparison['status'] != 'PASS':
                raise ValueError('Native scratch endpoint not empty')
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
    script, identities = prepare(owner, isolation)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    receipt = dict(schema='pick-stage-state-qualification-v1', owner=owner,
        namespace=namespace(owner), data_directory=str(data_directory(owner)), status='STARTED',
        identities=identities, implementation_pins=implementation_pins(), scalar_adapters=scalar_binding(),
        canonical_source=script.source_path, source_sha256=script.source_sha256, cases=[],
        scope='one restricted native fixture family, weight/volume variants; zero full business-day invocations',
        limitations=['unique joins, exactly one applicable vehicle, positive non-NULL dimensions and unambiguous priority ranks only',
            'duplicate joins/NULL dimensions/multiple vehicles/rank ties remain unresolved generic branches',
            'full image typed bag and strict observed sequence both required; existing narrow assertions remain exact',
            'does not accept the preserved Pick file export-order failure or certify generic full-day readiness'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as file:
        try:
            cases = fixture_cases()
            states = []
            for name, case, declared in cases:
                validate_fixture(case, declared)
                states.append((name, case, declared, modern_state(case)))  # before lease/first mutation
            with isolation.exclusive_replay(validate_schema=True):
                receipt['schema_receipts'] = [json.loads((data_directory(owner) / (db + '-schema.json')).read_text())
                    for db in namespace(owner).values()]
                with isolation.connection('VFTEST_BPR') as raw:
                    receipt['native_context'] = native_context(raw, isolation)
                    sql = FixtureSQL(raw, isolation)
                    receipt['fixture_preflight'] = preflight_fixtures(sql, [(name, declared) for name, _, declared, _ in states])
                    if receipt['fixture_preflight']['status'] != 'PASS':
                        raise ValueError('Full fixture schema preflight failed before mutation')
                    for name, case, declared, state in states:
                        originals = {key: sql.rows(*key) for key in declared}
                        original_scratch = sql.scratch()
                        raw.raw.autocommit = False
                        try:
                            result = qualify(raw, isolation, script, case, declared, state)
                            result['name'] = name
                            receipt['cases'].append(result)
                        finally:
                            raw.rollback()
                            raw.raw.autocommit = True
                        result['outer_rollback'] = raw.execute('SELECT @@TRANCOUNT').fetchval() == 0
                        restored_scratch = sql.scratch()
                        if set(restored_scratch) != set(original_scratch):
                            raise ValueError('Rollback scratch roster changed')
                        result['seed_preservation'] = {'.'.join(k): compare_rows(sql.rows(*k), rows, sql.schema(*k)) for k, rows in originals.items()}
                        result['scratch_preservation'] = {table: compare_rows(restored_scratch[table], rows,
                            sql.schema('Intermediate', table)) for table, rows in original_scratch.items()}
                        restored = all(c['status'] == 'PASS' for c in (*result['seed_preservation'].values(), *result['scratch_preservation'].values()))
                        if result['status'] != 'PASS' or not result['outer_rollback'] or not restored:
                            raise ValueError('Stopped at first restricted truck-state qualification failure: ' + name)
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
    report = run(options.owner, options.output)
    print(json.dumps(dict(status=report['status'], cases=len(report['cases']), output=str(options.output))))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
