from datetime import datetime
import unittest

from mta.domain.complete_daily_scalars import (
    ascii_equal, identifier_sort_key, try_cast_float, round_float_zero,
    float_to_nvarchar, datetime_to_nvarchar, parse_datetime,
)


class ScalarTests(unittest.TestCase):
    def test_identifier_domain_and_sql_padding(self):
        self.assertTrue(ascii_equal('dp010290  ', 'DP010290'))
        self.assertFalse(ascii_equal(None, None))
        self.assertFalse(ascii_equal('X\t', 'X'))
        self.assertEqual(identifier_sort_key('dp010290 '), identifier_sort_key('DP010290'))
        with self.assertRaisesRegex(ValueError, 'UNQUALIFIED'):
            ascii_equal('ß', 'ss')
        with self.assertRaisesRegex(ValueError, 'UNQUALIFIED'):
            identifier_sort_key('SKU\t2')

    def test_qualified_word_order_punctuation_and_positional_secondary_weights(self):
        rows=['A',"'A",'-A',"A'",'A-','A0',"A'0",'A-0','AA','AB',"A'B", "A''B",'A-B','A--B',"AB'",'AB-']
        self.assertEqual(sorted(reversed(rows),key=identifier_sort_key),rows)
        expected=['OWNROOT7','OWN-ROOT7','OWNWH8','OWN-WH8','SUPPLIEDZ9','SUPPLIED-Z9']
        self.assertEqual(sorted(reversed(expected),key=identifier_sort_key),expected)
        self.assertEqual(identifier_sort_key("a-b' "),identifier_sort_key("A-B'"))
        self.assertNotEqual(identifier_sort_key('AB'),identifier_sort_key('A-B'))
        primary=list('!"#$%&()*,./:;?@[\\]^_`{|}~+<=>0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        self.assertEqual(sorted(reversed(primary),key=identifier_sort_key),primary)
        for value in ('',' ','A B','A\tB','\x00','ß','é'):
            with self.assertRaisesRegex(ValueError,'UNQUALIFIED'):identifier_sort_key(value)

    def test_try_cast_does_not_accept_python_extensions(self):
        for value in ('NaN', 'Inf', '1_000', '0x1', '1,000', '1e999', 'invalid'):
            self.assertIsNone(try_cast_float(value))
        self.assertIsNone(try_cast_float(None))
        self.assertEqual(try_cast_float(''), 0.0)
        self.assertEqual(try_cast_float(' \t-.5e2 '), -50.0)

    def test_round_ties_and_large_integral_values(self):
        for value, expected in ((2.5, 3.0), (-2.5, -3.0), (2.49, 2.0),
                                (-0.49, 0.0), (4503599627370495.0, 4503599627370495.0)):
            self.assertEqual(round_float_zero(value), expected)
        self.assertEqual(round_float_zero(-0.0).hex(), '-0x0.0p+0')

    def test_native_float_format(self):
        for value, expected in ((8.0, '8'), (-0.0, '-0'), (12345678.0, '1.23457e+007'),
                                (0.00001234567, '1.23457e-005'), (123456.5, '123457'),
                                (123454.5, '123455'), (999999.5, '1e+006')):
            self.assertEqual(float_to_nvarchar(value), expected)

    def test_native_whitespace_is_asymmetric_and_whitespace_only_is_not_empty(self):
        for whitespace in ('\t', '\r', '\n', '\v', '\f'):
            self.assertIsNone(try_cast_float(whitespace))
            self.assertIsNone(try_cast_float(' ' + whitespace + ' '))
            self.assertEqual(try_cast_float(whitespace + '-.5e2 '), -50.0)
            self.assertIsNone(try_cast_float('1' + whitespace))
        self.assertEqual(try_cast_float('   '), 0.0)
        self.assertIsNone(try_cast_float('\t\r\n'))

    def test_native_underflow_flushes_positive_zero_without_erasing_literal_sign(self):
        for value in ('1e-308', '-1e-308', '1e-320', '-1e-320', '1e-400', '-1e-400',
                      '2.225073858507201e-308'):
            self.assertEqual(try_cast_float(value).hex(), '0x0.0p+0')
        self.assertEqual(try_cast_float('2.2250738585072014e-308').hex(), '0x1.0000000000000p-1022')
        self.assertEqual(try_cast_float('-0').hex(), '-0x0.0p+0')

    def test_native_date_roundtrip_and_seconds_not_invented(self):
        for value in (datetime(2026, 6, 6), datetime(2026, 10, 16, 12, 35),
                      datetime(2026, 12, 31, 23, 59)):
            self.assertEqual(parse_datetime(datetime_to_nvarchar(value)), value)
        self.assertEqual(datetime_to_nvarchar(datetime(2026, 6, 6)), 'Jun  6 2026 12:00AM')
        self.assertNotEqual(parse_datetime(datetime_to_nvarchar(datetime(2026, 6, 6, 0, 0, 1))),
                            datetime(2026, 6, 6, 0, 0, 1))

    def test_datetime_300th_second_storage_and_midnight_carry(self):
        self.assertEqual(parse_datetime('2026-06-06T00:00:00.001'), datetime(2026, 6, 6))
        self.assertEqual(parse_datetime('2026-06-06T00:00:00.002'), datetime(2026, 6, 6, microsecond=3000))
        self.assertEqual(parse_datetime('2026-06-06T00:00:00.005'), datetime(2026, 6, 6, microsecond=7000))
        self.assertEqual(parse_datetime('2026-06-06T23:59:59.999'), datetime(2026, 6, 7))


if __name__ == '__main__':
    unittest.main()
