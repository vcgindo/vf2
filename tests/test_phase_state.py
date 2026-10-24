"""Native live-out contracts, independent of scope business acceptance."""
from copy import deepcopy
from unittest import TestCase

from mta.application.native_output_contracts import native_assignments
from mta.application.stage_calculation_sources import capture_bpr
from mta.application.operational_capture import CAPTURE_POLICY
from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY
from mta.application.timeline_controls import FORCE_CAPTURE_POLICY
from mta.application import production_output_policy
from mta.runtime import phase_state
from mta.runtime.relational_state import production_projection
from mta.serialization import digest, storage
from mta.temporal import chain
from tests.test_daily_calculation_phases import inputs, calculation


def native_prepared(identity='phase-state-test'):
    prior, day, profile = inputs()
    profile.update(operational_sources=CAPTURE_POLICY,
        operational_input_sources=INPUT_CAPTURE_POLICY,
        operational_force_sources=FORCE_CAPTURE_POLICY)
    policy = dict(bor_history_horizon=90, rrr_history_horizon=90,
                  output_contract=production_output_policy.contract())
    day['production_report_policy'] = policy
    opening = dict(supplier=deepcopy(prior['supplier']),
        production_report_policy=policy,
        production_report_schema=production_output_policy.SOURCE_SCHEMA)
    refs = deepcopy(dict(prior=prior, day=day, profile=profile, master_snapshot=None))
    phase = chain.prepare_day(prior, '2037-04-09', day, profile,
                              identity, calculation, native_daily=True)
    return phase, opening, refs


def native_bpr(identity='phase-state-test'):
    prepared, opening, refs = native_prepared(identity)
    phase = chain.produce_bpr(prepared)
    return phase, capture_bpr(phase, opening), refs


class MemoryImages:
    def __init__(self):self.values = {}; self.writes = []

    def rows(self, path, table, values):
        self.writes.append(path)
        self.values[path] = storage(values)
        columns = {n.casefold(): (n, kind) for n, kind in phase_state.REGISTRY[table]}
        meta, _, _ = phase_state.typed.describe_rows(values, columns, path)
        return dict(meta, table=table)

    def export(self, path, values):
        self.values[path] = storage(values)
        return dict(image=path, count=len(values), digest=digest(values), version=2)

    def read(self, item):
        value = deepcopy(self.values[item['image']])
        if len(value) != item['count'] or digest(value) != item['digest']:
            raise ValueError('Fixture typed value/order drift')
        return value


