from datetime import date, datetime
from decimal import Decimal
import unittest

from mta.application.operational_inputs import encode_csv, decode_csv, physical_files, typed_value


def column(name, kind, parameters=None, nullable=True):
    return dict(name=name, type=kind, parameters=parameters, nullable=nullable)


class PhysicalInputsTests(unittest.TestCase):
    def setUp(self):
        self.columns = [column('Text', 'nvarchar', '100'), column('Qty', 'int'),
                        column('Ratio', 'decimal', '8,3'), column('Day', 'date'),
                        column('Stamp', 'datetime'), column('Flag', 'bit')]

    def test_exact_bytes_and_typed_duplicate_roundtrip(self):
        row = dict(Text='a,"b"\r\nc', Qty=-3, Ratio=Decimal('1.230'),
                   Day=date(2026, 6, 6), Stamp=datetime(2026, 6, 6, 0, 0), Flag=True)
        empty = dict(Text='', Qty=None, Ratio=None, Day=None, Stamp=None, Flag=False)
        payload = encode_csv(self.columns, [row, empty, row])
        self.assertEqual(payload, b'Text,Qty,Ratio,Day,Stamp,Flag\r\n'
                         b'"a,""b""\r\nc",-3,1.230,2026-06-06,2026-06-06T00:00:00,1\r\n'
                         b',\\N,\\N,\\N,\\N,0\r\n'
                         b'"a,""b""\r\nc",-3,1.230,2026-06-06,2026-06-06T00:00:00,1\r\n')
        self.assertEqual(decode_csv(self.columns, payload), [row, empty, row])
        self.assertEqual(decode_csv(self.columns, payload)[0]['Ratio'].as_tuple().exponent, -3)

    def test_empty_population_has_exact_header(self):
        self.assertEqual(encode_csv(self.columns, []), b'Text,Qty,Ratio,Day,Stamp,Flag\r\n')
        self.assertEqual(decode_csv(self.columns, encode_csv(self.columns, [])), [])

    def test_reject_null_collision_and_missing_columns(self):
        with self.assertRaises(ValueError):
            encode_csv([self.columns[0]], [{'Text': '\\N'}])
        with self.assertRaises(ValueError):
            encode_csv(self.columns, [{'Text': 'x'}])
        with self.assertRaises(ValueError):
            typed_value(None, column('required', 'int', nullable=False))

    def test_no_rounding_or_integer_coercion(self):
        for value in (1.5, True, '1.0', '01', 2**31):
            with self.subTest(value=value), self.assertRaises(ValueError):
                typed_value(value, column('Qty', 'int'))
        for value in ('1.2345', '100000.000', 'NaN', 1.23):
            with self.subTest(value=value), self.assertRaises(ValueError):
                typed_value(value, column('Ratio', 'decimal', '8,3'))

    def test_utf16_native_width_and_timestamp_zone(self):
        with self.assertRaises(ValueError):
            typed_value('😀', column('Text', 'nvarchar', '1'))
        with self.assertRaises(ValueError):
            typed_value('2026-06-06T00:00:00+05:30', column('Stamp', 'datetime'))

    def test_reject_noncanonical_bytes(self):
        for payload in (b'Text\nx\n', b'\xef\xbb\xbfText\r\nx\r\n', b'Text\r\n"x"\r\n',
                        b'Text\r\nx,y\r\n'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                decode_csv([self.columns[0]], payload)

    def test_all_five_sources_must_be_explicit(self):
        names = ['MasterDataRaw', 'DailyDataRaw', 'SOBDataRaw', 'MOQDataRaw1']
        schema = {'tables': {'Importer/' + name: [self.columns[0]] for name in names}}
        populations = {name: [] for name in [*names, 'InTransitRaw']}
        files = physical_files(schema, populations, [self.columns[0]])
        self.assertEqual(list(files), [name + '.csv' for name in [*names, 'InTransitRaw']])
        del populations['InTransitRaw']
        with self.assertRaises(ValueError):
            physical_files(schema, populations, [self.columns[0]])


if __name__ == '__main__':
    unittest.main()
