"""Actual record/rollback checks for one verification per stored transition."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

from tests import test_scoped_actions_postgresql as action_tests


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedActionTailPostgresTests(unittest.TestCase):
    for name in ('setUp','rollback','owner','accept','pause_bpr','state','action'):
        locals()[name]=getattr(action_tests.ScopedActionTests,name)

    def test_apply_sleep_each_prior_transition_checked_once_then_only_new_tail(self):
        from mta.runtime import scoped_actions as actions
        self.pause_bpr(duplicates=True)
        with patch.object(actions,'_checked_event',wraps=actions._checked_event) as checked:
            apply=self.action('APPLY')
            self.assertEqual([call.args[-1].pk for call in checked.call_args_list],[apply.pk])
        applied=self.state(self.bpr,apply.pk)
        with patch.object(actions,'_checked_event',wraps=actions._checked_event) as checked:
            sleep=self.action('SLEEP',expected_revision=apply.pk,key='sleep-tail')
            self.assertEqual([call.args[-1].pk for call in checked.call_args_list],[apply.pk,sleep.pk])
        after=self.state(self.bpr,sleep.pk)
        self.assertEqual(after['DBMMaster'],self.base_state['DBMMaster'])
        self.assertEqual(after['NormAcceptanceTbl'],applied['NormAcceptanceTbl'])
        self.assertEqual(len(after['NormsInSleepModeTbl']),len(applied['NormsInSleepModeTbl'])+2)
        self.assertFalse([row for row in after['Suggestions']
                          if [row['SKUCode'],row['WhCode']]==self.selected[0]])
        # Exact retry uses the original parent identity, with no new event/read.
        with patch.object(actions,'_checked_event',side_effect=AssertionError('retry replay')):
            self.assertEqual(self.action('SLEEP',expected_revision=apply.pk,key='sleep-tail').pk,sleep.pk)

    def test_late_typed_tail_corruption_rolls_back_new_event_and_retains_prior(self):
        from mta.runtime import scoped_actions as actions,relational_state as typed
        from mta.runtime.models import RunCommand
        self.pause_bpr(duplicates=True)
        apply=self.action('APPLY')
        before=self.state(self.bpr,apply.pk)
        from django.db import connection
        def image_counts():
            with connection.cursor() as cursor:
                counts=[]
                for table in ('dbm_normacceptancetbl','dbm_normsinsleepmodetbl','dbm_suggestions'):
                    cursor.execute('SELECT count(*) FROM mta_state.'+table+
                                   " WHERE vf_run_id=%s AND vf_image LIKE 'action/%%'",[self.run.pk])
                    counts.append(cursor.fetchone()[0])
                return counts
        counts_before=image_counts()
        original=typed.load_image
        def corrupt(run,image,*args,**kwargs):
            rows=original(run,image,*args,**kwargs)
            if (image['image'].startswith('action/')
                    and image['image']!='action/'+str(apply.pk)+'/NormAcceptanceTbl'
                    and image['table']=='DBM/NormsInSleepModeTbl'):
                rows=deepcopy(rows)
                rows[-1]['StartDate']='2037-04-11'
            return rows
        with patch.object(typed,'load_image',side_effect=corrupt), \
                self.assertRaisesRegex(ValueError,'canonical typed result'):
            self.action('SLEEP',expected_revision=apply.pk,key='sleep-tail')
        self.assertEqual(list(RunCommand.objects.filter(run=self.run).values_list('pk',flat=True)),[apply.pk])
        self.assertEqual(actions.revision(self.run),apply.pk)
        self.assertEqual(image_counts(),counts_before)
        self.assertEqual(self.state(self.bpr,apply.pk),before)
        retry=self.action('SLEEP',expected_revision=apply.pk,key='sleep-tail')
        self.assertTrue(retry.state_sealed)
        self.assertEqual(retry.scope_parent_revision,apply.pk)
