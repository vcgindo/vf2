"""Finite inherited history ownership, not a same-content source lookup."""
from copy import deepcopy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.runtime import inherited_history_image as image


class InheritedHistoryOwnerTests(unittest.TestCase):
    def setUp(self):
        self.parent=SimpleNamespace(pk='parent',status='SUCCEEDED',output_digest='o'*64,input_digest='i'*64)
        self.run=SimpleNamespace(pk='child',predecessor_id='parent',predecessor=self.parent)
        self.cut=SimpleNamespace(initialization='init',run='parent',position=3,
            body=dict(family=image.FAMILY,input_digest='i'*64))
        self.frozen=dict(initialization_binding={'id':'init'},
                         lineage=dict(run_id='parent',output_digest='o'*64))

    def test_exact_own_predecessor_or_initialization_anchor(self):
        image._owner(self.run,self.cut,self.frozen)
        self.run.predecessor_id=None;self.cut.run=None;self.cut.position=0
        image._owner(self.run,self.cut,self.frozen)

    def test_same_content_does_not_authorize_another_owner(self):
        for field,value in (('initialization','other'),('run','other')):
            with self.subTest(field=field),patch.object(self.cut,field,value), \
                    self.assertRaisesRegex(ValueError,'opening owner'):
                image._owner(self.run,self.cut,self.frozen)
        for field,value in (('status','RUNNING'),('output_digest','x'*64),('input_digest','x'*64)):
            with self.subTest(field=field),patch.object(self.parent,field,value), \
                    self.assertRaisesRegex(ValueError,'accepted predecessor'):
                image._owner(self.run,self.cut,self.frozen)

    def test_anchor_and_family_are_not_interchangeable(self):
        self.run.predecessor_id=None;self.cut.run=None
        with self.assertRaisesRegex(ValueError,'initialization anchor'):
            image._owner(self.run,self.cut,self.frozen)
        self.cut.position=0;self.cut.body['family']='closing/dbm/OrderData'
        with self.assertRaisesRegex(ValueError,'opening owner'):
            image._owner(self.run,self.cut,self.frozen)

    def test_partial_persistence_metadata_cannot_stand_in_for_captured_lineage(self):
        partial={'initialization_binding':self.frozen['initialization_binding'],'profile':{}}
        with self.assertRaisesRegex(ValueError,'accepted predecessor'):
            image._owner(self.run,self.cut,partial)
        image._owner(self.run,self.cut,dict(partial,lineage=self.frozen['lineage']))


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Configured isolated Django/PG proof required')
class InheritedHistoryReferenceTests(unittest.TestCase):
    def setUp(self):
        InheritedHistoryOwnerTests.setUp(self)
        from mta.runtime import relational_state as typed
        self.typed=typed
        self.rows=[dict(SKUCode='s',WhCode='w',Type=5,OldNorm=123,NewNorm=82,SuggestionDate='2026-10-23'),
                   dict(SKUCode='s',WhCode='w',Type=None,OldNorm=123,NewNorm=None,SuggestionDate=None)]
        self.rows.append(deepcopy(self.rows[-1]))
        self.columns={n.casefold():(n,k) for n,k in typed.STORAGE_TABLES[image.TABLE]}
        self.path='phase/PRE_BPR/controls/suggestions_log'
        self.description=typed.describe_rows(self.rows,self.columns,self.path)
        self.cut.identity='cut';self.cut.root_digest='c'*64
        self.cut.body.update(fields=self.description[0]['fields'],count=3)

    def writer(self):
        from mta.runtime import dated_history_reader as reader
        self.enterContext(patch.object(image,'opening_cut',return_value=self.cut))
        self.load=self.enterContext(patch.object(reader,'load_cut',return_value=self.rows))
        return image.ReferenceWriter(self.run)

    def reference(self):
        return self.writer()(self.path,image.TABLE,self.description)

    def test_exact_typed_ordered_reference_preserves_duplicates_and_nulls(self):
        writer=self.writer()
        result=writer(self.path,image.TABLE,self.description)
        self.assertEqual(result['count'],3)
        self.assertEqual(result['digest'],self.description[0]['digest'])
        self.assertEqual(result['cut_id'],'cut')
        self.assertEqual(result['run_id'],'child')
        self.assertEqual(writer(self.path,image.TABLE,self.description),result)
        self.assertEqual(self.load.call_count,1)

    def test_changed_values_order_or_multiplicity_keep_physical_codec(self):
        writer=self.writer()
        changed=deepcopy(self.rows);changed[0]['NewNorm']=83
        for rows in (changed,list(reversed(self.rows)),self.rows[:2]):
            description=self.typed.describe_rows(rows,self.columns,self.path)
            self.assertIsNone(writer(self.path,image.TABLE,description))

    def test_unrelated_empty_or_current_dbm_population_cannot_reference_prior(self):
        writer=self.writer()
        for path in ('phase/DBM/dbm/SuggestionsLog','closing/dbm/SuggestionsLog',
                     'phase/PRE_BPR/controls/order_summary'):
            self.assertIsNone(writer(path,image.TABLE,self.description))
        self.load.assert_not_called()

    def test_reader_rejects_rebound_child_and_cut_digest(self):
        from mta.runtime import dated_history_reader as reader
        meta=self.reference()
        with patch.object(reader,'read_cut',return_value=self.cut),patch.object(image,'_frozen',return_value=self.frozen):
            self.assertIs(image.require_image(self.run,meta),self.cut)
            for key,value in (('run_id','other'),('cut_digest','d'*64),('image','closing/dbm/SuggestionsLog')):
                wrong=dict(meta,**{key:value})
                with self.subTest(key=key),self.assertRaises(ValueError):image.require_image(self.run,wrong)

    def test_audit_rejects_changed_payload_even_when_count_is_equal(self):
        from mta.runtime import dated_history_reader as reader,dated_history_audit as audit
        meta=self.reference()
        changed=deepcopy(self.rows);changed[0]['NewNorm']=83
        with patch.object(image,'require_image',return_value=self.cut), \
                patch.object(audit,'audit_cut'),patch.object(reader,'iter_occurrences',return_value=iter(enumerate(changed))), \
                self.assertRaisesRegex(ValueError,'typed content'):
            list(image.iter_image(self.run,meta,audit=True))
