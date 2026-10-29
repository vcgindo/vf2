"""One accepted handoff, immutable predecessor rows and bounded preparation."""
from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from mta.application import accepted_inputs, persistent_master, r1_daily_input
from mta.application.r1_calculation import _OwnedTrackAInputs
from mta.row_sequences import RecordRows


class DailyIngestionPolicyTests(TestCase):
    def test_lazy_typed_input_is_validated_once_not_on_each_traversal(self):
        original = [{'SKUCode': 'A', 'ReportDate': '2026-04-08'},
                    {'SKUCode': 'A', 'ReportDate': '2026-04-08'}]
        source = RecordRows(len(original), lambda: (dict(row) for row in original))
        with patch.object(r1_daily_input, 'date', wraps=date) as dates:
            rows = r1_daily_input._typed_rows(source, ('SKUCode', 'ReportDate'))
            self.assertEqual(dates.fromisoformat.call_count, len(original))
            self.assertEqual(list(rows), original)
            self.assertEqual(list(rows), original)
            self.assertEqual(rows[1], original[1])
            self.assertEqual(dates.fromisoformat.call_count, len(original))
        invalid = RecordRows(1, lambda: iter([{'SKUCode': 'A', 'ReportDate': 'invalid'}]))
        with self.assertRaises(ValueError):
            r1_daily_input._typed_rows(invalid, ('SKUCode', 'ReportDate'))

    def test_track_a_preparation_moves_once_without_copy_or_retained_graph(self):
        track = {'nodes': []}
        shared = {'nodes': track['nodes']}
        value = (track, shared)
        owned = _OwnedTrackAInputs(value)
        taken = owned.take()
        self.assertIs(taken, value)
        self.assertIs(taken[0]['nodes'], taken[1]['nodes'])
        self.assertIsNone(owned._value)
        with self.assertRaisesRegex(ValueError, 'already consumed'):
            owned.take()

    def test_persisted_master_rows_are_copied_for_mutation_without_prior_raw_replay(self):
        rows = [{'Code': 'B', 'Approved': True}, {'Code': 'A', 'Approved': False}]
        prior = {'importer': {'MasterData': RecordRows(2, lambda: (dict(row) for row in rows)),
            'MasterDataRaw': RecordRows(1, lambda: (_ for _ in ()).throw(AssertionError('old raw replay')))}}
        result = persistent_master.static_tables(prior)
        self.assertEqual(result, {'MasterData': [{'Code': 'A', 'Approved': 0}, {'Code': 'B', 'Approved': 1}]})
        self.assertIs(list(prior['importer']['MasterData'])[0]['Approved'], True)
        result['MasterData'][1]['Code'] = 'C'
        self.assertEqual(list(prior['importer']['MasterData'])[0]['Code'], 'B')

    def test_execution_keeps_the_gate_handoff_through_publication_then_releases_it(self):
        context = SimpleNamespace(identity='owned-run', native_daily=True, accepted_inputs=None)
        self.assertFalse(accepted_inputs.accepted())
        with accepted_inputs.execution('owned-run'):
            self.assertFalse(accepted_inputs.accepted())
            accepted_inputs._complete(context)
            admitted = accepted_inputs.current()
            self.assertIs(admitted, context.accepted_inputs)
            with accepted_inputs.consume(context):
                self.assertIs(accepted_inputs.current(), admitted)
            self.assertIs(accepted_inputs.current(), admitted)
        self.assertFalse(accepted_inputs.accepted())
