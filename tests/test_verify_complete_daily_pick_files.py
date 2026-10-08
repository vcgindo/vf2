"""No SQL: generic fixture schema, strict resultset and rollback guard tests."""
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

from mta.serialization import storage
from parity import verify_complete_daily_pick_files as verifier
from parity.verify_complete_daily_producers import FixtureSQL


def observed(resultsets):
    return [dict(fields=list(r['fields']), rows=storage(r['rows']),
        python_types=[[type(value).__name__ for value in row] for row in r['rows']]) for r in resultsets]


class CanonicalGenericSchema:
    def schema(self, role, table):
        raw = (verifier.SOURCE / ('Scripts/DBCreation/' + role + '_DBCreation.sql')).read_bytes()
        text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'cp1252')
        match = re.search(r'CREATE TABLE \[dbo\]\.\[' + re.escape(table) + r'\]\((.*?)\)\s*ON', text, re.S | re.I)
        if match is None:
            raise ValueError('Generic canonical fixture table missing')
        columns = []
        pattern = r'^\s*\[([^]]+)\]\s*(?:\[([a-z]+)\]|([a-z]+))(?:\(([^)]+)\))?\s+(NOT NULL|NULL)'
        for name, bracket_kind, bare_kind, arguments, nullability in re.findall(pattern, match[1], re.M | re.I):
            kind = (bracket_kind or bare_kind).lower()
            args = [int(a.strip()) for a in arguments.split(',')] if arguments else []
            columns.append(dict(name=name, type_name=kind, nullable=nullability.upper() == 'NULL',
                identity=False, computed=False, max_length=args[0]*2 if kind == 'nvarchar' else 0,
                precision=args[0] if kind == 'decimal' else 0, scale=args[1] if kind == 'decimal' else 0,
                collation=verifier.NATIVE_COLLATION if 'char' in kind else None))
        if not columns:
            raise ValueError('Generic native fixture schema could not be parsed')
        return columns

    def fill(self, column):
        return FixtureSQL(None, None).fill(column)


