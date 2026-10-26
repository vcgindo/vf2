"""Wire/typed image adapter; actual PostgreSQL read proof is recorded separately."""
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
import unittest
from unittest.mock import patch

from mta.runtime import runtime_report_sources as source
from mta.row_sequences import RecordRows
from mta.serialization import digest

REGISTRY = {'BPR/Example': [('SKUCode', 'nvarchar'), ('Qty', 'int'),
    ('Amount', 'decimal'), ('Day', 'date'), ('Stamp', 'datetime'), ('Flag', 'bit')]}
FIELDS = tuple(field for field, kind in REGISTRY['BPR/Example'])


def metadata(count=1):
    return dict(table='BPR/Example', count=count, image='phase/BPR/example',
        fields=[[field, field, 'str' if field in ('SKUCode', 'Amount', 'Day', 'Stamp')
                 else 'bool' if field == 'Flag' else 'int'] for field in FIELDS])


def row():
    return dict(SKUCode='s ', Qty=3, Amount='2.5000', Day='2026-10-25',
                Stamp='2026-10-25T12:00:00', Flag=True)


class RuntimeReportSourcesTests(unittest.TestCase):
    def test_verified_reader_then_lossless_typed_decode_without_mutation(self):
        original = [row(), row()]; before = digest(original); info = metadata(2)
        with patch.object(source.relational_state, 'load_image', return_value=original) as reader:
            result = source.image_rows('run', info, expected_table='BPR/Example', fields=FIELDS, registry=REGISTRY)
            reader.assert_called_once_with('run', info, table_registry=REGISTRY)
            expected = dict(SKUCode='s ', Qty=3, Amount=Decimal('2.5000'), Day=date(2026, 10, 25),
                            Stamp=datetime(2026, 10, 25, 12), Flag=True)
            self.assertEqual(list(result), [expected, expected])
            self.assertEqual(result[0]['Amount'].as_tuple().exponent, -4)
            self.assertEqual(digest(original), before)
            self.assertEqual(list(result), [expected, expected])

    def test_column_case_uses_actual_physical_identifier_without_normalizing_values(self):
        info = metadata(); info['fields'][0][0] = 'skuCode'
        original = row(); original['skuCode'] = original.pop('SKUCode')
        with patch.object(source.relational_state, 'load_image', return_value=[original]):
            rows = source.image_rows('run', info, expected_table='BPR/Example',
                                     fields=('skucode', 'AMOUNT'), registry=REGISTRY)
            self.assertEqual(list(rows), [dict(skucode='s ', AMOUNT=Decimal('2.5000'))])

    def test_existing_empty_image_uses_declared_schema_but_unknown_field_or_missing_image_denies(self):
        info = dict(metadata(0), fields=[])
        with patch.object(source.relational_state, 'load_image', return_value=[]) as reader:
            self.assertEqual(list(source.image_rows('run', info, expected_table='BPR/Example',
                             fields=FIELDS, registry=REGISTRY)), [])
            reader.reset_mock()
            for changed, fields in ((None, FIELDS), (info, ('invented',)),
                    (dict(info, table='different-owner'), FIELDS), (dict(info, count=True), FIELDS),
                    (dict(info, fields=[['SKUCode', 'SKUCode', 'str']]), FIELDS)):
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    source.image_rows('run', changed, expected_table='BPR/Example',
                                      fields=fields, registry=REGISTRY)
            reader.assert_not_called()

    def test_checksum_failure_and_wrong_row_count_are_not_hidden_by_projection(self):
        with patch.object(source.relational_state, 'load_image', side_effect=ValueError('checksum failed')):
            with self.assertRaisesRegex(ValueError, 'checksum failed'):
                source.image_rows('run', metadata(), expected_table='BPR/Example', fields=FIELDS, registry=REGISTRY)
        with patch.object(source.relational_state, 'load_image', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'row count'):
                source.image_rows('run', metadata(), expected_table='BPR/Example', fields=FIELDS, registry=REGISTRY)

    def test_full_source_metadata_and_required_fields_are_checked_before_read(self):
        variants = []
        info = metadata(); info['fields'].pop(); variants.append(info)
        info = metadata(); info['fields'].append(info['fields'][0]); variants.append(info)
        info = metadata(); info['fields'][0][1] = 'DifferentPhysical'; variants.append(info)
        with patch.object(source.relational_state, 'load_image') as reader:
            for info in variants:
                with self.assertRaises(ValueError):
                    source.image_rows('run', info, expected_table='BPR/Example', fields=FIELDS, registry=REGISTRY)
            with self.assertRaises(ValueError):
                source.image_rows('run', metadata(), expected_table='BPR/Example',
                                  fields=('Qty', 'qty'), registry=REGISTRY)
            reader.assert_not_called()

    def test_large_reiterable_source_is_not_copied_to_a_list(self):
        seen = []
        def rows():
            for ordinal in range(10001):
                seen.append(ordinal)
                yield row()
        with patch.object(source.relational_state, 'load_image', return_value=RecordRows(10001, rows)):
            result = source.image_rows('run', metadata(10001), expected_table='BPR/Example',
                                       fields=FIELDS, registry=REGISTRY)
            self.assertEqual(seen, [])
            self.assertEqual(next(iter(result))['Qty'], 3)
            self.assertEqual(seen, [0])

    def test_null_reserved_text_and_exact_scalar_domains(self):
        for kind in ('nvarchar', 'int', 'decimal', 'date', 'datetime', 'bit'):
            self.assertIsNone(source.scalar(None, kind))
        self.assertEqual(source.scalar('\\N', 'nvarchar'), '\\N')
        self.assertEqual(source.scalar('1', 'bit'), True)
        self.assertEqual(source.scalar('2026-10-25', 'date'), date(2026, 10, 25))
        for value, kind in ((True, 'int'), (True, 'decimal'), (1.1, 'decimal'),
                ('NaN', 'decimal'), ('Infinity', 'decimal'), ('1.5', 'int'),
                (2**31, 'int'), (2, 'bit'), (3, 'nvarchar'),
                (datetime.now(timezone.utc), 'datetime'), (None, 'invented')):
            with self.subTest(value=value, kind=kind), self.assertRaises(ValueError):
                source.scalar(value, kind)

    def test_missing_row_cell_cannot_be_supplied_by_a_null_default(self):
        original = row(); del original['Amount']
        with patch.object(source.relational_state, 'load_image', return_value=[original]):
            result = source.image_rows('run', metadata(), expected_table='BPR/Example', fields=FIELDS, registry=REGISTRY)
            with self.assertRaisesRegex(ValueError, 'field missing'):
                list(result)
