"""Source preparation invariants not covered by the retained heavy bag proof."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation.planning_source_sql import (
    BPR_FIELDS, GIT_FIELDS, bpr_master_query, git_master_query, validate_target_lengths, source_queries,
)


class PlanningSourceSQLTests(unittest.TestCase):
    def test_preparation_refuses_wrong_fixture_before_reading_sources(self):
        from mta.presentation.context import PublicationUnavailable
        selected = SimpleNamespace(pk='retained')
        with patch('mta.presentation.fixture.binding', return_value=(selected, 'seal')), \
                patch('mta.presentation.selective.image_query') as query:
            for kind, pk, day in [('DAILY_CHAIN', 'retained', '2026-04-07'),
                                  ('LEGACY_UI_FIXTURE', 'other', '2026-04-07'),
                                  ('LEGACY_UI_FIXTURE', 'retained', '2026-06-17')]:
                with self.subTest(kind=kind, pk=pk, day=day), self.assertRaises(PublicationUnavailable):
                    source_queries(SimpleNamespace(kind=kind, pk=pk, business_date=day))
            query.assert_not_called()

    def test_git_target_conversion_and_existence_do_not_expand_parent_matches(self):
        query = git_master_query('SELECT * FROM rationed', 'SELECT * FROM standards')
        self.assertIn('trunc(b."Price")::integer', query)
        self.assertIn('EXISTS(SELECT 1 FROM base c', query)
        self.assertIn('WHERE a."GIT">0', query)
        self.assertNotIn('DISTINCT', query)
        self.assertIn('a.vf_ordinal rationed_ordinal,b.vf_ordinal standard_ordinal', query)
        self.assertIn('TRUE AS "IsReceiving"', query)

    def test_master_preserves_source_occurrences(self):
        query = bpr_master_query('SELECT * FROM importer_master')
        self.assertIn('vf_ordinal source_ordinal', query)
        self.assertNotIn('DISTINCT', query)
        self.assertIn('"WhCode" AS "WHCode"', query)

    def test_target_nvarchar_limits_use_utf16_units(self):
        row = {field: None for field in GIT_FIELDS}
        row['SKUCode'] = '\U0001f600' * 25
        validate_target_lengths([row], GIT_FIELDS)
        row['SKUCode'] += 'a'
        with self.assertRaisesRegex(ValueError, 'SKUCode'):
            validate_target_lengths([row], GIT_FIELDS)

    def test_nulls_and_exact_color_limit(self):
        row = {field: None for field in GIT_FIELDS}
        row['PhysicalInventoryColor'] = 'a' * 10
        validate_target_lengths([row], GIT_FIELDS)
        row['PhysicalInventoryColor'] += 'b'
        with self.assertRaisesRegex(ValueError, 'PhysicalInventoryColor'):
            validate_target_lengths([row], GIT_FIELDS)
        validate_target_lengths([{field: None for field in BPR_FIELDS}], BPR_FIELDS)
