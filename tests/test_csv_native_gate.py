"""Single CSV cell gate; native context and ordinary input gates stay real."""
from copy import deepcopy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'csv-native-gate-unit-only')
import django
django.setup()

from mta.application import production_csv as intake, production_source_inputs
from mta.application.production_csv_contract import feeds
from mta.application.production_csv_files import load_binding
from mta.application.streamed_input import StreamedInput, JsonInputFile
from mta.runtime import daily_preparation, production_daily as native
from tools.create_daily_csv_example import create
from tests.production_daily_fixture import day_input
from tests.test_production_daily_contract import encoded_day


class CsvNativeGateTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        source = create(Path(__file__).resolve().parents[1] /
            'examples/starter-data/vectorflow-starter-inputs-v1.zip', self.root / 'csv')
        self.binding = load_binding(source / 'binding-template.json')
        self.batch = json.loads((source / '2026-10-18' / 'batch.json').read_bytes())
        self.payloads = {name: (source / '2026-10-18' / name).read_bytes()
                         for name, state in self.batch['feeds'].items() if state == 'PRESENT'}
        self.counter = 0

    def transfer(self, payloads=None, binding=None, batch=None):
        self.counter += 1
        target = self.root / ('native-' + str(self.counter) + '.json')
        value, positions = intake.assemble(batch or self.batch, binding or self.binding,
            self.payloads if payloads is None else payloads, first_day=True,
            output_file=target, _transfer=True)
        return value, positions, target

    def ordinary(self, payloads=None, binding=None, batch=None):
        raw, positions = intake.assemble(batch or self.batch, binding or self.binding,
            self.payloads if payloads is None else payloads, first_day=True)
        return native.decode(raw, hashlib.sha256(raw).hexdigest()), positions

    def change_cell(self, filename, column, value):
        payloads = dict(self.payloads)
        records = list(csv.reader(io.StringIO(payloads[filename].decode('utf-8-sig'), newline='')))
        records[1][records[0].index(column)] = value
        stream = io.StringIO(newline='')
        csv.writer(stream, lineterminator='\r\n').writerows(records)
        payloads[filename] = stream.getvalue().encode('utf-8')
        return payloads

    def test_real_csv_cells_are_typed_once_without_scalar_repeat_or_second_sha_pass(self):
        expected, expected_positions = self.ordinary()
        declarations = feeds(self.binding['intake_schema'])
        cells = sum(len(expected_positions[name]) * len(spec['columns'])
                    for name, spec in declarations.items())
        with patch.object(intake, 'typed_value', wraps=intake.typed_value) as typed, \
                patch.object(intake, 'canonical_parts', wraps=intake.canonical_parts) as encoded, \
                patch.object(native, 'scalar', side_effect=AssertionError('Cell checked twice')), \
                patch.object(native, '_typed_rows', side_effect=AssertionError('Daily cells checked twice')), \
                patch.object(native, '_decode_value', wraps=native._decode_value) as context, \
                patch.object(production_source_inputs, 'validate', wraps=production_source_inputs.validate) as sources, \
                patch.object(StreamedInput, '_checked', side_effect=AssertionError('Owned CSV rehashed')):
            carrier, positions, target = self.transfer()
            self.assertNotIsInstance(carrier, daily_preparation.PreparedDaily)
            self.assertEqual(context.call_count, 0)
            self.assertTrue(target.exists())
            prepared = daily_preparation.prepare(carrier, carrier.sha256)
            self.assertIs(daily_preparation.prepare(prepared, prepared.sha256), prepared)
            self.assertIs(native.decode(prepared, prepared.sha256), prepared.checked(prepared.sha256))
            self.assertEqual(prepared.checked(prepared.sha256), expected)
            self.assertEqual(positions, expected_positions)
            self.assertEqual(typed.call_count, cells)
            self.assertEqual(encoded.call_count, 1)
            self.assertEqual(context.call_count, 1)
            self.assertEqual(sources.call_count, 1)
            self.assertIsNone(carrier._value)
            self.assertIsNone(carrier._csv_native_rows._value)
        self.assertEqual(prepared.sha256, hashlib.sha256(target.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, 'already transferred'):
            daily_preparation.prepare(carrier, carrier.sha256)

    def test_native_missing_predicates_keep_the_same_rejected_values(self):
        for column, cell, reason in (
                ('SKUCode', 'é', 'bounded ASCII'),
                ('SKUCode', 'S\x00X', 'Initialization field type differs'),
                ('Stock', str(2**31), 'Invalid native integer'),
                ('ReportDate', '\\N', 'NOT NULL|required column'),
                ('ReportDate', '2026-10-19', 'declared business date')):
            with self.subTest(column=column, cell=repr(cell)):
                payloads = self.change_cell('DailyDataRaw.csv', column, cell)
                with self.assertRaisesRegex(ValueError, reason):
                    self.ordinary(payloads)
                try:
                    carrier, _, _ = self.transfer(payloads)
                except ValueError as error:
                    self.assertRegex(str(error), reason)
                else:
                    with self.assertRaisesRegex(ValueError, reason):
                        daily_preparation.prepare(carrier, carrier.sha256)

    def test_csv_width_header_and_number_diagnostics_remain_identical(self):
        bad_number = self.change_cell('DailyDataRaw.csv', 'Stock', '1.5')
        bad_header = dict(self.payloads)
        bad_header['DailyDataRaw.csv'] = b'wrong,header\n1,2\n'
        bad_width = dict(self.payloads)
        header = self.payloads['DailyDataRaw.csv'].splitlines()[0]
        bad_width['DailyDataRaw.csv'] = header + b'\nextra,row\n'
        for payloads in (bad_number, bad_header, bad_width):
            with self.subTest(payload=payloads['DailyDataRaw.csv'][:80]):
                with self.assertRaises(intake.CsvIntakeError) as ordinary:
                    self.ordinary(payloads)
                with self.assertRaises(intake.CsvIntakeError) as owned:
                    self.transfer(payloads)
                self.assertEqual(list(owned.exception.issues), list(ordinary.exception.issues))

    def test_context_failure_occurs_at_prepare_and_keeps_archive_and_unconsumed_input(self):
        binding = deepcopy(self.binding)
        binding['report_policy']['bor_history_horizon'] = -1
        with self.assertRaisesRegex(ValueError, 'history horizons'):
            self.ordinary(binding=binding)
        carrier, positions, target = self.transfer(binding=binding)
        self.assertTrue(target.exists())
        self.assertTrue(positions['DailyDataRaw.csv'])
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), carrier.sha256)
        with self.assertRaisesRegex(ValueError, 'history horizons'):
            daily_preparation.prepare(carrier, carrier.sha256)
        self.assertIsNotNone(carrier._value)
        # The ordinary fallback still sees the same exact StreamedInput class
        # and can reconstruct diagnostics without borrowing a successful gate.
        self.assertIs(type(carrier), StreamedInput)
        self.assertEqual(carrier.snapshot(carrier.sha256), json.loads(target.read_bytes()))

    def test_binding_and_snapshot_mutation_cannot_change_owned_parser_values(self):
        expected, _ = self.ordinary()
        carrier, _, _ = self.transfer()
        self.binding['consumer_opening']['requests'].append({'not': 'a request'})
        self.binding['report_policy']['bor_history_horizon'] = -1
        snapshot = carrier.snapshot(carrier.sha256)
        snapshot['day']['raw_daily'][0]['Stock'] = 'not an integer'
        prepared = daily_preparation.prepare(carrier, carrier.sha256)
        self.assertEqual(prepared.checked(prepared.sha256), expected)

    def test_private_evidence_cannot_be_forged_borrowed_or_relabelled(self):
        carrier, _, _ = self.transfer()
        copied = StreamedInput.take(carrier.snapshot(carrier.sha256), carrier.sha256)
        copied._csv_native_rows = carrier._csv_native_rows
        with self.assertRaisesRegex(ValueError, 'owner|identity'):
            daily_preparation.prepare(copied, copied.sha256)
        with self.assertRaisesRegex(ValueError, 'identity'):
            daily_preparation.prepare(carrier, 'f' * 64)
        carrier.sha256 = 'e' * 64
        with self.assertRaisesRegex(ValueError, 'identity'):
            daily_preparation.prepare(carrier, carrier.sha256)
        copied._csv_native_rows = SimpleNamespace(validated=True)
        with self.assertRaisesRegex(ValueError, 'requires its parser'):
            daily_preparation.prepare(copied, copied.sha256)
        with self.assertRaisesRegex(ValueError, 'requires its parser'):
            intake._CsvNativeRows(None, carrier, [])

    def test_bytes_files_and_ordinary_streams_still_use_full_native_gate(self):
        value = day_input('2037-04-10', root=True)
        raw, checksum = encoded_day(value)
        path = self.root / 'ordinary.json'
        path.write_bytes(raw)
        for source in (raw, JsonInputFile(path), StreamedInput(value, checksum)):
            # StreamedInput hashes canonical transport bytes; encoded_day's
            # JSON representation is deliberately a separate byte interface.
            if isinstance(source, StreamedInput):
                from mta.serialization import canonical_parts
                source.sha256 = hashlib.sha256(b''.join(canonical_parts(value, ensure_ascii=False))).hexdigest()
            expected_sha = source.sha256 if isinstance(source, StreamedInput) else checksum
            with self.subTest(source=type(source).__name__), \
                    patch.object(native, 'scalar', wraps=native.scalar) as scalars, \
                    patch.object(native, '_typed_rows', wraps=native._typed_rows) as daily, \
                    patch.object(native, 'decode_value', wraps=native.decode_value) as decode:
                prepared = daily_preparation.prepare(source, expected_sha)
                self.assertEqual(prepared.checked(expected_sha), value)
                self.assertEqual(decode.call_count, 1)
                self.assertGreater(scalars.call_count, 0)
                self.assertEqual(daily.call_count, 1)

    def test_requirement_stock_date_constraint_is_not_inferred_from_csv_types(self):
        from mta.application.native_daily_contract import ACTIVE_STOCK_SCHEMA
        binding, batch, payloads = deepcopy(self.binding), deepcopy(self.batch), dict(self.payloads)
        binding['intake_schema'] = ACTIVE_STOCK_SCHEMA
        filename = 'AdditionalDataStockForReqCalc.csv'
        batch['feeds'][filename] = 'PRESENT'
        payloads[filename] = b'SKUCode,WhCode,StockForReqCalc,ReportDate\nS,W,-7,2026-10-17\n'
        with self.assertRaisesRegex(ValueError, 'Requirement-stock date differs'):
            self.ordinary(payloads, binding, batch)
        carrier, _, _ = self.transfer(payloads, binding, batch)
        with self.assertRaisesRegex(ValueError, 'Requirement-stock date differs'):
            daily_preparation.prepare(carrier, carrier.sha256)

    def test_all_intake_modes_keep_master_supplier_stock_values_without_scalar_rechecks(self):
        from mta.application.native_daily_contract import SCHEMA, FEED_SCHEMA, STOCK_FEED_SCHEMA, ACTIVE_STOCK_SCHEMA
        from mta.application.operational_inputs import encode_csv
        from mta.application import requirement_stock
        from tests.test_production_csv_diagnostics import master_payload
        master = master_payload()['raw_master']
        master[0].update(Weight='1.230', Volume=None)
        supplied = {'MasterDataRaw.csv': master,
            'SOBDataRaw.csv': [dict(SKUCode='CSV-1', WHCode='CSV-W', SupplierCode='CSV-P',
                SupplierDescription='Parent', SOB=37.125)],
            'MOQDataRaw1.csv': [], 'MOQDataRaw2.csv': [],
            'AdditionalDataStockForReqCalc.csv': [dict(SKUCode='CSV-1', WhCode='CSV-W',
                StockForReqCalc=value, ReportDate=self.batch['business_date']) for value in (None, -7, -7)]}
        for mode in (SCHEMA, FEED_SCHEMA, STOCK_FEED_SCHEMA, ACTIVE_STOCK_SCHEMA):
            with self.subTest(mode=mode):
                binding, batch, payloads = deepcopy(self.binding), deepcopy(self.batch), dict(self.payloads)
                binding['intake_schema'] = mode
                for filename, spec in feeds(mode).items():
                    if filename not in batch['feeds']:
                        batch['feeds'][filename] = 'PRESENT'
                        payloads[filename] = encode_csv(spec['columns'], supplied[filename])
                expected, _ = self.ordinary(payloads, binding, batch)
                with patch.object(native, 'scalar', side_effect=AssertionError('CSV scalar repeated')), \
                        patch.object(native, '_typed_rows', side_effect=AssertionError('CSV daily types repeated')), \
                        patch.object(requirement_stock, 'validate', side_effect=AssertionError('CSV stock cells repeated')):
                    carrier, _, _ = self.transfer(payloads, binding, batch)
                    prepared = daily_preparation.prepare(carrier, carrier.sha256)
                self.assertEqual(prepared.checked(prepared.sha256), expected)

    def test_nonempty_source_cells_are_checked_once_and_source_context_is_still_validated(self):
        from mta.application.operational_inputs import encode_csv
        from mta.application import daily_transit
        payloads = dict(self.payloads)
        columns = feeds(self.binding['intake_schema'])
        shipment = dict.fromkeys(daily_transit.RAW_FIELDS)
        shipment.update(SKUCode='S', ToLocationCode='W', FromLocationCode='P',
            InTransitQty=-7, CreationDate='2026-10-17', ReportDate=self.batch['business_date'])
        directory = [dict(TransporterCode='TR', TransporterName='雪', TransporterContact=None)]
        payloads['InTransitRaw.csv'] = encode_csv(columns['InTransitRaw.csv']['columns'], [shipment, shipment])
        payloads['Transporters.csv'] = encode_csv(columns['Transporters.csv']['columns'], directory)
        expected, _ = self.ordinary(payloads)
        with patch.object(daily_transit, '_text', side_effect=AssertionError('Source text checked twice')), \
                patch.object(daily_transit, '_integer', side_effect=AssertionError('Source integer checked twice')), \
                patch.object(production_source_inputs, 'validate', wraps=production_source_inputs.validate) as context:
            carrier, _, _ = self.transfer(payloads)
            prepared = daily_preparation.prepare(carrier, carrier.sha256)
        self.assertEqual(prepared.checked(prepared.sha256), expected)
        self.assertEqual(context.call_count, 1)
        self.assertEqual(context.call_args.args[0]['shipments']['rows'], [])
        self.assertEqual(prepared.checked(prepared.sha256)['producer_sources']['shipments']['rows'],
                         [shipment, shipment])
        payloads['Transporters.csv'] = encode_csv(columns['Transporters.csv']['columns'],
            [dict(directory[0], TransporterName='x' * 126)])
        with self.assertRaisesRegex(ValueError, 'TransporterName exceeds native width'):
            self.ordinary(payloads)
        with self.assertRaisesRegex(ValueError, 'TransporterName exceeds native width'):
            self.transfer(payloads)

    def test_accepted_restoration_does_not_reenter_either_native_decoder(self):
        value = day_input('2037-04-10', root=True)
        _, checksum = encoded_day(value)
        admission = {'fixture': 'already-admitted'}
        prepared = daily_preparation.restored(value, checksum, admission)
        with patch.object(native, 'decode_value', side_effect=AssertionError('Restored input decoded')), \
                patch.object(native, '_decode_csv_value', side_effect=AssertionError('Restored CSV decoded')):
            self.assertIs(daily_preparation.prepare(prepared, checksum), prepared)
            self.assertIs(native.decode(prepared, checksum), value)
        self.assertIs(prepared.admission, admission)
