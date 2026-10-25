"""Actual pre-BTR typed reader and pending actions, on rollback-owned fixtures.

This qualifies the consumer, not native initialization, selection or legacy parity.
"""
from contextlib import ExitStack
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

from tests import test_scoped_actions_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedDbmStopTests(unittest.TestCase):
    for name in ('setUp','rollback','owner','accept','pause_bpr','state','action'):
        locals()[name] = getattr(fixtures.ScopedActionTests,name)

    def start(self):
        from tests import test_h3_daily_integration as supplied
        opening = supplied.frame()
        opening['opening']['state']['dbm']['ReasonCodes'] = [dict(Id=1,Reason='Declared Rule 1')]
        with patch.object(supplied,'frame',return_value=opening):
            self.pause_bpr(scope='UptoDBM')

    def binding(self, revision=0, **changes):
        from mta.presentation.scoped_dbm_stop import bind
        return bind(self.bpr.pk, **dict(expected_digest=self.bpr.digest,
            action_revision=revision, **changes))

    def expected(self, revision=0):
        from mta.runtime.scoped_actions import restore, state_after
        from mta.presentation.scoped_dbm import ATTRIBUTES
        phase, _ = restore(self.run,self.bpr)
        state = state_after(self.run,self.bpr,phase,expected_revision=revision)
        state['ReasonCodes'] = deepcopy(phase.final_dbm['ReasonCodes'])
        state.update({name:deepcopy(phase.importer[name]) for name in ATTRIBUTES})
        for row in state['SkuLocAttributeData']:
            if row['NonNMS'] is not None: row['NonNMS'] = bool(row['NonNMS'])
        from mta.serialization import storage
        return storage(state)

    def test_nonempty_dbm_and_grid_equal_canonical_pre_btr_without_restore_or_writes(self):
        from django.db import connection
        from mta.presentation.dbm import dbm_rows
        from mta.serialization import storage
        self.start()
        expected = self.expected()
        self.assertTrue(expected['Suggestions'])
        self.assertTrue(dbm_rows(expected))
        before = list(self.run.phase_acceptances.order_by('accepted_at').values_list('id','digest'))
        def readonly(execute, sql, params, many, context):
            self.assertEqual(sql.lstrip().split(None,1)[0].upper(),'SELECT')
            return execute(sql,params,many,context)
        with ExitStack() as stack:
            for name in ('mta.runtime.scoped_actions.restore','mta.runtime.phase_state.read',
                         'mta.temporal.chain.produce_dbm','mta.temporal.chain.produce_btr'):
                stack.enter_context(patch(name,side_effect=AssertionError('UI reconstruction/calculation forbidden')))
            stack.enter_context(connection.execute_wrapper(readonly))
            actual = self.binding()
            self.assertEqual(storage(actual.dbm),expected)
            self.assertEqual(dbm_rows(actual.dbm),dbm_rows(expected))
        self.assertEqual(list(self.run.phase_acceptances.order_by('accepted_at').values_list('id','digest')),before)

    def test_apply_and_sleep_read_exact_pending_state_without_dbm_consumer_replay(self):
        from mta.serialization import storage
        from mta.presentation.context import PublicationUnavailable
        self.start()
        apply = self.action('APPLY',key='pre-btr-apply')
        after_apply = self.binding(apply.pk)
        self.assertEqual(storage(after_apply.dbm),self.expected(apply.pk))
        self.assertEqual(after_apply.dbm['DBMMaster'],self.base_state['DBMMaster'])
        self.assertTrue(after_apply.dbm['NormAcceptanceTbl'])
        sleep = self.action('SLEEP',expected_revision=apply.pk,key='pre-btr-sleep')
        after_sleep = self.binding(sleep.pk)
        self.assertEqual(storage(after_sleep.dbm),self.expected(sleep.pk))
        self.assertTrue(after_sleep.dbm['NormsInSleepModeTbl'])
        self.assertFalse([row for row in after_sleep.dbm['Suggestions']
                          if [row['SKUCode'],row['WhCode']]==self.selected[0]])
        with self.assertRaises(PublicationUnavailable): self.binding(apply.pk)
        self.assertEqual(self.run.phase_acceptances.filter(phase='DBM').count(),1)

    def test_bpr_parent_bad_digest_or_changed_head_cannot_masquerade_as_dbm(self):
        from mta.presentation.scoped_dbm_stop import bind
        from mta.presentation.context import PublicationUnavailable
        self.start()
        parent = self.bpr.snapshot.parent.acceptance
        with self.assertRaises(PublicationUnavailable):
            bind(parent.pk,expected_digest=parent.digest,action_revision=0)
        with self.assertRaises(PublicationUnavailable):
            bind(self.bpr.pk,expected_digest='f'*64,action_revision=0)
        with patch('mta.runtime.scope_execution.head',return_value=('DAY_FINAL','d'*64)):
            with self.assertRaises(PublicationUnavailable): self.binding()


if __name__=='__main__': unittest.main()
