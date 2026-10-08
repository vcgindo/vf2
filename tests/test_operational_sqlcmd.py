from datetime import datetime
from decimal import Decimal
import unittest

from mta.application.operational_sqlcmd import (
    resultset_bytes, converted_text, no_norm_parent_bytes, upload_log_bytes,
)


class OperationalSqlcmdTests(unittest.TestCase):
    def test_native_trimmed_scalar_probe(self):
        rows = [dict(fields=[''] * 8,
            types=['nvarchar(50)', 'nvarchar(50)', 'int', 'decimal(10,3)', 'date', 'datetime', 'bit', 'nvarchar(20)'],
            rows=[['Text ', None, 3, Decimal('1.230'), '2026-06-06',
                   datetime(2026, 6, 6, 13, 4, 5, 123000), True, '1.25']])]
        self.assertEqual(resultset_bytes(rows),
            b'Text ,NULL,3,1.230,2026-06-06,2026-06-06 13:04:05.123,1,1.25\r\n')

    def test_decimal_display_differs_from_sql_conversion(self):
        rows = [dict(fields=[''] * 3, types=['decimal(10,3)'] * 3,
                     rows=[[Decimal('.120'), Decimal('-.120'), Decimal('.000')]])]
        self.assertEqual(resultset_bytes(rows), b'.120,-.120,.000\r\n')
        self.assertEqual(converted_text(Decimal('.120'), 'decimal'), '0.120')
        self.assertEqual(converted_text(datetime(2026, 6, 6, 13, 4, 5, 123000), 'datetime'),
                         'Jun  6 2026  1:04PM')

    def test_native_headers_with_W_use_header_width(self):
        self.assertEqual(no_norm_parent_bytes([dict(SKUCode='S', WhCode='W', Norm=12, ParentWhCode='P')]),
            b'SKUCode,WhCode,Norm,ParentWhCode\r\n-------,------,----,------------\r\nS,W,12,P\r\n')
        self.assertEqual(no_norm_parent_bytes([]), b'')

    def test_long_header_is_not_256_display_truncated(self):
        report = dict(header_result_set=((dict(value='X' * 300, sql_type='nvarchar(4000)'),),),
                      data_result_set=())
        self.assertEqual(upload_log_bytes(report), b'X' * 300 + b'\r\n')

    def test_preserve_spaces_delimiters_newlines_and_native_encoding(self):
        rows = [dict(fields=[''] * 4, types=['nvarchar(50)'] * 4,
                     rows=[['  both  ', 'a,b', 'a\r\nb', 'é']])]
        self.assertEqual(resultset_bytes(rows), b'  both  ,a,b,a\r\nb,\xe9\r\n')
        rows[0]['rows'][0][0] = '😀'
        with self.assertRaises(ValueError):
            resultset_bytes(rows)
