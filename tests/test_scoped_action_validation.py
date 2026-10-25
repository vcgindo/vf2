"""Explicit proof lifetime and fresh validation boundaries; native proof is separate."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from contextlib import ExitStack
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from mta.presentation import scoped_action_validation as validation, scoped_selection
from mta.presentation.context import PublicationUnavailable
from mta.runtime.models import CalculationRun


class ActionValidationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.identity = self.stack.enter_context(patch.object(validation, '_identity', return_value=('session', 'tx')))
        self.guard = self.stack.enter_context(patch.object(validation, 'guard_stamp', return_value='guards'))
        self.recipes = self.stack.enter_context(patch.object(validation, '_recipes', return_value=('recipe',)))
        self.runtime = self.stack.enter_context(patch.object(validation, '_runtime', return_value=True))

    def proof(self):
        proof = object.__new__(validation.ComponentProof)
        proof._ticket = validation.begin()
        proof._used = False
        proof._finished = False
        proof._recipes = ('recipe',)
        return proof

    def test_unqualified_or_nontransactional_callers_get_no_ticket(self):
        self.runtime.return_value = False
        self.assertIsNone(validation.begin())
        self.guard.assert_not_called()
        self.runtime.return_value = True
        self.identity.return_value = None
        self.assertIsNone(validation.begin())
        self.guard.assert_not_called()

    def test_capture_requires_dbm_and_unchanged_initial_selection_boundary(self):
        from mta.presentation.scoped_dbm_view import DbmViewBinding
        view = DbmViewBinding(None, None, None, None, None, None, None)
        ticket = validation.begin()
        self.assertIsNone(validation.capture(None, view))
        self.assertIsNone(validation.capture(ticket, object()))
        for target, changed in ((self.identity, ('new', 'tx')),):
            original = target.return_value
            target.return_value = changed
            with self.assertRaises(PublicationUnavailable):
                validation.capture(ticket, view)
            target.return_value = original

    def test_transaction_change_denies_before_owner_queries(self):
        from mta.presentation import scoped_dbm_view
        for target, value in ((self.identity, ('session', 'different-tx')),):
            proof = self.proof()
            original = target.return_value
            target.return_value = value
            with patch.object(scoped_dbm_view, '_accepted') as accepted:
                with self.assertRaises(PublicationUnavailable):
                    proof.selected({}, (1, 0))
                accepted.assert_not_called()
            target.return_value = original

    def test_failed_attempt_consumes_proof(self):
        from mta.presentation import scoped_dbm_view
        proof = self.proof()
        with patch.object(scoped_dbm_view, '_accepted', side_effect=ValueError('changed phase')) as accepted:
            with self.assertRaisesRegex(ValueError, 'changed phase'):
                proof.selected({'phase_id': 'phase', 'phase_digest': 'digest'}, (1, 0))
            with self.assertRaises(PublicationUnavailable):
                proof.selected({}, (1, 0))
            self.assertEqual(accepted.call_count, 1)

    def test_finish_requires_use_and_is_single_use(self):
        proof = self.proof()
        with self.assertRaises(PublicationUnavailable):
            proof.finish()
        proof._used = True
        proof.finish()
        with self.assertRaises(PublicationUnavailable):
            proof.finish()

    def test_finish_checks_transaction_guards_and_current_recipe_bytes(self):
        for target, value in ((self.identity, None), (self.guard, 'changed'),
                              (self.recipes, ('changed',))):
            proof = self.proof()
            proof._used = True
            original = target.return_value
            target.return_value = value
            with self.assertRaises(PublicationUnavailable):
                proof.finish()
            self.assertFalse(proof._finished)
            target.return_value = original

    def test_row_snapshot_keeps_all_concrete_fields_and_detaches_nested_metadata(self):
        run = CalculationRun(id=uuid4(), input_payload={'items': [1, None, 1]})
        frozen = validation._row(run)
        self.assertEqual(set(frozen), {field.attname for field in run._meta.concrete_fields})
        run.input_payload['items'].append(2)
        self.assertEqual(frozen['input_payload'], {'items': [1, None, 1]})
        self.assertNotEqual(frozen, validation._row(run))

    def test_source_snapshot_includes_inherited_owner_not_just_source_digest(self):
        from mta.presentation.scoped_sources import BprSources
        run = CalculationRun(id=uuid4())
        predecessor = CalculationRun(id=uuid4(), output_digest='old')
        locator = {'owner': str(predecessor.pk), 'rows': [None, 1, 1]}
        inherited = NS(owner=predecessor, provenance=lambda: deepcopy(locator))
        source = BprSources(run, uuid4(), 'phase', 'snapshot', 0, 'date', 'unchanged', {}, inherited)
        before = validation._sources(source)
        locator['rows'].reverse()
        self.assertNotEqual(before, validation._sources(source))
        locator['rows'].reverse()
        predecessor.output_digest = 'new'
        self.assertNotEqual(before, validation._sources(source))

    def test_explicit_proof_never_enters_request_cache(self):
        proof = object()
        with patch.object(scoped_selection, '_selected', return_value='fresh') as selected, \
                patch.object(scoped_selection, '_request_selected', side_effect=AssertionError('cached')):
            self.assertEqual(scoped_selection.selected(action_proof=proof), 'fresh')
            selected.assert_called_once_with(action_proof=proof)

    def test_final_candidate_and_cut_checks_precede_finish(self):
        from django.test import override_settings
        anchor = dict(schema=scoped_selection.DBM_SCHEMA, run_id='run')
        proof = Mock()
        proof.selected.return_value = object()
        with override_settings(VF_MTA_SELECTION_FILE='', VF_MTA_PUBLISHED_RUN='',
                VF_MTA_PUBLISHED_DIGEST='', VF_MTA_PHASE_SELECTION_FILE='anchor',
                VF_MTA_PHASE_SELECTION=anchor), \
                patch.object(scoped_selection, 'read', return_value=anchor), \
                patch.object(scoped_selection, '_cut', return_value=(1, 0)) as cut, \
                patch.object(scoped_selection, 'candidate', return_value=anchor) as candidate:
            # Exercise the real selector body; only its read-scope decorator is
            # omitted because this unit test has no PostgreSQL connection.
            result = scoped_selection._selected.__wrapped__(action_proof=proof)
            self.assertIs(result, proof.selected.return_value)
            proof.finish.assert_called_once()
            for failure in ('candidate', 'cut'):
                proof.finish.reset_mock()
                candidate.return_value = {} if failure == 'candidate' else anchor
                cut.side_effect = [(1, 0), (2, 0)] if failure == 'cut' else None
                with self.assertRaises(PublicationUnavailable):
                    scoped_selection._selected.__wrapped__(action_proof=proof)
                proof.finish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
