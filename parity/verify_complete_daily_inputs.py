"""Small rollback-native input bridge qualification, never a business-day run.

Supplier28 and Pick69 compare their exact INSERT endpoints. Req7 and BOR3 have
retained evidence, not a new native proof in this suite.
Every quantity is calculated independently from declared stage inputs by the
existing R1 owners. Neither native outputs nor late report reads feed modern.
"""
import argparse
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application import complete_daily_inputs as bridge
from mta.domain import complete_daily_scalars as scalars
from mta.domain.complete_daily_completion import mark_script_executed
from mta.domain.remaining_capabilities import calculate_bor
from mta.domain.r1_current_day import RationedRequirement, bifurcate_rationed_requirement
from mta.serialization import storage
from parity.adapters.legacy.complete_daily_sql import namespace, data_directory, preflight_scripts
from parity.verify_complete_daily_completion import execute_native, SETUP
from parity.verify_complete_daily_producers import (
    FixtureSQL, compare_rows, preflight_fixture_suite, native_context, scalar_binding,
    guard_options, OWNER, OUTPUT_ROOT, SOURCE, TODAY, NATIVE_COLLATION)

PATHS = {key: bridge.SOURCES[key] for key in ('supplier', 'pick')}
FLAG = ('Importer', 'ScriptExecutedFlag')
RRR = ('BPR', 'vf_RationedReqReport')
MASTER = ('BPR', 'BPRMaster')
SCRATCH = ('Intermediate', 'GulfOil_TechColorData')
IMPLEMENTATION_FILES = (
    'mta/application/complete_daily_inputs.py', 'mta/presentation/rrr.py',
    'mta/domain/remaining_capabilities.py', 'mta/domain/r1_current_day.py',
    'mta/domain/complete_daily_scalars.py', 'mta/domain/complete_daily_completion.py',
    'mta/serialization.py', 'mta/runtime/relational_state.py',
    'parity/verify_complete_daily_inputs.py', 'parity/verify_complete_daily_completion.py',
    'parity/verify_complete_daily_producers.py', 'parity/adapters/legacy/complete_daily_sql.py',
    'parity/legacy_isolation.py', 'baseline/production-state-schema.json')


def implementation_pins():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in IMPLEMENTATION_FILES}


def report_row(sku, wh, parent, **overrides):
    """Complete explicit stage fixture; no inferred production defaults."""
    row = {}
    for ordinal, (name, kind) in enumerate(bridge.CATALOG['tables']['BPR/vf_RationedReqReport']):
        row[name] = (Decimal('1.25') if kind == 'decimal' else
                     True if kind == 'bit' else 2 if kind == 'int' else 'unit')
    row.update(SKUCode=sku, WhCode=wh, ParentWhCode=parent, SKUName=None,
        WhName='receiving', ParentWhName=None, Norm=9, VirtualNorm=9,
        Stock=1, GIT=1, StockForReqCalc=1, Req=7, RationedReq=7,
        DispatchColor='Black', TechColor=None, ParentPackSize=4, PackSize=2,
        LeftoverStock=5, AllocatedForDirectOrders=3,
        StockPercentageForRationing=75, NormPercentReservation=20,
        ParentStockPercentageForRationing=90, ParentNormPercentReservation=10)
    row.update(overrides)
    return row


def common(kind):
    marker = Path(PATHS[kind][0]).name
    return {FLAG: [dict(ScriptName=marker, ModuleName='BPR',
                       IsScriptExecuted=False, IsScriptCritical=True)],
            SCRATCH: [dict(ReportDate=TODAY, SKUCode='SCRATCH', WhCode='W', TechColor='NA')]}