class PickFileQualificationTests(unittest.TestCase):
    def test_mixed_and_empty_fixtures_have_generic_schema_and_all_four_endpoints(self):
        cases = verifier.fixture_cases()
        self.assertEqual(len(cases), 2)
        schema = CanonicalGenericSchema()
        self.assertEqual(len(schema.schema(*verifier.LOGISTIC)), 21)
        self.assertEqual(len(schema.schema(*verifier.REMAINING)), 16)
        report = verifier.preflight_fixtures(schema, cases)
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['status'], 'PASS')
        self.assertTrue(all('GulfOil' not in p['table'] for p in report['populations']))
        for _, declared in cases:
            before = deepcopy(declared)
            projections = verifier.projections.project_reports(logistic_pick_list=declared[verifier.LOGISTIC],
                pick_list_data_for_truck_formation=declared[verifier.REMAINING])
            self.assertEqual(len(projections), 4)
            self.assertEqual(declared, before)
            for output in projections.values():
                comparison = verifier.compare_resultsets(observed(output['resultsets']), output['resultsets'])
                self.assertEqual(comparison['status'], 'PASS')
                self.assertFalse(comparison['unaccepted_file_order_gap'])

    def test_same_typed_bag_reorder_is_unaccepted_and_fails(self):
        _, declared = verifier.fixture_cases()[0]
        expected = verifier.projections.logistic_pick_list_report(declared[verifier.LOGISTIC])['resultsets']
        native = observed(expected)
        native[1]['rows'].reverse()
        native[1]['python_types'].reverse()
        result = verifier.compare_resultsets(native, expected)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['unaccepted_file_order_gap'])
        self.assertEqual(result['resultsets'][1]['typed_bag_status'], 'PASS')
        self.assertEqual(result['resultsets'][1]['strict_sequence_status'], 'FAIL')

    def test_header_literal_columns_resultset_count_and_duplicate_loss_are_failures(self):
        _, declared = verifier.fixture_cases()[0]
        expected = verifier.projections.logistic_pick_list_report(declared[verifier.LOGISTIC])['resultsets']
        native = observed(expected)
        native[0]['rows'][0][0] = 'changed header'
        self.assertEqual(verifier.compare_resultsets(native, expected)['status'], 'FAIL')
        native = observed(expected)
        native[0]['fields'][0] = 'invented label'
        self.assertEqual(verifier.compare_resultsets(native, expected)['status'], 'FAIL')
        self.assertEqual(verifier.compare_resultsets(observed(expected)[:1], expected)['status'], 'FAIL')
        native = observed(expected)
        native[1]['rows'].pop()
        native[1]['python_types'].pop()
        result = verifier.compare_resultsets(native, expected)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['resultsets'][1]['typed_bag_status'], 'FAIL')

    def test_approved_four_file_data_bags_retain_strict_failure_and_exact_headers(self):
        _, declared = verifier.fixture_cases()[0]
        outputs = verifier.projections.project_reports(logistic_pick_list=declared[verifier.LOGISTIC],
            pick_list_data_for_truck_formation=declared[verifier.REMAINING])
        for kind, projection in outputs.items():
            expected = projection['resultsets']
            native = observed(expected)
            native[1]['rows'].reverse()
            native[1]['python_types'].reverse()
            result = verifier.compare_resultsets(native, expected, file_report=kind)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['strict_sequence_status'], 'FAIL')
            self.assertTrue(result['qualified_file_order_difference'])
            native[0]['rows'][0][0] = 'changed header'
            self.assertEqual(verifier.compare_resultsets(native, expected, file_report=kind)['status'], 'FAIL')
            native = observed(expected)
            native[1]['rows'].pop()
            native[1]['python_types'].pop()
            self.assertEqual(verifier.compare_resultsets(native, expected, file_report=kind)['status'], 'FAIL')
        with self.assertRaisesRegex(ValueError, 'restricted'):
            verifier.compare_resultsets([], [], file_report='API')

    def test_decimal_type_sidecar_is_lossless_and_never_accepts_wire_text_as_native_decimal(self):
        expected = [dict(fields=('Amount',), types=('decimal(13,3)',), rows=[(Decimal('1.250'),), (None,)])]
        native = observed(expected)
        restored = verifier.restore_resultset(native[0])
        self.assertEqual(restored, [[Decimal('1.250')], [None]])
        self.assertEqual(verifier.compare_resultsets(native, expected)['status'], 'PASS')
        native[0]['python_types'][0][0] = 'str'
        self.assertEqual(verifier.compare_resultsets(native, expected)['status'], 'FAIL')
        native[0]['python_types'] = []
        with self.assertRaises(ValueError):
            verifier.restore_resultset(native[0])

    def test_preflight_audits_later_case_before_any_loader_mutation(self):
        cases = verifier.fixture_cases()
        cases[1][1][verifier.LOGISTIC] = [dict(SKUCode='S', IsTruckFormed=1)]
        schema = CanonicalGenericSchema()
        schema.load = Mock(side_effect=AssertionError('preflight must not mutate'))
        result = verifier.preflight_fixtures(schema, cases)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(any('bit' in item['failure'] for item in result['errors']))
        schema.load.assert_not_called()

    def test_wrong_owner_overwrite_and_active_lease_are_denied(self):
        with self.assertRaises(ValueError):
            verifier.guard_options('temporal-full-001', verifier.OUTPUT_ROOT / 'new.json')
        with patch.object(Path, 'exists', return_value=True):
            with self.assertRaises(FileExistsError):
                verifier.guard_options(verifier.OWNER, verifier.OUTPUT_ROOT / 'new.json')
        with self.assertRaisesRegex(ValueError, 'active lease'):
            verifier.prepare(verifier.OWNER, SimpleNamespace(_lease=object()))

    def test_failure_rolls_back_and_stops_without_retry_or_commit(self):
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
        scripts = {k: SimpleNamespace(source_path=p, source_sha256=s) for k, (p, s) in verifier.projections.SOURCES.items()}
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'proof.json'
            for db in verifier.namespace(verifier.OWNER).values():
                (Path(directory) / (db + '-schema.json')).write_text('{}')
            with patch.object(verifier, 'guard_options', return_value=output), \
                    patch.object(verifier, 'prepare', return_value=(scripts, {})), \
                    patch.object(verifier, 'data_directory', return_value=Path(directory)), \
                    patch.object(verifier, 'scalar_binding', return_value={}), \
                    patch.object(verifier, 'native_context', return_value={}), \
                    patch.object(verifier, 'preflight_fixtures', return_value={'status': 'PASS'}), \
                    patch.object(verifier, 'FixtureSQL', EmptySQL), \
                    patch.object(isolation, 'exclusive_replay', return_value=nullcontext()), \
                    patch.object(isolation, 'connection', return_value=nullcontext(raw)), \
                    patch.object(verifier, 'qualify', return_value={'status': 'FAIL', 'failure': 'UNACCEPTED_FILE_ORDER_GAP'}) as qualify:
                report = verifier.run(verifier.OWNER, output)
            self.assertEqual(report['status'], 'FAIL')
            self.assertEqual(len(report['cases']), 1)
            self.assertEqual(qualify.call_count, 1)
            self.assertIn('UNACCEPTED_FILE_ORDER_GAP', output.read_text())
        raw.rollback.assert_called_once()
        raw.commit.assert_not_called()
        self.assertTrue(raw.raw.autocommit)


if __name__ == '__main__':
    unittest.main()
