"""RRR consumer contracts over real accepted phase bands and memberships."""
from contextlib import ExitStack
from types import SimpleNamespace
import os
import unittest
import uuid
from unittest.mock import patch

from tests import test_scoped_pick_storage_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class ScopedRrrTests(unittest.TestCase):
    for name in ('setUp', 'rollback', 'owner', 'accept', 'bpr', 'parents', 'fetch',
                 'manual_members', 'prepare', 'binding'):
        locals()[name] = getattr(fixtures.ScopedPickStorageTests, name)

    def start(self):
        self.parents(counter=True)
        self.bound = self.binding(self.prepare())

    def attributes(self):
        return {name: self.bound.sources.rows('closing/importer/' + name)
                for name in ('SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData')}

    def scopes(self, weight=1, empty=False):
        from mta.presentation.context import PermissionCodes
        attrs = self.attributes()
        return (PermissionCodes({} if empty else {r['SKUCode']: weight for r in attrs['SkuAttributeData']}),
                PermissionCodes({} if empty else {r['WHCode']: weight for r in attrs['LocationAttributeData']}))

    def expected(self, payload=None, weight=1):
        from mta.presentation import rrr, rrr_filters
        sources = self.bound.sources
        importer = self.attributes()
        output = dict(ClosingState=[dict(importer=importer,
            dbm={'SKULocStandardAttributes': sources.rows('closing/dbm/SKULocStandardAttributes')})],
            BPRReports=[{'vf_RationedReqReport': sources.rows('reports/bpr/vf_RationedReqReport')}])
        predicate = rrr_filters.rrr_predicate(payload or {}, importer)
        return rrr.selected_rows(output, sources.rows('sources/calculation/PickBands'),
            predicate=lambda *rows: predicate(*rows) * weight * weight)

    def reads(self, **options):
        from mta.presentation import rrr_prepared_sql as reader, scoped_pick_storage, scoped_pick_queries
        stack = ExitStack()
        stack.enter_context(patch.object(reader, 'scope', return_value=self.scopes(**options)))
        for name in ('image_rows', 'image_query'):
            stack.enter_context(patch.object(reader, name, side_effect=AssertionError('Full source read')))
        stack.enter_context(patch.object(reader.hierarchy, 'selected_manifest', side_effect=AssertionError('Full hierarchy')))
        stack.enter_context(patch.object(scoped_pick_storage, 'prepare', side_effect=AssertionError('Request preparation')))
        stack.enter_context(patch.object(scoped_pick_queries, 'bind_sources', side_effect=AssertionError('Band reconstruction')))
        return stack

    def read(self, payload=None, *, paging=None, count=False, bound=None):
        from mta.presentation.scoped_rrr import read
        return read(self.run, payload or {}, paging=paging, count=count,
            read_binding=self.bound if bound is None else bound)

    def complete(self, *, virtual=False):
        from mta.runtime.models import PickProjection, RrrPreparedProjection
        from mta.runtime.scope_revisions import require_current
        from mta.presentation.rrr_export import FIELDS, selected_headers, csv_chunks
        from mta.presentation.rrr_types import selected_rrr_response
        self.virtual_case = virtual
        self.start()
        before = require_current(self.run)
        expected = self.expected()
        self.assertTrue(expected)
        self.assertEqual(any(r['SKUCode'] == 'SUPPLIED-Z9' and r['PWh'] == r['WhCode'] for r in expected), virtual)
        with self.reads():
            actual = self.read()
            self.assertEqual(actual, expected)
            self.assertEqual(self.read(count=True), len(expected))
            self.assertEqual(self.read(paging=(2, 1)), expected[1:2])
        self.assertEqual([selected_rrr_response(r) for r in actual], [selected_rrr_response(r) for r in expected])
        headers = selected_headers(None, FIELDS)
        self.assertEqual(b''.join(csv_chunks(actual, headers)), b''.join(csv_chunks(expected, headers)))
        self.assertFalse(PickProjection.objects.filter(run=self.run).exists())
        self.assertFalse(RrrPreparedProjection.objects.filter(run=self.run).exists())
        self.assertEqual(require_current(self.run), before)

    def test_complete_grid_count_paging_wire_and_csv_without_full_receipts(self):
        self.complete()

    def test_actual_virtual_band_preserves_original_aliases_and_wire_values(self):
        self.complete(virtual=True)

    def test_permission_multiplicities_filters_and_denied_scope(self):
        from tests.production_h3_fixture import CHILD
        self.start()
        payload = dict(filters=dict(supplyChainFilter=dict(filters=[
            dict(attributeName='forlocationlocationcode', value=CHILD, operator='equalto')])))
        expected = self.expected(payload, weight=2)
        self.assertTrue(expected)
        self.assertTrue(all(row['WhCode'] == CHILD for row in expected))
        with self.reads(weight=2):
            self.assertEqual(self.read(payload), expected)
            self.assertEqual(self.read(payload, count=True), len(expected))
        with self.reads(empty=True):
            self.assertEqual(self.read(), [])
            self.assertEqual(self.read(count=True), 0)

    def test_actual_produced_empty_membership_settles_grid_and_count(self):
        self.pick_empty_case = True
        self.start()
        self.assertEqual(self.expected(), [])
        with self.reads():
            self.assertEqual(self.read(), [])
            self.assertEqual(self.read(count=True), 0)

    def test_missing_foreign_and_mismatched_membership_deny_before_source_reads(self):
        from mta.presentation import scoped_rrr, rrr_prepared_sql as reader
        from mta.presentation.context import PublicationUnavailable
        self.start()
        with self.reads():
            for owner in (None, object()):
                with self.assertRaisesRegex(PublicationUnavailable, 'phase_owner_differs'):
                    scoped_rrr.read(self.run, {}, read_binding=owner, paging=None)
            with self.assertRaisesRegex(PublicationUnavailable, 'phase_owner_differs'):
                scoped_rrr.read(SimpleNamespace(pk=uuid.uuid4()), {}, read_binding=self.bound, paging=None)
            relation, params = self.bound.query('raw')
            with self.assertRaisesRegex(PublicationUnavailable, 'phase_membership_differs'):
                reader.read_prepared(self.run, {}, paging=None, count=False,
                    relation=relation, relation_params=params, read_binding=self.bound)

    def test_action_invalidates_fresh_admission_but_retains_inflight_rrr(self):
        from mta.runtime.scope_execution import _setting, _close_attempt
        from mta.runtime.scoped_actions import record
        from mta.presentation.context import PublicationUnavailable
        from tests.production_h3_fixture import SEASON, CHILD
        self.action_case = True
        self.start()
        with self.reads(): before = self.read()
        with _setting('fresh.scope_worker', self.attempt.worker_token):
            _close_attempt(self.attempt, self.run, 'RELEASED', {})
        event = record(self.run.pk, phase_id=self.receipt.pk, phase_digest=self.receipt.digest,
            expected_revision=0, operation='SLEEP', selected=[[SEASON, CHILD]],
            timestamp='2037-04-10T10:00:00', actor='rrr-component', idempotency_key='rrr-sleep')
        with self.assertRaises(PublicationUnavailable): self.binding(self.bound.generation)
        with self.reads(): self.assertEqual(self.read(), before)
        fresh = self.binding(self.prepare(event.pk), event.pk)
        with self.reads(): self.assertEqual(self.read(bound=fresh), before)

    def test_full_default_query_and_parameters_differ_only_at_admitted_sources(self):
        from unittest.mock import MagicMock
        from mta.presentation import rrr_prepared_sql as reader, scoped_pick_queries, rrr_preparation
        from mta.runtime.models import PickBand
        from mta.runtime.relational_state import quote
        self.start()
        relation, values = self.bound.query('rrr')
        def capture(bound):
            cursor = MagicMock()
            cursor.description = []
            cursor.fetchall.return_value = []
            with patch.object(reader.connection, 'cursor') as factory:
                factory.return_value.__enter__.return_value = cursor
                reader.read_prepared(self.run, {}, paging=(1, 5), count=False,
                    relation=relation, relation_params=values, **({} if bound is None else {'read_binding': bound}))
            return cursor.execute.call_args.args
        with patch.object(reader, 'scope', return_value=self.scopes()), \
                patch.object(reader, 'image_rows', side_effect=lambda run, path: self.bound.sources.rows(path)), \
                patch.object(reader, 'image_query', side_effect=lambda run, path: self.bound.image_query(path)), \
                patch.object(reader.hierarchy, 'selected_manifest', return_value=None):
            full_sql, full_params = capture(None)
            scoped_sql, scoped_params = capture(self.bound)
        (bands, band_params), _ = scoped_pick_queries.band_queries(self.bound.sources)
        full_join = ' JOIN mta.' + quote(PickBand._meta.db_table) + ' K ON K.run_id=H.run_id AND K.ordinal=H.band_ordinal'
        self.assertEqual(full_sql.count(full_join), 1)
        self.assertEqual(scoped_sql, full_sql.replace(',A AS (', ',K AS NOT MATERIALIZED (' + bands + '),A AS (', 1)
            .replace(full_join, ' JOIN K ON K.ordinal=H.band_ordinal'))
        source_count = len(values) + sum(len(self.bound.image_query(path)[1]) for _, path in rrr_preparation.SOURCES)
        self.assertEqual(scoped_params, [*full_params[:source_count], *band_params, *full_params[source_count:]])