def supplier_fixture(refresh=False):
    declared = common('supplier')
    specifications = [
        ('BLACK', 9, 9, 0, 0, 9, 'Black', 60, 0),
        ('RED', 9, 9, 1, 0, 8, 'Red', 100, 12),
        ('YELLOW', 10, 10, -2, 1, 11, 'Yellow', 33, 0),
        ('GREEN', 9, 9, 4, 1, 4, 'Green', 100, 6),
        ('BLUE', 0, 0, 0, 0, 2, 'Blue', 100, 5),
        ('WHITE', 9, 9, 8, 0, 1, 'White', 100, 0),
        ('ZERO', 9, 9, 0, 0, 0, 'Black', 100, 0),
        ('CHILD', 9, 9, 0, 0, 9, 'Black', 100, 0)]
    rationed, master, sob, moq = [], [], [], []
    for sku, norm, vn, stock, git, req, colour, share, minimum in specifications:
        rationed.append(report_row(sku, 'W', 'PLANT', Norm=norm, VirtualNorm=vn,
            Stock=stock, StockForReqCalc=stock, GIT=git, Req=req, DispatchColor=colour))
        master.append(dict(SKUCode=sku, WHCode='W', ParentWhCode='PLANT', Norm=norm))
        sob.append(dict(SKUCode=sku, WHCode='W', SupplierCode='PLANT', SOB=float(share)))
        moq.append(dict(SKUCode=sku, WHCode='W', SupplierCode='PLANT', MOQ=minimum))
    # Repeated source suppliers have separate occurrence lineage; duplicate
    # master/attribute joins amplify the final INSERT without a tie-break.
    sob.append(dict(sob[0]))
    master.append(dict(master[0]))
    master.append(dict(SKUCode='CHILD', WHCode='PLANT', ParentWhCode='OUTSIDE', Norm=9))
    attrs = [dict(SKUCode='BLACK', LocCode='W',
                  **{f'c{i}': None if i % 2 else 'A' for i in range(1, 16)}),
             dict(SKUCode='black ', LocCode='w',
                  **{f'c{i}': None if i % 2 else 'B' for i in range(1, 16)})]
    declared.update({MASTER: master, RRR: rationed,
        ('BPR', 'SkuLocAttributeData'): attrs,
        ('BPR', 'SOBData'): [dict(r, SOB=1.0) for r in sob] if refresh else sob,
        ('BPR', 'MOQData'): [dict(r, MOQ=99) for r in moq] if refresh else moq,
        ('Importer', 'SOBDataRaw'): sob if refresh else [],
        ('Importer', 'MOQDataRaw2'): moq if refresh else [],
        ('Vendor', 'VendorList'): [], ('BPR', 'BPR_Table'): [],
        ('BPR', 'SupplierDispatchReq'): [], ('BPR', 'VendorDispatchReq'): []})
    return declared


def pick_fixture():
    declared = common('pick')
    rows = [report_row('DUP', 'W', 'P'),
            report_row('ONE', 'W', 'P', VirtualNorm=1, Stock=0, GIT=0, RationedReq=4),
            report_row('EXCLUDE', 'W', 'P', Req=0),
            report_row('NO-PARENT', 'W', 'OUTSIDE')]
    masters = [dict(SKUCode=r['SKUCode'], WHCode='P', ParentWhCode='OUTSIDE', Norm=9)
               for r in rows if r['SKUCode'] != 'NO-PARENT']
    masters.append(dict(masters[0]))
    virtual = [dict(SKUCode='DUP', WhCode='V', ParentWhCode='W', VirtualNorm=3, OverdueOrderQty=3)] * 2
    declared.update({MASTER: masters, RRR: rows,
                     ('BPR', 'VirtualNodes'): virtual, ('BPR', 'vf_PickListReport'): []})
    return declared


def fixture_cases():
    return [('supplier-opening-duplicates-null-attributes', 'supplier', supplier_fixture()),
            ('supplier-explicit-importer-refresh', 'supplier', supplier_fixture(True)),
            ('pick-physical-virtual-duplicates-reservation-aliases', 'pick', pick_fixture())]


def _one(rows, left, fields):
    matches = [r for r in rows if all(scalars.ascii_equal(left[a], r[b]) for a, b in fields)]
    if len(matches) != 1:
        raise ValueError('Declared fixture quantity owner is not unique')
    return matches[0]