class PhaseStateTests(TestCase):
    def test_prepared_snapshot_restarts_before_bpr_without_intake_or_controls(self):
        from unittest.mock import patch
        with native_assignments(True):
            prepared, opening, refs = native_prepared()
            expected_bpr = chain.produce_bpr(deepcopy(prepared))
            expected_sources = capture_bpr(expected_bpr, opening)
            expected = chain.produce_btr(chain.produce_dbm(expected_bpr))
            memory = MemoryImages()
            manifest = phase_state.encode(prepared, None, row_writer=memory.rows,
                                          export_writer=memory.export)
            with self.assertRaisesRegex(ValueError, 'calculation callable'):
                phase_state.decode(manifest, **deepcopy(refs), row_reader=memory.read,
                                   export_reader=memory.read)
            restored, sources = phase_state.decode(manifest, **deepcopy(refs),
                row_reader=memory.read, export_reader=memory.read, execute_calculation=calculation)
            self.assertIsNone(sources)
            self.assertIsNone(restored.daily)
            self.assertIsNone(restored.daily_input)
            self.assertIs(restored.context.completion, restored.context.prior['complete'])
            with patch('mta.temporal.entry_preparation.prepare', side_effect=AssertionError('intake replay')), \
                    patch('mta.application.timeline_controls.timeline_control_stages', side_effect=AssertionError('control replay')), \
                    patch.object(chain, 'generated_bpr_daily_state', side_effect=AssertionError('daily graph replay')):
                bpr = chain.produce_bpr(restored)
            actual_sources = capture_bpr(bpr, opening)
            actual = chain.produce_btr(chain.produce_dbm(bpr))
        self.assertEqual(storage(actual), storage(expected))
        self.assertEqual(storage(actual_sources.__dict__), storage(expected_sources.__dict__))
        self.assertNotIn('CalculationOutputs', str(manifest))
        self.assertIsNone(manifest['consumers'])

    def test_bpr_and_pre_btr_dbm_roundtrip_keep_complete_terminal_projection(self):
        with native_assignments(True):
            bpr, sources, refs = native_bpr()
            expected = chain.produce_btr(chain.produce_dbm(deepcopy(bpr)))
            memory = MemoryImages()
            manifest = phase_state.encode(bpr, sources, row_writer=memory.rows,
                                         export_writer=memory.export)
            restored, actual_sources = phase_state.decode(manifest, **deepcopy(refs),
                row_reader=memory.read, export_reader=memory.read)
            self.assertIsNone(restored.calculated)
            self.assertEqual(storage(actual_sources.__dict__), storage(sources.__dict__))
            self.assertNotIn('allocations', restored.pick_state)
            self.assertNotIn('AdditionalMasterData', restored.order_state)
            self.assertEqual(restored.force_alert_capture, bpr.force_alert_capture)
            self.assertEqual(restored.operational_input_tables, bpr.operational_input_tables)
            dbm = chain.produce_dbm(restored)
            dbm_manifest = phase_state.encode(dbm, actual_sources, row_writer=memory.rows,
                export_writer=memory.export, parent_manifest=manifest)
            self.assertEqual(dbm_manifest['images']['phase/DBM/bpr_master'],
                             manifest['images']['phase/BPR/bpr_master'])
            self.assertNotIn('phase/DBM/bpr_master', memory.writes)
            terminal, final_sources = phase_state.decode(dbm_manifest, **deepcopy(refs),
                row_reader=memory.read, export_reader=memory.read)
            standards = deepcopy(terminal.final_dbm['SKULocStandardAttributes'])
            result = chain.produce_btr_from_snapshot(terminal, final_sources,
                pick_source_digests=dbm_manifest['metadata']['pick_source_digests'])
        self.assertEqual(terminal.final_dbm['SKULocStandardAttributes'], standards)
        self.assertNotIn('CalculationOutputs', result.output)
        self.assertEqual(storage(result.calculation_sources.__dict__), storage(sources.__dict__))
        self.assertEqual(storage(production_projection(result.output)),
                         storage(production_projection(expected)))
        for key in ('_PickSourceDigests', '_MasterPreparation', '_OperationalInputTables',
                    '_OperationalForceSources', '_CompletedBoundaries', '_Cohort1'):
            self.assertEqual(result.output[key], expected[key], key)

    def test_frozen_dependency_changes_are_rejected_before_any_image_read(self):
        with native_assignments(True):
            bpr, sources, refs = native_bpr()
        memory = MemoryImages()
        manifest = phase_state.encode(bpr, sources, row_writer=memory.rows,
                                     export_writer=memory.export)
        for family, key in (('prior', 'dbm'), ('prior', 'bpr'), ('day', 'order_raw'),
                            ('day', 'exclusions'), ('day', 'order_feed'), ('day', 'order_feed_status')):
            changed = deepcopy(refs)
            changed[family][key] = dict(unrelated='revision')
            with self.subTest(family=family, key=key), self.assertRaisesRegex(
                    ValueError, 'dependency revision'):
                phase_state.decode(manifest, **changed,
                    row_reader=lambda _: self.fail('read before dependency validation'),
                    export_reader=memory.read)
        with self.assertRaisesRegex(ValueError, 'Full BTR assembly'):
            restored, _ = phase_state.decode(manifest, **refs,
                row_reader=memory.read, export_reader=memory.read)
            chain.produce_btr(chain.produce_dbm(restored))

    def test_snapshot_manifest_has_shapes_and_references_not_business_cells(self):
        with native_assignments(True):bpr, sources, _ = native_bpr()
        memory = MemoryImages()
        manifest = phase_state.encode(bpr, sources, row_writer=memory.rows,
                                     export_writer=memory.export)
        encoded = str(manifest)
        self.assertNotIn('SUPPLIED-Z9', encoded)
        self.assertNotIn('OWN-PARENT', encoded)
        self.assertNotIn('CalculationOutputs', encoded)
        self.assertEqual(manifest['metadata']['calculation_digest'], sources.calculation_digest)
        self.assertTrue(manifest['images'])
