"""The BTR-only COPY contract; PostgreSQL value/guard proof is separate."""
from decimal import Decimal
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from django.db.models import Value
from mta.presentation import btr_copy
from mta.runtime.models import BtrPresentationRow


class BtrCopyTests(unittest.TestCase):
    def row(self, **values):
        return BtrPresentationRow(generation_id=uuid4(), branch='tech', a_ordinal=0,
                                 available_prefix=[0] *91, empty_prefix=[0] *91, **values)

    def test_requires_owning_transaction_and_bounded_fresh_rows(self):
        with patch.object(btr_copy.connection, 'in_atomic_block', False), \
                patch.object(btr_copy.connection, 'cursor') as cursor:
            with self.assertRaisesRegex(ValueError, 'owning transaction'):
                btr_copy.write_batch([self.row()])
            cursor.assert_not_called()
        with patch.object(btr_copy.connection, 'in_atomic_block', True), \
                patch.object(btr_copy.connection, 'cursor') as cursor:
            for rows in ([], [self.row()] *65, [SimpleNamespace(pk=None)], [self.row(id=1)]):
                with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                    btr_copy.write_batch(rows)
            cursor.assert_not_called()

    def test_fields_use_django_preparation_and_copy_row_protocol(self):
        row = self.row(filter_e_norm=Decimal('1.23456789015'),
                       display_skudescription_text="O'Brien\tline\n\\N Ω中",
                       nonfinite_fields=['D1'], nonfinite_tokens=[None])
        cursor = MagicMock()
        writer = cursor.copy.return_value.__enter__.return_value
        with patch.object(btr_copy.connection, 'in_atomic_block', True), \
                patch.object(btr_copy.connection, 'cursor') as opened:
            opened.return_value.__enter__.return_value = cursor
            self.assertIsNone(btr_copy.write_batch([row]))
        sql = cursor.copy.call_args.args[0]
        self.assertTrue(sql.startswith('COPY "mta"."fresh_mta_btrpresentationrow" ('))
        self.assertTrue(sql.endswith(' FROM STDIN'))
        self.assertNotIn('"id",', sql)
        stored = writer.write_row.call_args.args[0]
        fields = [field.attname for field in btr_copy._FIELDS]
        self.assertEqual(len(stored), len(fields))
        for key in ('generation_id', 'filter_e_norm', 'display_skudescription_text',
                    'available_prefix', 'empty_prefix', 'nonfinite_fields', 'nonfinite_tokens'):
            self.assertEqual(stored[fields.index(key)], getattr(row, key))
        self.assertIsNone(row.pk)

    def test_expression_is_rejected_without_fallback_or_literal_conversion(self):
        cursor = MagicMock()
        with patch.object(btr_copy.connection, 'in_atomic_block', True), \
                patch.object(btr_copy.connection, 'cursor') as opened:
            opened.return_value.__enter__.return_value = cursor
            with self.assertRaisesRegex(ValueError, 'SQL expressions'):
                btr_copy.write_batch([self.row(filter_e_norm=Value(1))])
        cursor.copy.return_value.__enter__.return_value.write_row.assert_not_called()


if __name__ == '__main__':
    unittest.main()