def fixture_share(value):
    """The declared SOB float fixture is integral and exactly representable.

    The R1 quantity owner accepts exact decimals, not binary floats. Restrict
    this fixture bridge to its declared integer SOB values and retain the
    original float cells in evidence; never generalize float conversion.
    """
    if type(value) is not float or not value.is_integer() or abs(value) > 2**53:
        raise ValueError('Fixture SOB requires an exactly representable integral native float')
    return Decimal.from_float(value)


def modern_outputs(kind, inputs):
    """Only fixture INPUT tables are consumed; target outputs are never read."""
    quantities, lineage, wanted = {}, {}, {}
    if kind == 'supplier':
        sob, moq = inputs[('BPR', 'SOBData')], inputs[('BPR', 'MOQData')]
        sob = inputs[('Importer', 'SOBDataRaw')] or sob
        moq = inputs[('Importer', 'MOQDataRaw2')] or moq
        items, occurrences = [], []
        for ordinal, supplier in enumerate(sob):
            key = [('SKUCode', 'SKUCode'), ('WHCode', 'WhCode')]
            report = _one(inputs[RRR], supplier, key)
            minimum = _one(moq, supplier, key[:1] + [('WHCode', 'WHCode'), ('SupplierCode', 'SupplierCode')])
            case = 'fixture_' + str(ordinal + 1).zfill(3)
            item = dict(case=case, sku=supplier['SKUCode'], location=supplier['WHCode'],
                supplier=supplier['SupplierCode'], norm=report['Norm'], virtual_norm=report['VirtualNorm'],
                stock=report['Stock'], git=report['GIT'], stock_for_requirement=report['StockForReqCalc'],
                requirement=report['Req'], dispatch_color=report['DispatchColor'],
                sob=fixture_share(supplier['SOB']), moq=minimum['MOQ'], pack_size=report['PackSize'])
            items.append(item)
            occurrences.append(dict(case=case, sku_code=item['sku'], location_code=item['location'], supplier=item['supplier']))
        calculated = calculate_bor({'items': items}, allow_negative_stock_for_requirement=True)
        quantities.update(owner='calculate_bor',
                          inputs=items, outputs=calculated)
        rows, lineage = bridge.supplier_dispatch(sourcing=occurrences, bor=calculated,
            bpr_master=inputs[MASTER], sku_loc_attributes=inputs[('BPR', 'SkuLocAttributeData')],
            equal=scalars.ascii_equal)
        # Canonical importer refresh INSERTs project four columns; the raw
        # tables additionally retain SupplierDescription. Do not carry raw
        # metadata into the expected BPR table roster.
        bpr_sob = [{field: row[field] for field in ('SKUCode', 'WHCode', 'SupplierCode', 'SOB')}
                   for row in sob]
        bpr_moq = [{field: row[field] for field in ('SKUCode', 'WHCode', 'SupplierCode', 'MOQ')}
                   for row in moq]
        wanted.update({('BPR', 'SupplierDispatchReq'): rows, ('BPR', 'VendorDispatchReq'): [],
                       ('BPR', 'SOBData'): bpr_sob, ('BPR', 'MOQData'): bpr_moq})
    elif kind == 'pick':
        bands, probes = [], []
        for ordinal, row in enumerate(inputs[RRR]):
            parents = [(i, m) for i, m in enumerate(inputs[MASTER]) if row['Req'] > 0
                       and scalars.ascii_equal(row['SKUCode'], m['SKUCode'])
                       and scalars.ascii_equal(row['ParentWhCode'], m['WHCode'])]
            virtual = [(i, v) for i, v in enumerate(inputs[('BPR', 'VirtualNodes')])
                       if scalars.ascii_equal(row['SKUCode'], v['SKUCode'])
                       and scalars.ascii_equal(row['WhCode'], v['ParentWhCode'])]
            for branch, matches in [('physical', parents), ('virtual', virtual)]:
                for join_ordinal, _ in matches:
                    args = RationedRequirement(row['SKUCode'], row['WhCode'],
                        row['ParentWhCode'] if branch == 'physical' else row['WhCode'],
                        Decimal(row['VirtualNorm']), Decimal(row['Stock']), Decimal(row['GIT']),
                        Decimal(row['RationedReq'] if branch == 'physical' else 0))
                    band = bifurcate_rationed_requirement(args)
                    bands.append(band)
                    probes.append(dict(rationed_ordinal=ordinal, branch=branch, join_ordinal=join_ordinal,
                        input=asdict(args), output=band))
        wanted[('BPR', 'vf_PickListReport')] = bridge.pick_report(rationed=inputs[RRR], bands=bands)
        quantities.update(owner='bifurcate_rationed_requirement', probes=probes)
    else:
        raise ValueError('Only explicitly staged Supplier/Pick endpoints are permitted')
    wanted[FLAG] = mark_script_executed(inputs[FLAG], Path(PATHS[kind][0]).name, equal=scalars.ascii_equal)
    return wanted, quantities, lineage


