"""Recognize only the exact new storage bookkeeping watch; retain old readers."""
from importlib import import_module
import unittest
from unittest.mock import Mock

from mta.runtime import ingestion_ownership as ownership

migration = import_module('mta.runtime.migrations.0254_rationing_anchor_revision_ownership')


class RationingAnchorOwnershipTests(unittest.TestCase):
    def test_dated_history_anchor_guard_is_exact_and_latest(self):
        dated=import_module('mta.runtime.migrations.0268_dated_history_anchor_revision')
        candidate=dict(name='mta.ingestion_watch()',security_definer=True,
            configuration=['search_path=pg_catalog, mta'],returns='trigger',body=dated.NEW)
        self.assertTrue(ownership.is_revision_guard(candidate))
        self.assertFalse(ownership.is_revision_guard(dict(candidate,body=dated.NEW+'\n')))
        cursor=Mock()
        cursor.fetchall.return_value=[('0254_rationing_anchor_revision_ownership',),('0268_dated_history_anchor_revision',)]
        self.assertEqual(ownership.scoped_derived_body(cursor,minimum='0254_rationing_anchor_revision_ownership'),dated.NEW)

    def test_exact_frozen_body_and_metadata(self):
        candidate = dict(name='mta.ingestion_watch()', security_definer=True,
            configuration=['search_path=pg_catalog, mta'], returns='trigger', body=migration.NEW)
        self.assertTrue(ownership.is_revision_guard(candidate))
        self.assertTrue(ownership.is_revision_guard(dict(candidate, body=migration.OLD)))
        for key, value in (('body', migration.NEW+'\n'), ('name', 'mta.unknown()'),
                ('security_definer', False), ('configuration', ['search_path=public, mta']),
                ('returns', 'text')):
            with self.subTest(key=key):
                self.assertFalse(ownership.is_revision_guard(dict(candidate, **{key:value})))

    def test_scoped_reader_selects_actual_latest_without_relaxing_minimum(self):
        cursor = Mock()
        minimum = '0246_btr_scope_dimension_ingestion_ownership'
        cursor.fetchall.return_value = [(minimum,)]
        self.assertEqual(ownership.scoped_derived_body(cursor, minimum=minimum), migration.OLD)
        cursor.fetchall.return_value.append(('0254_rationing_anchor_revision_ownership',))
        self.assertEqual(ownership.scoped_derived_body(cursor, minimum=minimum), migration.NEW)
        cursor.fetchall.return_value = [('0254_rationing_anchor_revision_ownership',)]
        with self.assertRaisesRegex(ValueError, 'Required scoped derived'):
            ownership.scoped_derived_body(cursor, minimum=minimum)
