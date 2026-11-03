"""Producer transition evidence preserves typed occurrences and logical order."""
from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from mta.runtime.dated_history_delta import (
    Occurrence, Removal, RETIREMENT, producer_sort_key, transition_facts, transition_rows,
)
from mta.row_sequences import RecordRows


REJECTED = 'closing/importer/RejectedMaster'
NORM = 'closing/dbm/NormChangeLogTbl'
DAY = '2026-10-26'


def rejection(reason, day=DAY, description='Rejection'):
    return dict(SKUCode='5954', WhCode='DP010290', RejectionDate=day+'T04:05:06',
        ReasonCode=reason, ReasonDescription=description)


def retirement(day, event):
    return dict(SKUCode='5954', WhCode='DP010290', Norm=5, Event_Date=day, Event_Type=event)


def norm(reason, day=DAY):
    return dict(SKUCode='5954', WHCode='DP010290', OldNorm=123, NewNorm=82,
        NormChangeDate=day, NormChangeReason=reason)


def transition(opening, additions, *, removed=(), sorted_prefix=None):
    return dict(opening_count=len(opening), removed=list(removed), additions=additions,
        sorted_prefix=sorted_prefix)


class ProducerHistoryProjectionTests(TestCase):
    def test_importer_resorts_by_producer_json_then_keeps_validation_tail(self):
        old = rejection(7, '2026-10-25')
        future = rejection(7, '2026-10-27')
        master = rejection(1)
        daily = rejection(6)
        first_tail = rejection(144)
        second_tail = rejection(201)
        prior = [old, old, future, rejection(102, '2026-10-25')]
        added = [daily, master, first_tail, second_tail]
        changes = transition(prior, added, sorted_prefix=2)
        self.assertEqual(list(transition_rows(prior,changes,REJECTED)),
            [master,prior[-1],daily,old,old,future,first_tail,second_tail])
        self.assertIn(r'\u00e9', producer_sort_key(rejection(8,description='ré'),REJECTED))
        self.assertEqual(prior[0],prior[1])

    def test_retirement_successor_normalizes_bit_anchor_and_inserts_before_future(self):
        old = retirement('2026-10-25',False)
        future = retirement('2026-10-27',False)
        incoming = retirement(DAY,1)
        prior = [old,old,future]
        rows = list(transition_rows(prior,transition(prior,[incoming],sorted_prefix=1),RETIREMENT))
        self.assertEqual(rows,[retirement('2026-10-25',0)]*2+[incoming,retirement('2026-10-27',0)])
        self.assertTrue(all(type(row['Event_Type']) is int for row in rows))
        self.assertIs(old['Event_Type'],False)

    def test_retirement_reuse_sorts_unsorted_bit_anchor_without_insertions(self):
        from mta.application.persistent_master import static_tables
        old = retirement('2026-10-25',False)
        future = retirement('2026-10-27',False)
        before = [future,old,old]
        carried = list(transition_rows(before,transition(before,[],sorted_prefix=0),RETIREMENT))
        self.assertEqual(carried,[retirement('2026-10-25',0)]*2+[retirement('2026-10-27',0)])
        self.assertEqual(carried,static_tables({'importer':{'RetiredNormsTbl':before}})['RetiredNormsTbl'])
        added = retirement(DAY,1)
        self.assertEqual(list(transition_rows(carried,transition(carried,[added],sorted_prefix=1),RETIREMENT)),
            [retirement('2026-10-25',0)]*2+[added,retirement('2026-10-27',0)])

    def test_norm_removal_is_by_opening_ordinal_and_does_not_require_addition(self):
        before = [norm(102),norm(102),norm(None),norm(102,'2026-10-27'),norm(102,None)]
        changes = transition(before,[],removed=(1,))
        self.assertEqual(list(transition_rows(before,changes,NORM)),before[:1]+before[2:])
        change = transition(before,RecordRows(1,lambda:iter([norm(104)])),removed=(0,1))
        removed,facts,prefix = transition_facts(NORM,change,opening_count=len(before),
            today=date.fromisoformat(DAY),position=9)
        self.assertEqual(removed,{0,1})
        self.assertEqual(next(facts).occurrence,Occurrence(9,0))
        self.assertIsNone(prefix)
        self.assertEqual(list(transition_rows(before,change,NORM)),before[2:]+[norm(104)])

    def test_invalid_transition_cannot_drop_occurrences_or_invent_sort_rules(self):
        prior = [rejection(7)]
        for family,changes in (
                (REJECTED,transition(prior,[],removed=(0,),sorted_prefix=0)),
                (REJECTED,transition(prior,[],sorted_prefix=True)),
                (REJECTED,transition(prior,[rejection(6,'2026-10-27')],sorted_prefix=1)),
                (RETIREMENT,transition(prior,[retirement(DAY,1)],sorted_prefix=0)),
                (RETIREMENT,transition(prior,[retirement(DAY,1)])),
                (RETIREMENT,transition(prior,[retirement(DAY,False)],sorted_prefix=1)),
                (NORM,transition(prior,[],removed=(0,0))),
                (NORM,transition(prior,[],removed=(-1,))),
                (NORM,transition(prior,[],sorted_prefix=0)),
                (NORM,dict(transition(prior,[]),opening_count=0))):
            with self.subTest(family=family,changes=changes),self.assertRaises(ValueError):
                _removed,facts,_prefix = transition_facts(family,changes,opening_count=1,today=DAY,position=1)
                list(facts)

    def test_sql_order_retains_anchor_birth_order_and_sorts_successor_prefix(self):
        from mta.runtime.dated_history_reader import occurrence_order, occurrence_relation
        anchor = SimpleNamespace(position=0,initialization='init',
            body=dict(family=REJECTED,fields=[],sorted_prefix=None))
        successor = SimpleNamespace(position=4,initialization='init',
            body=dict(family=REJECTED,fields=[],sorted_prefix=2))
        self.assertEqual(occurrence_order(anchor),'born_position,vf_ordinal')
        sql,params,_ = occurrence_relation(successor)
        self.assertIn('history_sort_key',sql)
        self.assertEqual(params,['init',4])
        self.assertEqual(occurrence_order(successor),
            '(born_position=4 AND vf_ordinal>=2),CASE WHEN NOT (born_position=4 AND vf_ordinal>=2) '
            'THEN history_sort_key END COLLATE "C",born_position,vf_ordinal')

    def test_writer_closes_exact_prior_coordinate_and_refuses_reordered_readback(self):
        from contextlib import nullcontext
        from mta.runtime import dated_history_writer as writer

        before = [norm(102),norm(102),norm(None)]
        prior_coordinates = [(Occurrence(2,0),{}),(Occurrence(4,1),{}),(Occurrence(4,5),{})]
        parent = SimpleNamespace(identity='prior',body=dict(family=NORM,count=3))
        cut = SimpleNamespace(pk='cut',parent_id='prior',initialization_id='init',
            run_id='run',family=NORM,position=5)
        expected = [before[0],before[2]]
        change = transition(before,[],removed=(1,))
        for reordered in (False,True):
            readback = [(Occurrence(2,0),expected[0]),(Occurrence(4,5),expected[1])]
            if reordered:
                readback.reverse()
            with patch.object(writer,'connection',SimpleNamespace(in_atomic_block=True)), \
                    patch.object(writer.transaction,'atomic',side_effect=nullcontext), \
                    patch.object(writer,'iter_occurrences',side_effect=[
                        (row for row in prior_coordinates),(row for row in readback)]), \
                    patch.object(writer,'_flush') as flush, patch.object(writer,'_seal') as seal:
                if reordered:
                    with self.assertRaisesRegex(ValueError,'reconstructed successor'):
                        writer.write_transition(cut,parent,expected,today=DAY,transition=change)
                    seal.assert_not_called()
                else:
                    writer.write_transition(cut,parent,expected,today=DAY,transition=change)
                    seal.assert_called_once()
                flush.assert_called_once_with(cut,[Removal(Occurrence(4,1))])
