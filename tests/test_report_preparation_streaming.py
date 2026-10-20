"""Bounded report preparation retains the established wire and drift contracts."""
import hashlib
import json
import os
import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import bor_sources, boroa_sources, daily_bor_prepared as bor
from mta.presentation import planning_summary_daily as summary
from mta.presentation.context import PublicationUnavailable
from mta.row_sequences import RecordRows
from mta.serialization import digest


def legacy_digest(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class StreamOnlyQuery:
    """Fail if a caller asks the queryset for a population-sized Python copy."""
    def __init__(self, factory):
        self.factory = factory

    def __iter__(self):
        raise AssertionError('queryset must use bounded iterator')

    def order_by(self, *args):
        return self

    def values(self, *args):
        return self

    def values_list(self, *args):
        return self

    def iterator(self, *, chunk_size):
        assert chunk_size <= 1000
        return self.factory()


class ReportPreparationStreamingTests(unittest.TestCase):
    def test_capture_checksum_matches_original_unsorted_unicode_json(self):
        rows = [dict(z='é漢字\n"\\', a=None, number=-0.0),
                dict(z='é漢字\n"\\', a='', number=1e100)]
        spooled = RecordRows.from_rows(rows)
        self.assertEqual(bor_sources.capture_digest(spooled), legacy_digest(rows))
        self.assertEqual(bor_sources.capture_digest([]), legacy_digest([]))
        self.assertNotEqual(bor_sources.capture_digest(spooled), digest(rows))
        with self.assertRaises(ValueError):
            bor_sources.capture_digest([{'bad': float('nan')}])

    def test_source_capture_spools_duplicate_rows_and_preserves_scalar_conversions(self):
        stamp = datetime(2026, 6, 17, 9, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        remark = dict(SKUCode='é', WhCode='L', Remark=None, Username='',
                      RemarkDate=stamp, SupplierCode='S')
        sob = dict(SKUCode='é', WHCode='L', SupplierCode='S', SOB=Decimal('0.125'))
        source_rows = {'SOBData': [sob, sob], 'BORReport_RemarkDetails': [remark, remark]}
        with patch.dict(bor_sources.MODELS, {name: None for name in source_rows}, clear=True), \
             patch.object(bor, '_source_rows', side_effect=lambda _r, _l, name, _f: source_rows[name]):
            captures, expected = bor._source_expected(None, 'bor', bor_sources,
                bor_sources.FIELDS, lambda: 'recipe')
        wire_remark = dict(remark, RemarkDate='2026-06-17T04:00:00')
        wire_sob = dict(sob, SOB=0.125)
        for name, rows in (('SOBData', [wire_sob, wire_sob]),
                           ('BORReport_RemarkDetails', [wire_remark, wire_remark])):
            self.assertIsInstance(captures[name], RecordRows)
            self.assertTrue(hasattr(captures[name], '_data'))
            self.assertEqual(list(captures[name]), rows)
            self.assertEqual(expected[bor_sources.DIGEST_FIELDS[name]], legacy_digest(rows))
        self.assertEqual(remark['RemarkDate'], stamp)

    def test_capture_validation_keeps_field_type_count_and_digest_denials(self):
        row = dict(SKUCode='é', WHCode='L', SupplierCode='S', SOB=0.125)
        for rows, count, checksum, error in (
            ([row], 2, legacy_digest([row]), 'count differs'),
            ([dict(reversed(list(row.items())))], 1, '0'*64, 'field order'),
            ([dict(row, SOB=1)], 1, '0'*64, 'type/length'),
            ([row], 1, '0'*64, 'values differ'),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                bor_sources.validate_capture('SOBData', RecordRows.from_rows(rows),
                    expected_count=count, expected_digest=checksum)

    def test_boroa_decimal_capture_and_readback_keep_declared_scale_and_nulls(self):
        name = 'BORWithOrderAllocation'
        specs = boroa_sources.SOURCE_FIELDS[name]
        row = {field: (None if spec['nullable'] else
                      'é' if spec['kind'] == 'text' else
                      Decimal('0.125').quantize(Decimal(1).scaleb(-spec['scale']))
                      if spec['kind'] == 'decimal' else 1)
               for field, spec in specs.items()}
        # Exercise a non-NULL decimal even when that field permits NULL.
        field = next(field for field, spec in specs.items() if spec['kind'] == 'decimal')
        row[field] = Decimal('0.125').quantize(Decimal(1).scaleb(-specs[field]['scale']))
        wire = {key: str(value) if isinstance(value, Decimal) else value for key, value in row.items()}
        checksum = legacy_digest([wire, wire])
        self.assertEqual(boroa_sources.validate_capture(name, RecordRows.from_rows([wire, wire]),
            expected_count=2, expected_digest=checksum), checksum)
        model = MagicMock()
        model.objects.filter.return_value = StreamOnlyQuery(
            lambda: (dict(ordinal=i, **row) for i in range(2)))
        with patch.dict(boroa_sources.MODELS, {name: model}, clear=True):
            self.assertEqual(boroa_sources.verify_values(SimpleNamespace(kind='DAILY_CHAIN')),
                {boroa_sources.DIGEST_FIELDS[name]: checksum})
        for value in ('NaN', '0.000000001', 1):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'capture type differs'):
                boroa_sources.validate_capture(name, RecordRows.from_rows([dict(wire, **{field: value})]),
                    expected_count=1, expected_digest='0'*64)

    def test_source_build_bounds_model_construction_and_keeps_ordinals(self):
        count = 901
        rows = RecordRows(count, lambda: (dict(SKUCode='é', WHCode='L', SupplierCode='S',
                                              SOB=0.125) for _ in range(count)))
        checksum = bor_sources.capture_digest(rows)
        constructed, inserted = [], []
        model = MagicMock()
        def make(**values):
            constructed.append(values['ordinal'])
            self.assertLessEqual(len(constructed), 300)
            return SimpleNamespace(**values)
        def insert(batch, *, batch_size):
            self.assertEqual(batch_size, 300)
            self.assertEqual([row.ordinal for row in batch], constructed)
            inserted.extend(constructed)
            constructed.clear()
        model.side_effect = make
        model.objects.bulk_create.side_effect = insert
        model.objects.filter.return_value.exists.return_value = False
        receipt_model = MagicMock()
        receipt_model.objects.filter.return_value.first.return_value = None
        receipt_model.objects.create.side_effect = lambda **values: SimpleNamespace(**values)
        sources = SimpleNamespace(MODELS={'SOBData': model}, DIGEST_FIELDS={'SOBData': 'sob_digest'},
            verify_values=MagicMock(return_value={'sob_digest': checksum}), admitted_sources=MagicMock())
        modules = (sources, None, {'SOBData': bor_sources.FIELDS['SOBData']}, None, None,
                   receipt_model, None, None, MagicMock(), None)
        with patch.object(bor, '_source_expected', return_value=(
                {'SOBData': rows}, {'recipe_digest': 'recipe', 'sob_digest': checksum})), \
             patch.object(bor.connection, 'cursor', return_value=MagicMock()):
            receipt = bor._prepare_source(SimpleNamespace(pk='run'), 'bor', 'source', modules,
                                          verify_only=False)
        self.assertEqual(inserted, list(range(count)))
        self.assertEqual(model.objects.bulk_create.call_count, 4)
        self.assertEqual(receipt.sob_digest, checksum)
        sources.admitted_sources.assert_called_once()

    def test_source_resume_and_verify_only_recheck_complete_producer_values(self):
        sources = SimpleNamespace(MODELS={}, DIGEST_FIELDS={'SOBData': 'sob_digest'},
            verify_values=MagicMock(return_value={'sob_digest': 'same'}), admitted_sources=MagicMock())
        receipt_model = MagicMock()
        receipt = SimpleNamespace(recipe_digest='recipe', source_digest='source', sob_digest='same')
        receipt_model.objects.filter.return_value.first.return_value = receipt
        modules = (sources, None, {}, None, None, receipt_model, None, None, None, None)
        for verify_only in (False, True):
            with patch.object(bor, '_source_expected', return_value=(
                    {}, {'recipe_digest': 'recipe', 'sob_digest': 'same'})):
                sources.verify_values.return_value = {'sob_digest': 'same'}
                self.assertIs(bor._prepare_source(None, 'bor', 'source', modules,
                                                  verify_only=verify_only), receipt)
                sources.verify_values.return_value = {'sob_digest': 'drift'}
                with self.assertRaisesRegex(PublicationUnavailable, 'source_producer_values_changed'):
                    bor._prepare_source(None, 'bor', 'source', modules, verify_only=verify_only)
                sources.verify_values.return_value = {}
                with self.assertRaisesRegex(PublicationUnavailable, 'source_producer_values_changed'):
                    bor._prepare_source(None, 'bor', 'source', modules, verify_only=verify_only)
        receipt_model.objects.create.assert_not_called()

    def test_bor_and_boroa_readback_stream_with_original_wire_and_ordinal_denial(self):
        cases = (
            (bor_sources, 'BORReport_RemarkDetails',
             dict(SKUCode='é', WhCode='L', Remark=None, Username='',
                  RemarkDate=datetime(2026, 6, 17, tzinfo=timezone.utc), SupplierCode='S'),
             '2026-06-17T00:00:00'),
            (boroa_sources, 'BORReport_OARemarkDetails',
             dict(SKUCode='é', WhCode='L', Remark=None, Username='',
                  RemarkDate=datetime(2026, 6, 17, tzinfo=timezone.utc), SupplierCode='S'),
             '2026-06-17T00:00:00+00:00'),
        )
        for module, name, row, stamp in cases:
            model = MagicMock()
            query = StreamOnlyQuery(lambda: (dict(ordinal=i, **row) for i in range(1201)))
            model.objects.filter.return_value = query
            with self.subTest(module=module.__name__), \
                 patch.dict(module.MODELS, {name: model}, clear=True):
                values = module.verify_values(SimpleNamespace(kind='DAILY_CHAIN'))
                expected = [dict(row, RemarkDate=stamp)] * 1201
                self.assertEqual(values, {module.DIGEST_FIELDS[name]: legacy_digest(expected)})
                query.factory = lambda: iter([dict(ordinal=0, **row), dict(ordinal=2, **row)])
                with self.assertRaisesRegex(PublicationUnavailable, 'ordinal_population_changed'):
                    module.verify_values(SimpleNamespace(kind='DAILY_CHAIN'))

    def test_planning_receipt_streams_same_digest_and_denies_gap_or_value_drift(self):
        rows = [('git_parent', 'é', None, 'raw', i % 7) for i in range(1201)]
        query = StreamOnlyQuery(lambda: ((i, *row) for i, row in enumerate(rows)))
        receipt = SimpleNamespace(row_count=len(rows), rows_digest=digest(rows))
        with patch.object(summary.PlanningSummaryContribution.objects, 'filter', return_value=query):
            self.assertEqual(summary._contribution_receipt(receipt), (len(rows), digest(rows)))
            summary.verify_contribution_rows(receipt)
            receipt.rows_digest = '0'*64
            with self.assertRaisesRegex(PublicationUnavailable, 'summary_rows_changed'):
                summary.verify_contribution_rows(receipt)
            query.factory = lambda: iter([(0, *rows[0]), (2, *rows[1])])
            with self.assertRaisesRegex(PublicationUnavailable, 'ordinals_changed'):
                summary.verify_contribution_rows(receipt)


if __name__ == '__main__':
    unittest.main()
