"""Pure fixture/guard proofs only; no SQL connections or business runs."""
from contextlib import nullcontext
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from parity import verify_complete_daily_inputs as verifier
from parity.verify_complete_daily_producers import FixtureSQL, preflight_fixture_suite


class DeclaredSchema:
    """Read retained canonical DDL, never a database or engine."""
    def schema(self, role, table):
        if role == 'Intermediate':
            return [dict(name=n, type_name='date' if n == 'ReportDate' else 'nvarchar',
                nullable=True, identity=False, computed=False, max_length=100, precision=0,
                scale=0, collation=verifier.NATIVE_COLLATION)
                for n in ('ReportDate', 'SKUCode', 'WhCode', 'TechColor')]
        source = verifier.SOURCE / ('Scripts/DBCreation/' + role + '_DBCreation.sql')
        text = source.read_text(encoding='cp1252')
        match = re.search(r'CREATE TABLE \[dbo\]\.\[' + re.escape(table) + r'\]\((.*?)\)\s*ON', text, re.S)
        if match is None:
            raise ValueError('Canonical fixture table not found: ' + table)
        columns = []
        for name, kind, arguments, nullability in re.findall(
                r'^\s*\[([^]]+)\]\s+\[([^]]+)\](?:\(([^)]+)\))?\s+(NOT NULL|NULL)', match[1], re.M):
            args = [int(a.strip()) for a in arguments.split(',')] if arguments else []
            columns.append(dict(name=name, type_name=kind, nullable=nullability == 'NULL',
                identity=False, computed=False,
                max_length=args[0] * 2 if kind == 'nvarchar' else args[0] if kind == 'varchar' else 0,
                precision=args[0] if kind == 'decimal' else 0,
                scale=args[1] if kind == 'decimal' else 0,
                collation=verifier.NATIVE_COLLATION if 'char' in kind else None))
        if not columns:
            raise ValueError('No canonical fixture fields parsed')
        return columns

    def fill(self, column):
        return FixtureSQL(None, None).fill(column)


