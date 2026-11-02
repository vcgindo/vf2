from dataclasses import FrozenInstanceError
from decimal import Decimal
import math
import unittest

from mta.runtime.execution_setting_values import (
    SettingCell, decode_scalar, encode_scalar, rows_digest, set_path,
)


class ScalarCodecTests(unittest.TestCase):
    def test_exact_round_trips(self):
        values = [None, False, True, 0, 1, -(2**200), 2**200, 1.0, -0.0,
                  1.25e-100, Decimal('1.00'), Decimal('-0.00'), Decimal('1E+20'),
                  Decimal('123456789012345678901234567890.12345678901234567890'),
                  '', ' 0 ', 'SKU/日本語/🧭', '__import__("os")']
        for value in values:
            with self.subTest(value=value):
                decoded = decode_scalar(*encode_scalar(value))
                self.assertIs(type(decoded), type(value))
                self.assertEqual(decoded, value)
                if type(value) is Decimal:
                    self.assertEqual(decoded.as_tuple(), value.as_tuple())
                if type(value) is float:
                    self.assertEqual(decoded.hex(), value.hex())

    def test_distinct_types_have_distinct_encodings(self):
        values = [None, '', False, 0, 0.0, -0.0, True, 1, 1.0, Decimal('1.00'), '1']
        self.assertEqual(len({encode_scalar(value) for value in values}), len(values))
        self.assertEqual(encode_scalar(Decimal('1.00')), ('decimal', '1.00'))

    def test_rejects_unsupported_payloads_and_nonfinite_values(self):
        for value in ([], {}, (), object(), b'1'):
            with self.subTest(value=value), self.assertRaises(TypeError):
                encode_scalar(value)
        for value in (math.inf, -math.inf, math.nan, Decimal('Infinity'), Decimal('NaN'), Decimal('sNaN')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                encode_scalar(value)

    def test_decode_rejects_noncanonical_or_malformed_encodings(self):
        invalid = [('null', ''), ('text', None), ('text', 1), (None, 'x'),
                   ('unknown', '1'), ('absent', None), ('bool', '1'), ('bool', 'True'),
                   ('int', '01'), ('int', '+1'), ('int', ' 1'), ('int', '-0'), ('int', '١'),
                   ('int', '1.0'), ('float', '1'), ('float', '1.00'), ('float', ' 1.0'),
                   ('float', '-0'), ('float', 'nan'), ('float', 'inf'), ('float', '1e999'),
                   ('decimal', '01.00'), ('decimal', '1e2'), ('decimal', '+1'),
                   ('decimal', ' 1'), ('decimal', 'NaN'), ('decimal', 'Infinity'),
                   ('decimal', 'garbage')]
        for kind, text in invalid:
            with self.subTest(kind=kind, text=text), self.assertRaises(ValueError):
                decode_scalar(kind, text)


class SettingCellTests(unittest.TestCase):
    def cell(self, value=1):
        return SettingCell.from_value('/delivery/batch', 'DBM', 'AutoDBMActive', 0, value)

    def test_frozen_strict_cell_round_trip(self):
        cell = self.cell(False)
        self.assertIs(cell.value(), False)
        self.assertEqual(SettingCell.from_dict(cell.as_dict()), cell)
        with self.assertRaises(FrozenInstanceError):
            cell.ordinal = 2
        changed = cell.as_dict()
        changed['value_text'] = 'true'
        self.assertIs(cell.value(), False)

    def test_null_absent_and_empty_are_separate(self):
        null = self.cell(None)
        empty = self.cell('')
        absent = SettingCell('/delivery', 'DBM', 'missing', 0, 'absent', None, 'ABSENT')
        self.assertEqual(null.value_state, 'NULL')
        self.assertIsNone(null.value())
        self.assertEqual(empty.value(), '')
        with self.assertRaisesRegex(ValueError, 'ABSENT'):
            absent.value()
        self.assertEqual(SettingCell.from_dict(absent.as_dict()), absent)

    def test_rejects_bad_fields_metadata_and_state_combinations(self):
        original = self.cell().as_dict()
        malformed = [dict(original, extra=1), {k: v for k, v in original.items() if k != 'value_state'},
                     dict(original, ordinal=True), dict(original, ordinal=-1),
                     dict(original, module=1), dict(original, path=[]), dict(original, parameter=None),
                     dict(original, value_kind=[]), dict(original, value_text=1),
                     dict(original, value_state='other'), dict(original, value_state='NULL'),
                     dict(original, value_state='ABSENT'), dict(original, value_kind='null', value_text=None),
                     dict(original, value_kind='int', value_text='01')]
        for row in malformed:
            with self.subTest(row=row), self.assertRaises(ValueError):
                SettingCell.from_dict(row)
        with self.assertRaises(ValueError):
            SettingCell.from_dict([])

    def test_ordered_digest_retains_scalar_types_duplicates_and_order(self):
        cells = [self.cell(False), self.cell(0), self.cell(1.0), self.cell(Decimal('1.00'))]
        self.assertEqual(rows_digest(cells), rows_digest([cell.as_dict() for cell in cells]))
        self.assertEqual(rows_digest(cells), rows_digest(iter(cells)))
        self.assertNotEqual(rows_digest(cells), rows_digest(reversed(cells)))
        self.assertNotEqual(rows_digest(cells), rows_digest(cells + cells[:1]))
        self.assertEqual(len({rows_digest([cell]) for cell in cells}), len(cells))


class SetPathTests(unittest.TestCase):
    def test_copy_on_write_shares_unrelated_populations(self):
        large = tuple(range(100000))
        old = {'profile': {'batch': {'AutoDBMActive': 0}, 'masters': large}, 'history': large}
        new = set_path(old, ('profile', 'batch', 'AutoDBMActive'), 1)
        self.assertEqual(old['profile']['batch']['AutoDBMActive'], 0)
        self.assertEqual(new['profile']['batch']['AutoDBMActive'], 1)
        self.assertIsNot(new, old)
        self.assertIsNot(new['profile'], old['profile'])
        self.assertIsNot(new['profile']['batch'], old['profile']['batch'])
        self.assertIs(new['profile']['masters'], large)
        self.assertIs(new['history'], large)

    def test_rejects_untrusted_or_missing_dictionary_paths(self):
        root = {'rows': [{'x': 1}], 'scalar': 1}
        for path in ((), ['scalar'], ('missing',), ('rows', '0', 'x'), ('scalar', 'x'), (0,)):
            with self.subTest(path=path), self.assertRaises(ValueError):
                set_path(root, path, 2)
        self.assertEqual(root, {'rows': [{'x': 1}], 'scalar': 1})


if __name__ == '__main__':
    unittest.main()