def prepare(owner, isolation):
    if isolation._lease is not None:
        raise ValueError('Cannot bind an owner during an active lease')
    mapping, directory = namespace(owner), data_directory(owner)
    setup = json.loads(SETUP.read_text())
    if (setup['owner_id'] != owner or setup['namespace'] != mapping
            or Path(setup['data_directory']).resolve() != directory.resolve()
            or setup.get('schema_only') is not True or setup.get('business_invocations') != 0):
        raise ValueError('Owned schema-only setup receipt differs')
    manifest_path = ROOT / 'baseline/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    pins = {row['path']: row['sha256'] for row in manifest['engine_sources']}
    for path, expected in PATHS.values():
        if pins.get((SOURCE / path).as_posix()) != expected:
            raise ValueError('Canonical input-bridge source registration differs')
    isolation.MAPPING.clear()
    isolation.MAPPING.update(mapping)
    isolation.DATA = directory
    variables = dict(IntermediateDatabase=mapping['VFTEST_Intermediate'],
        ImporterDatabase=mapping['VFTEST_Importer'], VendorDatabase=mapping['VFTEST_Vendor'],
        ScriptExecutionFlagQuery='UPDATE ' + mapping['VFTEST_Importer']
            + '.dbo.ScriptExecutedFlag SET IsScriptExecuted=1 WHERE ScriptName=')
    scripts = preflight_scripts([dict(source_path=(SOURCE / path).as_posix(),
        source_sha256=pin, role='BPR', variables=variables) for path, pin in PATHS.values()],
        owner_id=owner, namespace=mapping)
    return dict(zip(PATHS, scripts)), dict(setup_sha256=hashlib.sha256(SETUP.read_bytes()).hexdigest(),
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest())


def comparison(sql, key, wanted):
    native, columns = sql.rows(*key), sql.schema(*key)
    return compare_rows(native, wanted, columns)


def qualify(raw, isolation, script, name, kind, declared):
    sql = FixtureSQL(raw, isolation)
    report = dict(name=name, kind=kind, status='STARTED', declared=storage([
        dict(role=k[0], table=k[1], rows=v) for k, v in declared.items()]),
        filler_policy=sql.fills, sql_receipts=[], comparisons={})
    try:
        for key, rows in declared.items():
            sql.load(*key, rows)
        inputs = {key: sql.rows(*key) for key in declared}
        report['inputs'] = storage([dict(role=k[0], table=k[1], schema=sql.schema(*k), rows=v)
                                    for k, v in inputs.items()])
        wanted, quantities, lineage = modern_outputs(kind, inputs)
        report.update(independent_quantities=storage(quantities), occurrence_lineage=lineage)
        # All dependent identifier fields use the independently qualified domain.
        for key in declared:
            for column in sql.schema(*key):
                if column['name'] in ('SKUCode', 'WHCode', 'WhCode', 'LocCode', 'ParentWhCode', 'SupplierCode', 'ScriptName'):
                    if column['collation'] != NATIVE_COLLATION:
                        raise ValueError('Fixture join collation differs from qualified scalar domain')
        scratch_before = sql.scratch()
        execute_native(raw, script, isolation, report['sql_receipts'])
        for key, expected in wanted.items():
            result = comparison(sql, key, expected)
            report['comparisons']['.'.join(key)] = result
            if result['status'] != 'PASS':
                raise ValueError('Exact native input-bridge boundary differs: ' + '.'.join(key))
        for key, original in inputs.items():
            if key in wanted or key[0] == 'Intermediate':
                continue
            result = comparison(sql, key, original)
            report['comparisons']['unchanged:' + '.'.join(key)] = result
            if result['status'] != 'PASS':
                raise ValueError('Unexpected fixture input mutation')
        scratch_after = sql.scratch()
        if set(scratch_after) != set(scratch_before):
            raise ValueError('Native intermediate table roster changed')
        for table, rows in scratch_before.items():
            result = compare_rows(scratch_after[table], [] if kind != 'pick' else rows,
                                  sql.schema('Intermediate', table))
            report['comparisons']['scratch:' + table] = result
            if result['status'] != 'PASS':
                raise ValueError('Native scratch endpoint differs')
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
        try:
            report['native_after_failure'] = storage([dict(role=k[0], table=k[1], rows=sql.rows(*k)) for k in declared])
        except Exception as read_error:
            report['failure_readback_error'] = str(read_error)
    return report