class InputQualificationTests(unittest.TestCase):
    def test_three_bounded_cases_and_independent_suppliers(self):
        cases = verifier.fixture_cases()
        self.assertEqual([kind for _, kind, _ in cases], ['supplier', 'supplier', 'pick'])
        declaration = cases[0][2]
        before = deepcopy(declaration)
        with patch.object(verifier, 'calculate_bor', wraps=verifier.calculate_bor) as producer:
            wanted, quantities, lineage = verifier.modern_outputs('supplier', declaration)
        producer.assert_called_once()
        rows = wanted[('BPR', 'SupplierDispatchReq')]
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(len(r) == 28 for r in rows))
        self.assertEqual(len([r for r in rows if r['SKUCode'] == 'BLACK']), 8)
        self.assertFalse(any(r['SKUCode'] in ('GREEN', 'ZERO', 'CHILD') for r in rows))
        self.assertTrue(any(r['SKUCode'] == 'BLUE' and r['DispatchReq'] == 5 for r in rows))
        self.assertTrue(any(r['SKULocAtt02'] is None for r in rows))
        self.assertEqual(len(lineage), len(rows))
        self.assertEqual(quantities['owner'], 'calculate_bor')
        self.assertEqual(declaration, before)

    def test_refresh_uses_explicit_importer_input_not_stale_opening(self):
        declaration = verifier.supplier_fixture(True)
        wanted, quantities, _ = verifier.modern_outputs('supplier', declaration)
        self.assertEqual(quantities['inputs'][0]['sob'], Decimal(60))
        self.assertEqual(wanted[('BPR', 'SOBData')], declaration[('Importer', 'SOBDataRaw')])
        self.assertEqual(wanted[('BPR', 'MOQData')], declaration[('Importer', 'MOQDataRaw2')])
        self.assertNotEqual(wanted[('BPR', 'SOBData')], declaration[('BPR', 'SOBData')])

    def test_refresh_projects_canonical_bpr_columns_from_full_raw_roster(self):
        declaration = verifier.supplier_fixture(True)
        for table in ('SOBDataRaw', 'MOQDataRaw2'):
            for row in declaration[('Importer', table)]:
                row['SupplierDescription'] = 'raw metadata stays in Importer'
        before = deepcopy(declaration)
        wanted, _, _ = verifier.modern_outputs('supplier', declaration)
        for table, quantity in (('SOBData', 'SOB'), ('MOQData', 'MOQ')):
            self.assertTrue(all(set(row) == {'SKUCode', 'WHCode', 'SupplierCode', quantity}
                                for row in wanted[('BPR', table)]))
        self.assertEqual(len(wanted[('BPR', 'SupplierDispatchReq')]), 12)
        self.assertEqual(declaration, before)

    def test_full_pick_uses_actual_band_owner_and_join_occurrences(self):
        declaration = verifier.pick_fixture()
        with patch.object(verifier, 'bifurcate_rationed_requirement',
                          wraps=verifier.bifurcate_rationed_requirement) as producer:
            wanted, quantities, _ = verifier.modern_outputs('pick', declaration)
        rows = wanted[('BPR', 'vf_PickListReport')]
        self.assertEqual(producer.call_count, 5)
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(len(r) == 69 for r in rows))
        physical = [r for r in rows if r['SKUCode'] == 'DUP' and r['ParentWhCode'] == 'P']
        virtual = [r for r in rows if r['SKUCode'] == 'DUP' and r['ParentWhCode'] == 'W']
        self.assertEqual((len(physical), len(virtual)), (2, 2))
        self.assertEqual(physical[0]['AllocatedForDirectOrders'], 0)
        self.assertEqual(virtual[0]['AllocatedForDirectOrders'], 3)
        self.assertEqual(physical[0]['ParentStockPercentageForRationing'], 90)
        self.assertEqual(virtual[0]['ParentStockPercentageForRationing'], 75)
        self.assertEqual(virtual[0]['ParentNormPercentReservation'], 20)
        self.assertTrue(all(r['PostPipelineInventoryPen'] is None for r in rows))
        one = next(r for r in rows if r['SKUCode'] == 'ONE')
        self.assertEqual((one['TOR_B'], one['TOR_R'], one['TOY'], one['TOG'], one['TOBlue']), (4, 0, 0, 0, 0))
        self.assertEqual(len(quantities['probes']), 5)

    def test_no_native_target_outputs_can_feed_modern(self):
        declaration = verifier.supplier_fixture()
        wanted = verifier.modern_outputs('supplier', declaration)[0]
        declaration[('BPR', 'SupplierDispatchReq')] = [dict(unknown='poison')]
        declaration[('BPR', 'VendorDispatchReq')] = [dict(unknown='poison')]
        self.assertEqual(verifier.modern_outputs('supplier', declaration)[0], wanted)
        declaration = verifier.pick_fixture()
        wanted = verifier.modern_outputs('pick', declaration)[0]
        declaration[('BPR', 'vf_PickListReport')] = [dict(unknown='poison')]
        self.assertEqual(verifier.modern_outputs('pick', declaration)[0], wanted)

    def test_native_full_schemas_and_fixture_preflight_from_canonical_ddl(self):
        schema = DeclaredSchema()
        supplier = schema.schema('BPR', 'SupplierDispatchReq')
        pick = schema.schema('BPR', 'vf_PickListReport')
        self.assertEqual(len(supplier), 28)
        self.assertEqual(len(pick), 69)
        self.assertEqual({c['name'] for c in supplier}, set(verifier.bridge.field_maps()['SupplierDispatchReq']))
        self.assertEqual({c['name'] for c in pick}, set(verifier.bridge.PICK_FIELDS))
        cases = [(name, 'BPR', verifier.PATHS[kind][0], declared)
                 for name, kind, declared in verifier.fixture_cases()]
        report = preflight_fixture_suite(schema, cases)
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['status'], 'PASS')

    def test_float_source_bridge_does_not_generalize_or_hide_types(self):
        self.assertEqual(verifier.fixture_share(60.0), Decimal(60))
        for value in (60, '60', 60.5, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                verifier.fixture_share(value)
        self.assertTrue(all(type(r['SOB']) is float for r in verifier.supplier_fixture()[('BPR', 'SOBData')]))

    def test_invalid_quantity_owner_stops_before_native_execution(self):
        declaration = verifier.supplier_fixture()
        declaration[verifier.RRR].append(dict(declaration[verifier.RRR][0]))
        class MemorySQL:
            def __init__(self, *args):
                self.fills = []
            def load(self, *args):
                pass
            def rows(self, *key):
                return declaration[key]
            def schema(self, *key):
                return []
        with patch.object(verifier, 'FixtureSQL', MemorySQL), patch.object(verifier, 'execute_native') as native:
            report = verifier.qualify(None, None, None, 'bad-owner', 'supplier', declaration)
        self.assertEqual(report['status'], 'FAIL')
        self.assertIn('not unique', report['failure'])
        native.assert_not_called()

    def test_failed_case_is_rolled_back_and_never_retried(self):
        from parity import legacy_isolation as isolation
        class EmptySQL:
            def __init__(self, *args):
                pass
            def rows(self, *args):
                return []
            def schema(self, *args):
                return []
            def scratch(self):
                return {}
        raw = Mock()
        raw.raw.autocommit = True
        raw.execute.return_value.fetchval.return_value = 0
        scripts = {k: SimpleNamespace(source_path=path, source_sha256=pin) for k, (path, pin) in verifier.PATHS.items()}
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'proof.json'
            for db in verifier.namespace(verifier.OWNER).values():
                (Path(directory) / (db + '-schema.json')).write_text('{}')
            with patch.object(verifier, 'guard_options', return_value=output), \
                    patch.object(verifier, 'prepare', return_value=(scripts, {})), \
                    patch.object(verifier, 'data_directory', return_value=Path(directory)), \
                    patch.object(verifier, 'scalar_binding', return_value={}), \
                    patch.object(verifier, 'native_context', return_value={}), \
                    patch.object(verifier, 'preflight_fixture_suite', return_value={'status': 'PASS'}), \
                    patch.object(verifier, 'FixtureSQL', EmptySQL), \
                    patch.object(isolation, 'exclusive_replay', return_value=nullcontext()), \
                    patch.object(isolation, 'connection', return_value=nullcontext(raw)), \
                    patch.object(verifier, 'qualify', return_value={'status': 'FAIL'}) as qualify:
                receipt = verifier.run(verifier.OWNER, output)
            self.assertEqual(receipt['status'], 'FAIL')
            self.assertEqual(len(receipt['cases']), 1)
            self.assertEqual(qualify.call_count, 1)
            self.assertEqual(json.loads(output.read_text())['status'], 'FAIL')
        raw.rollback.assert_called_once()
        raw.commit.assert_not_called()
        self.assertTrue(raw.raw.autocommit)


if __name__ == '__main__':
    unittest.main()
