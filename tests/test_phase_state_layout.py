"""Exact old/new logical codec qualification before physical-writer activation."""
from copy import deepcopy
from unittest import TestCase

from mta.application.native_output_contracts import native_assignments
from mta.application.stage_calculation_sources import capture_bpr
from mta.row_sequences import RecordRows
from mta.runtime import phase_state_layout as layout
from tests import phase_state_v1_reference as phase_state
from mta.runtime.relational_state import production_projection
from mta.serialization import storage, digest
from mta.temporal import chain
from tests.test_phase_state import MemoryImages, native_prepared, calculation


def layout_encode(phase, sources, memory, parent=None):
    """The unchanged v1 placement rule, separate from logical population choice."""
    def write(path, table, rows):
        columns = {n.casefold(): (n, kind) for n, kind in layout.REGISTRY[table]}
        description = phase_state.typed.describe_rows(rows, columns, path)[0]
        description['table'] = table
        inherited = None if parent is None else parent['images'].get(
            'phase/'+parent['phase']+'/'+path.split('/', 2)[2])
        if inherited is not None and all(description[key] == inherited[key]
                for key in ('table', 'count', 'digest', 'fields')):
            return inherited
        return memory.rows(path, table, rows)
    return layout.encode(phase, sources, image_writer=write, export_writer=memory.export)


class PhaseLayoutTests(TestCase):
    def test_all_phase_manifests_and_terminal_continuations_are_exact(self):
        with native_assignments(True):
            prepared, opening, refs = native_prepared('logical-layout')
            bpr = chain.produce_bpr(deepcopy(prepared))
            sources = capture_bpr(bpr, opening)
            dbm = chain.produce_dbm(deepcopy(bpr))
            old, new = MemoryImages(), MemoryImages()
            old_parent = new_parent = None
            expected = chain.produce_btr(deepcopy(dbm))
            for phase, consumers in ((prepared, None), (bpr, sources), (dbm, sources)):
                with self.subTest(phase=type(phase).__name__):
                    old_manifest = phase_state.encode(phase, consumers, row_writer=old.rows,
                        export_writer=old.export, parent_manifest=old_parent)
                    new_manifest = layout_encode(phase, consumers, new, new_parent)
                    self.assertEqual(new_manifest, old_manifest)
                    self.assertEqual(new.values, old.values)
                    self.assertEqual(new.writes, old.writes)
                    self.assertEqual(layout.consumer_identity(new_manifest),
                                     phase_state.consumer_identity(old_manifest))
                    restored, captured = layout.decode(new_manifest, **deepcopy(refs),
                        row_reader=new.read, export_reader=new.read,
                        execute_calculation=calculation)
                    if new_manifest['phase'] == 'PRE_BPR':
                        restored = chain.produce_bpr(restored)
                    if new_manifest['phase'] != 'DBM':
                        restored = chain.produce_dbm(restored)
                    # Restored BPR/DBM must use the existing snapshot continuation,
                    # including its phase-owned pre-BTR standards and sources.
                    if new_manifest['phase'] == 'PRE_BPR':
                        actual = chain.produce_btr(restored)
                    else:
                        actual = chain.produce_btr_from_snapshot(restored, captured,
                            pick_source_digests=new_manifest['metadata']['pick_source_digests']).output
                    self.assertEqual(storage(production_projection(actual)),
                                     storage(production_projection(expected)))
                    old_parent, new_parent = old_manifest, new_manifest

    def test_large_null_duplicate_history_and_deferred_sources_keep_wire_order(self):
        with native_assignments(True):
            prepared, opening, refs = native_prepared('layout-positive-history')
            # Crossing the actual lazy/spooled representation boundary matters:
            # a list-only layout proof would not qualify history consumers.
            rows = RecordRows.from_rows(dict(SKUCode='S1', WhCode='L1', Type=1,
                OldNorm=10, NewNorm=12, SuggestionDate=None if i % 17 == 0 else '2037-04-08')
                for i in range(10001))
            try:
                prepared.context.prior['dbm']['SuggestionsLog'] = rows
                prepared.control_final['suggestions_log'] = chain.control_rows(rows)
                bpr = chain.produce_bpr(prepared)
                sources = capture_bpr(bpr, opening)
                dbm = chain.produce_dbm(bpr)
                old, new = MemoryImages(), MemoryImages()
                expected = phase_state.encode(dbm, sources, row_writer=old.rows,
                                               export_writer=old.export)
                actual = layout_encode(dbm, sources, new)
                self.assertEqual(actual, expected)
                self.assertEqual(new.values, old.values)
                self.assertEqual(new.writes, old.writes)
                for path in ('phase/DBM/controls/suggestions_log', 'phase/DBM/dbm/SuggestionsLog'):
                    self.assertEqual(actual['images'][path]['count'], 10001)
                    self.assertEqual(actual['images'][path]['digest'], digest(rows))
                self.assertTrue(any(path.startswith('phase/DBM/report-facts/') for path in actual['images']))
            finally:
                rows._spool_finalizer()

    def test_dependency_and_phase_refusals_stay_before_row_reads(self):
        with native_assignments(True):
            prepared, _opening, refs = native_prepared('layout-refusals')
        memory = MemoryImages()
        manifest = layout_encode(prepared, None, memory)
        for family, name in (('prior', 'dbm'), ('day', 'business_date'), ('day', 'exclusions')):
            changed = deepcopy(refs)
            changed[family][name] = {'wrong': 'owner'}
            for codec in (phase_state, layout):
                with self.subTest(family=family, name=name, codec=codec.__name__), self.assertRaisesRegex(
                        ValueError, 'dependency revision'):
                    codec.decode(manifest, **changed,
                        row_reader=lambda _: self.fail('Read before dependency authentication'),
                        export_reader=memory.read, execute_calculation=calculation)
        with self.assertRaisesRegex(ValueError, 'schema/phase'):
            layout.decode(dict(manifest, phase='UNKNOWN'), **refs,
                          row_reader=memory.read, export_reader=memory.read)
        with self.assertRaisesRegex(ValueError, 'calculation callable'):
            layout.decode(manifest, **refs, row_reader=memory.read, export_reader=memory.read)