def run(owner, output):
    output = guard_options(owner, output)
    from parity import legacy_isolation as isolation
    prepared, identities = prepare(owner, isolation)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    receipt = dict(schema='complete-daily-inputs-qualification-v1', owner=owner,
        namespace=namespace(owner), data_directory=str(data_directory(owner)), status='STARTED',
        identities=identities, implementation_pins=implementation_pins(), scalar_adapters=scalar_binding(),
        sources={k: dict(path=s.source_path, sha256=s.source_sha256) for k, s in prepared.items()}, cases=[],
        scope='rollback-only small stage fixtures; zero full business-day invocations',
        limitations=['exact typed bags retain all observed sequences; full31 remains positional',
            'Supplier28/Pick69 only at exact INSERT endpoint, not later post-ration writes',
            'Req7/BOR3 retained evidence is not requalified by this fixture suite; full row owners remain unavailable',
            'ASCII scalar domain only; SOB restricted to exactly representable integral native float fixtures',
            'explicit VendorList empty; fallback supplier branch outside these fixtures'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as file:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                receipt['schema_receipts'] = [json.loads((data_directory(owner) / (db + '-schema.json')).read_text())
                    for db in namespace(owner).values()]
                with isolation.connection('VFTEST_BPR') as raw:
                    receipt['native_context'] = native_context(raw, isolation)
                    cases = fixture_cases()
                    sql = FixtureSQL(raw, isolation)
                    receipt['fixture_preflight'] = preflight_fixture_suite(sql,
                        [(name, 'BPR', PATHS[kind][0], declared) for name, kind, declared in cases])
                    if receipt['fixture_preflight']['status'] != 'PASS':
                        raise ValueError('Entire fixture suite failed schema preflight before mutation')
                    for name, kind, declared in cases:
                        originals = {key: sql.rows(*key) for key in declared}
                        original_scratch = sql.scratch()
                        raw.raw.autocommit = False
                        try:
                            case = qualify(raw, isolation, prepared[kind], name, kind, declared)
                            receipt['cases'].append(case)
                        finally:
                            raw.rollback()
                            raw.raw.autocommit = True
                        case['outer_rollback'] = raw.execute('SELECT @@TRANCOUNT').fetchval() == 0
                        restored_scratch = sql.scratch()
                        if set(restored_scratch) != set(original_scratch):
                            raise ValueError('Rollback intermediate table roster changed')
                        case['seed_preservation'] = {'.'.join(k): comparison(sql, k, rows) for k, rows in originals.items()}
                        case['scratch_preservation'] = {name: compare_rows(restored_scratch[name], rows,
                            sql.schema('Intermediate', name)) for name, rows in original_scratch.items()}
                        restored = all(r['status'] == 'PASS' for r in (
                            *case['seed_preservation'].values(), *case['scratch_preservation'].values()))
                        if case['status'] != 'PASS' or not case['outer_rollback'] or not restored:
                            raise ValueError('Stopped at first input-bridge qualification failure: ' + name)
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
