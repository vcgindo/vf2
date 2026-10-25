"""Direct accepted pre-DBM readers, compared with canonical paused action state."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

from tests import test_scoped_actions_postgresql as action_fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class ScopedDbmTests(unittest.TestCase):
    for name in ('setUp', 'rollback', 'owner', 'accept', 'pause_bpr', 'state', 'action'):
        locals()[name] = getattr(action_fixtures.ScopedActionTests, name)

    def binding(self, revision=0, **changes):
        from mta.presentation.scoped_dbm import bind
        arguments = dict(expected_digest=self.bpr.digest, action_revision=revision)
        arguments.update(changes)
        return bind(self.bpr.pk, **arguments)

    def test_direct_state_grid_and_null_duplicate_pair_without_phase_reconstruction(self):
        from contextlib import ExitStack
        from django.db import connection
        from mta.runtime.scoped_actions import TABLES
        from mta.presentation.dbm import dbm_rows
        from mta.presentation.scoped_dbm import ATTRIBUTES
        from tests import test_h3_daily_integration as supplied
        opening = supplied.frame()
        opening['opening']['state']['dbm']['ReasonCodes'] = [dict(Id=1, Reason='Declared component Rule 1')]
        with patch.object(supplied, 'frame', return_value=opening):
            self.pause_bpr(duplicates=True)
        expected = deepcopy(self.base_state)
        from mta.runtime.scoped_actions import restore
        phase, _ = restore(self.run, self.bpr)
        expected['ReasonCodes'] = deepcopy(phase.context.prior['dbm']['ReasonCodes'])
        expected.update({name: deepcopy(phase.importer[name]) for name in ATTRIBUTES})
        for row in expected['SkuLocAttributeData']:
            if row['NonNMS'] is not None:
                row['NonNMS'] = bool(row['NonNMS'])
        before = list(self.run.phase_acceptances.values_list('id', 'digest'))

        def readonly(execute, sql, params, many, context):
            self.assertEqual(sql.lstrip().split(None, 1)[0].upper(), 'SELECT')
            return execute(sql, params, many, context)

        with ExitStack() as stack:
            for target in ('mta.runtime.scoped_actions.restore', 'mta.runtime.phase_state.read',
                           'mta.temporal.chain.produce_bpr', 'mta.temporal.chain.produce_dbm'):
                stack.enter_context(patch(target, side_effect=AssertionError('Reader reconstruction/calculation')))
            stack.enter_context(connection.execute_wrapper(readonly))
            current = self.binding()
        self.assertEqual(current.dbm, expected)
        self.assertEqual(dbm_rows(current.dbm), dbm_rows(expected))
        self.assertEqual(len(dbm_rows(current.dbm)), 1)
        self.assertEqual(len(current.dbm['Suggestions']), 2)
        self.assertIsNone(current.dbm['Suggestions'][1]['Type'])
        self.assertIsNone(current.dbm['Suggestions'][1]['NewNorm'])
        self.assertEqual({name: current.dbm[name] for name in TABLES}, self.base_state)
        self.assertEqual(list(self.run.phase_acceptances.values_list('id', 'digest')), before)
        self.assertFalse(self.run.commands.exists())

    def test_actual_apply_then_sleep_revisions_equal_existing_complete_action_validation(self):
        from mta.runtime.scoped_actions import TABLES
        from mta.presentation.context import PublicationUnavailable
        self.pause_bpr()
        old = self.binding()
        event = self.action('APPLY', expected_revision=0, key='read-apply')
        with self.assertRaises(PublicationUnavailable):
            self.binding()
        expected = self.state(self.bpr, event.pk)
        with patch('mta.runtime.scoped_actions.restore', side_effect=AssertionError('Reader restore')):
            current = self.binding(event.pk)
        self.assertEqual({name: current.dbm[name] for name in TABLES}, expected)
        sleep = self.action('SLEEP', expected_revision=event.pk, key='read-sleep')
        with self.assertRaises(PublicationUnavailable):
            self.binding(event.pk)
        expected = self.state(self.bpr, sleep.pk)
        with patch('mta.runtime.scoped_actions.restore', side_effect=AssertionError('Reader restore')):
            current = self.binding(sleep.pk)
        self.assertEqual({name: current.dbm[name] for name in TABLES}, expected)
        self.assertEqual({name: old.dbm[name] for name in TABLES}, self.base_state)

    def test_wrong_phase_digest_revision_and_missing_inherited_reference_denied(self):
        from mta.presentation import scoped_dbm, scoped_inherited_btr
        from mta.presentation.context import PublicationUnavailable
        self.pause_bpr()
        for change in (dict(expected_digest='f' * 64), dict(action_revision=True),
                       dict(action_revision=-1), dict(action_revision=1)):
            with self.subTest(change=change), self.assertRaises(PublicationUnavailable):
                self.binding(**change)
        original = scoped_inherited_btr._node
        def missing(owner, path):
            return None if path.endswith('/dbm/ReasonCodes') else original(owner, path)
        with patch.object(scoped_inherited_btr, '_node', side_effect=missing), \
                self.assertRaises(PublicationUnavailable):
            self.binding()
        from copy import copy
        from uuid import uuid4
        def foreign(owner, path):
            found = original(owner, path)
            if found is not None and path.endswith('/dbm/ReasonCodes'):
                other = copy(found[0]); other.pk = uuid4()
                return other, found[1]
            return found
        with patch.object(scoped_inherited_btr, '_node', side_effect=foreign), \
                self.assertRaises(PublicationUnavailable):
            self.binding()
        parent = self.bpr.snapshot.parent.acceptance
        with self.assertRaises(PublicationUnavailable):
            scoped_dbm.bind(parent.pk, expected_digest=parent.digest, action_revision=0)

    def test_owned_empty_reason_codes_are_not_missing_or_synthesised(self):
        from tests import test_h3_daily_integration as supplied
        from mta.presentation.dbm import dbm_rows
        opening = supplied.frame()
        opening['opening']['state']['dbm']['ReasonCodes'] = []
        with patch.object(supplied, 'frame', return_value=opening):
            self.pause_bpr()
        current = self.binding()
        self.assertEqual(current.dbm['ReasonCodes'], [])
        self.assertTrue(current.dbm['Suggestions'])
        self.assertEqual(dbm_rows(current.dbm), [])
