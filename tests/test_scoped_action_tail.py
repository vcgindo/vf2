"""Persisted action-tail verification from an independently known before-state."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.serialization import digest
from mta.runtime.scoped_actions import _checked_event, _require_revision


class ScopedActionTailTests(unittest.TestCase):
    def setUp(self):
        self.run=SimpleNamespace(pk='run')
        self.phase=SimpleNamespace(pk='phase')
        self.before=dict(DBMMaster=[dict(SKUCode='s',WhCode='w',Norm=123)],
            Suggestions=[dict(SKUCode='s',WhCode='w',Type=5,NewNorm=82),
                         dict(SKUCode='s',WhCode='w',Type=None,NewNorm=None)],
            NormAcceptanceTbl=[],NormsInSleepModeTbl=[])
        self.after=deepcopy(self.before)
        self.after['NormAcceptanceTbl']=[dict(SKUCode='s',WhCode='w',OldNorm=123,
            NewNorm=value,AcceptanceDate='2026-10-24') for value in (82,None)]
        payload=dict(operation='APPLY',selected=[['s','w']],
                     timestamp='2026-10-24T10:00:00',actor='test')
        self.event=SimpleNamespace(pk=42,run_id='run',phase_acceptance_id='phase',
            state_sealed=True,payload=payload,digest=digest(payload),scope_parent_revision=7,
            before_digest=digest(self.before),after_digest=digest(self.after),
            state_manifest={'NormAcceptanceTbl':dict(image='action/42/NormAcceptanceTbl',
                                                     table='DBM/NormAcceptanceTbl')})

    def verify(self,rows=None):
        state=deepcopy(self.before)
        with patch('mta.runtime.relational_state.load_image',
                   return_value=deepcopy(self.after['NormAcceptanceTbl'] if rows is None else rows)) as read:
            _checked_event(self.run,self.phase,state,7,self.event)
        return state,read.call_count

    def test_positive_duplicate_null_result_reads_actual_typed_tail(self):
        state,count=self.verify()
        self.assertEqual(state,self.after)
        self.assertEqual(count,1)
        self.assertEqual(self.before['NormAcceptanceTbl'],[])

    def test_wrong_owner_parent_seal_or_payload_is_refused_before_read(self):
        for field,value in (('run_id','other'),('phase_acceptance_id','other'),
                            ('scope_parent_revision',6),('state_sealed',False),
                            ('digest','0'*64),('before_digest','0'*64)):
            with self.subTest(field=field),patch.object(self.event,field,value), \
                    patch('mta.runtime.relational_state.load_image') as read:
                with self.assertRaisesRegex(ValueError,'chain or typed owner'):
                    _checked_event(self.run,self.phase,deepcopy(self.before),7,self.event)
                read.assert_not_called()

    def test_wrong_typed_image_owner_is_refused(self):
        self.event.state_manifest['NormAcceptanceTbl']['image']='action/41/NormAcceptanceTbl'
        with self.assertRaisesRegex(ValueError,'image identity'):self.verify()

    def test_stored_payload_corruption_is_refused_even_with_matching_digest(self):
        rows=deepcopy(self.after['NormAcceptanceTbl'])
        rows[0]['NewNorm']=83
        changed=dict(self.after,NormAcceptanceTbl=rows)
        self.event.after_digest=digest(changed)
        with self.assertRaisesRegex(ValueError,'canonical typed result'):self.verify(rows)

    def test_missing_duplicate_and_changed_order_are_refused(self):
        rows=self.after['NormAcceptanceTbl']
        for changed in (rows[:1],list(reversed(rows))):
            with self.subTest(rows=changed),self.assertRaisesRegex(ValueError,'canonical typed result'):
                self.verify(changed)

    def test_final_revision_rechecks_database_head_and_integer_type(self):
        with patch('mta.runtime.scoped_actions.revision',return_value=42):
            _require_revision(self.run,42,42)
            for current,expected in ((41,42),(42,True),(42,43)):
                with self.assertRaisesRegex(ValueError,'revision changed'):
                    _require_revision(self.run,current,expected)
        with patch('mta.runtime.scoped_actions.revision',return_value=43), \
                self.assertRaisesRegex(ValueError,'revision changed'):
            _require_revision(self.run,42,42)


if __name__=='__main__':unittest.main()
