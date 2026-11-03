"""Reusing a prepared graph must still reject every live selection change."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
import unittest
from contextlib import ExitStack
from copy import deepcopy
from types import SimpleNamespace as NS
from uuid import uuid4
from unittest.mock import patch
from django.test import override_settings
from mta.presentation import request_scope, scoped_selection, scoped_view
from mta.presentation.context import PublicationUnavailable
from mta.runtime.models import CalculationRun, ScopeReadReference
from test_remark_validation_scope import Database


class PreparedSelectionTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.database = Database()
        self.stack.enter_context(patch('django.db.connection', self.database))
        self.run = CalculationRun(id=uuid4())
        self.row = ScopeReadReference(id=uuid4(), digest='sealed', metadata={'binding': 'original'})
        self.row._state.adding = False; self.row._state.db = 'default'
        self.view = scoped_view.ViewBinding(deepcopy(self.row), None, None, None, None)
        self.anchor = dict(schema=scoped_selection.SCHEMA, run_id=str(self.run.pk),
                           phase_id=str(uuid4()), recipe_digest='recipe')
        self.stack.enter_context(override_settings(VF_MTA_PHASE_SELECTION_FILE='owned',
            VF_MTA_PHASE_SELECTION=self.anchor, VF_MTA_SELECTION_FILE='',
            VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST=''))
        self.read_anchor = self.stack.enter_context(patch.object(scoped_selection, 'read', return_value=self.anchor))
        self.cut = self.stack.enter_context(patch.object(scoped_selection, '_cut', return_value=(7, 3)))
        self.stack.enter_context(patch.object(CalculationRun.objects, 'get', return_value=self.run))
        self.stack.enter_context(patch('mta.runtime.input_reader.read_input', return_value={}))
        self.recipe = self.stack.enter_context(patch.object(scoped_selection, 'recipe_for_run', return_value='recipe'))
        self.stack.enter_context(patch.object(scoped_view, '_configuration', return_value=({}, 'config')))
        self.stack.enter_context(patch.object(scoped_view, 'recipe_for_configuration', return_value='reference'))
        self.rows = self.stack.enter_context(patch.object(ScopeReadReference.objects, 'filter', return_value=[self.row]))
        self.bind = self.stack.enter_context(patch.object(scoped_view, 'bind', return_value=self.view))
        self.candidate = self.stack.enter_context(patch.object(scoped_selection, 'candidate', return_value=self.anchor))

    def selected(self):
        with request_scope.remark_validation(): return scoped_selection._selected(prepared=self.view)

    def test_prepared_graph_is_reused_but_current_row_permissions_and_cut_are_rechecked(self):
        self.assertIs(self.selected(), self.view)
        self.bind.assert_not_called()
        self.rows.assert_called_once(); self.candidate.assert_called_once_with(self.view)
        self.assertEqual(self.cut.call_count, 2)
        # Normal requests still bind independently.
        self.assertIs(scoped_selection._selected(), self.view)
        self.bind.assert_called_once()

    def test_current_reference_must_be_unique_and_every_stored_field_must_match(self):
        for rows in ([], [self.row, self.row]):
            self.rows.return_value = rows
            with self.assertRaisesRegex(PublicationUnavailable, 'missing_or_ambiguous'): self.selected()
        self.rows.return_value = [self.row]
        for field, value in (('digest', 'changed'), ('metadata', {'binding': 'changed'}),
                             ('report_generation_id', uuid4())):
            previous = getattr(self.row, field); setattr(self.row, field, value)
            with self.assertRaisesRegex(PublicationUnavailable, 'not_current'): self.selected()
            setattr(self.row, field, previous)
        self.bind.assert_not_called()

    def test_anchor_recipe_permissions_and_final_revision_changes_still_abort(self):
        self.read_anchor.return_value = dict(self.anchor, phase_id='changed')
        with self.assertRaisesRegex(PublicationUnavailable, 'restart_required'): self.selected()
        self.read_anchor.return_value = self.anchor
        self.recipe.return_value = 'changed'
        with self.assertRaisesRegex(PublicationUnavailable, 'recipe_differs'): self.selected()
        self.recipe.return_value = 'recipe'
        self.candidate.return_value = dict(self.anchor, permissions_sha256='changed')
        with self.assertRaisesRegex(PublicationUnavailable, 'identity_changed'): self.selected()
        self.candidate.return_value = self.anchor; self.cut.side_effect = [(7, 3), (8, 3)]
        with self.assertRaisesRegex(PublicationUnavailable, 'reference_changed'): self.selected()

    def test_reuse_requires_owning_validation_transaction_and_persisted_default_reference(self):
        with self.assertRaises(PublicationUnavailable): scoped_selection._selected(prepared=self.view)
        for adding, alias in ((True, 'default'), (False, 'other')):
            self.view.reference._state.adding = adding; self.view.reference._state.db = alias
            with self.assertRaisesRegex(PublicationUnavailable, 'owner_transaction'): self.selected()


if __name__ == '__main__': unittest.main()
