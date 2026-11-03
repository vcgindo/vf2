"""Physical reference reuse retains complete logical owner and ordered types."""
from copy import deepcopy
from unittest import TestCase

from mta.application.native_output_contracts import native_assignments
from mta.application.stage_calculation_sources import capture_bpr
from mta.runtime import phase_state, phase_state_layout as layout
from mta.runtime.phase_image_storage import FORMAT, ImageWriter, owns_physical_image
from mta.serialization import storage
from mta.temporal import chain
from tests.test_phase_state import MemoryImages, native_prepared, calculation
from tests import phase_state_v1_reference as legacy


def encode(phase, sources, memory, parent=None):
    writer = ImageWriter(lambda path, table, rows, description: memory.rows(path, table, rows),
                         parent_manifest=parent)
    result = layout.encode(phase, sources, image_writer=writer, export_writer=memory.export)
    result['storage_format'] = FORMAT
    return result


class PhaseImageStorageTests(TestCase):
    def test_current_dbm_cannot_indirectly_inherit_prior_control_cut(self):
        rows=[dict(SKUCode='S',WhCode='W',Type=5,OldNorm=123,NewNorm=82,SuggestionDate=None)]
        from mta.runtime.inherited_history_image import FORMAT as HISTORY_FORMAT
        control='phase/DBM/controls/suggestions_log'
        current='phase/DBM/dbm/SuggestionsLog'
        memory=MemoryImages()
        def prior(path,table,description):
            if path==control:
                return dict(description[0],table=table,storage_format=HISTORY_FORMAT,
                            run_id='child',cut_id='prior-cut',cut_digest='a'*64)
            return None
        writer=ImageWriter(lambda p,t,r,d:memory.rows(p,t,r),prior_writer=prior)
        carried=writer(control,'DBM/SuggestionsLog',rows)
        produced=writer(current,'DBM/SuggestionsLog',rows)
        self.assertEqual(carried['storage_format'],HISTORY_FORMAT)
        self.assertNotIn('storage_format',produced)
        self.assertEqual(produced['image'],current)
        self.assertEqual(memory.writes,[current])
        forged=dict(phase='DBM',storage_format=FORMAT,images={current:carried,control:carried},
                    state={'control_final':{'suggestions_log':{'image':control}}})
        self.assertFalse(owns_physical_image((forged,),current,carried))

    def test_unchanged_history_reuses_pre_bpr_owner_through_dbm_and_restarts(self):
        self._assert_history_restart(legacy_parent=False)

    def test_actual_v1_parent_to_v2_child_retains_owner_and_restarts(self):
        self._assert_history_restart(legacy_parent=True)

    def _assert_history_restart(self, *, legacy_parent):
        with native_assignments(True):
            prepared, opening, refs = native_prepared('image-reference-owners')
            rows = [dict(SKUCode='S1', WhCode='L1', Type=1, OldNorm=10, NewNorm=12,
                         SuggestionDate=value) for value in (None, '2037-04-08', '2037-04-08')]
            prepared.context.prior['dbm']['SuggestionsLog'] = deepcopy(rows)
            prepared.control_final['suggestions_log'] = deepcopy(rows)
            refs['prior']['dbm']['SuggestionsLog'] = deepcopy(rows)
            memory = MemoryImages()
            def parent_encode(phase, consumers, parent=None):
                if legacy_parent:
                    return legacy.encode(phase, consumers, row_writer=memory.rows,
                        export_writer=memory.export, parent_manifest=parent)
                return encode(phase, consumers, memory, parent)
            pre = parent_encode(prepared, None)
            bpr = chain.produce_bpr(prepared)
            sources = capture_bpr(bpr, opening)
            bp = parent_encode(bpr, sources, pre)
            dbm = chain.produce_dbm(bpr)
            current = encode(dbm, sources, memory, bp)
            logical = 'phase/DBM/dbm/SuggestionsLog'
            item = current['images'][logical]
            self.assertEqual(item['image'], 'phase/PRE_BPR/controls/suggestions_log')
            self.assertNotIn(logical, memory.writes)
            self.assertTrue(owns_physical_image((current, bp, pre), logical, item))
            history_writes = [p for p in memory.writes if p.endswith(('/suggestions_log', '/SuggestionsLog'))]
            self.assertEqual(history_writes, ['phase/PRE_BPR/controls/suggestions_log'])
            restored, captured = layout.decode(current, **refs, row_reader=memory.read,
                export_reader=memory.read, execute_calculation=calculation)
            self.assertEqual(restored.final_dbm['SuggestionsLog'], rows)
            self.assertEqual(restored.control_final['suggestions_log'], rows)
            result = chain.produce_btr_from_snapshot(restored, captured,
                pick_source_digests=current['metadata']['pick_source_digests']).output
            expected = chain.produce_btr(dbm)
            self.assertEqual(storage(phase_state.typed.production_projection(result)),
                             storage(phase_state.typed.production_projection(expected)))
            self.assertTrue(any('/report-facts/' in path and path not in memory.writes
                                for path in current['images']))
            for path, meta in current['images'].items():
                if '/report-facts/' in path and path not in memory.writes:
                    self.assertTrue(owns_physical_image((current, bp, pre), path, meta), path)

    def test_different_values_order_or_wire_types_are_written_independently(self):
        base = [dict(SKUCode='S1', WhCode='L1', Type=1, OldNorm=n, NewNorm=12,
                     SuggestionDate=None) for n in (0, 1)]
        for rows in (list(reversed(base)), [dict(row, OldNorm=bool(row['OldNorm'])) for row in base],
                     [{('WHCode' if key == 'WhCode' else key): value for key, value in row.items()} for row in base],
                     [dict(reversed(list(row.items()))) for row in base],
                     [*base, deepcopy(base[1])]):
            memory = MemoryImages()
            writer = ImageWriter(lambda path, table, values, _: memory.rows(path, table, values))
            writer('phase/DBM/controls/suggestions_log', 'DBM/SuggestionsLog', base)
            actual = writer('phase/DBM/dbm/SuggestionsLog', 'DBM/SuggestionsLog', rows)
            self.assertEqual(actual['image'], 'phase/DBM/dbm/SuggestionsLog')
            self.assertEqual(len(memory.writes), 2)

    def test_order_summary_shares_only_its_matching_controls_and_changed_report_writes(self):
        rows = [dict(SKUCode='S1', WhCode='L1', NodeOrderCount=1, CummOrderCount=2,
                     NodeConsumption=3, ImportDate=None)]
        memory = MemoryImages()
        writer = ImageWriter(lambda path, table, values, _: memory.rows(path, table, values))
        control = writer('phase/DBM/controls/order_summary', 'DBM/OrderDataSummary', rows)
        dbm = writer('phase/DBM/dbm/OrderDataSummary', 'DBM/OrderDataSummary', rows)
        self.assertEqual(dbm, control)
        source = 'phase/DBM/report-facts/norm-change-history/OrderDataSummary'
        self.assertEqual(writer(source, 'DBM/OrderDataSummary', rows), control)
        changed = 'phase/DBM/report-facts/norm-change-export/OrderDataSummary'
        result = writer(changed, 'DBM/OrderDataSummary', [dict(rows[0], NodeOrderCount=4)])
        self.assertEqual(result['image'], changed)
        self.assertEqual(memory.writes, ['phase/DBM/controls/order_summary', changed])

    def test_unrelated_empty_owner_old_format_missing_source_and_wrong_table_deny(self):
        logical = 'phase/DBM/dbm/SuggestionsLog'
        source = 'phase/DBM/controls/suggestions_log'
        meta = dict(image=source, table='DBM/SuggestionsLog', count=0, fields=[], digest='empty')
        manifest = dict(phase='DBM', storage_format=FORMAT,
            state={'control_final': {'suggestions_log': {'image': source}}},
            images={logical: meta, source: meta})
        self.assertTrue(owns_physical_image((manifest,), logical, meta))
        for bad in ('old_format', 'wrong_table', 'missing_source', 'wrong_logical_owner', 'unrelated'):
            changed = deepcopy(manifest)
            if bad == 'old_format':changed.pop('storage_format')
            if bad == 'wrong_table':changed['images'][logical]['table'] = 'Importer/SettingsTbl'
            if bad == 'missing_source':changed['images'].pop(source)
            if bad == 'wrong_logical_owner':changed['state']['control_final']['suggestions_log'] = {'image': logical}
            if bad == 'unrelated':
                changed['images'][logical]['image'] = 'phase/DBM/dbm/Unrelated'
                changed['images']['phase/DBM/dbm/Unrelated'] = changed['images'][logical]
            with self.subTest(bad=bad):
                self.assertFalse(owns_physical_image((changed,), logical, changed['images'][logical]))
