"""The narrow action reader preserves exact typed state and rejects bad owners."""
from contextlib import ExitStack
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
import os
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()

from mta.runtime import scoped_actions as actions, phase_state
from mta.serialization import storage


class ActionSubsetTests(unittest.TestCase):
    def setUp(self):
        self.run=NS(pk='run',production_manifest={'ingestion_preparation':{'bpr_consumer_cut':{}}})
        self.rows={
            'DBMMaster':[{'SKUCode':'A','WhCode':'W','Norm':12}],
            'Suggestions':[{'SKUCode':'A','WhCode':'W','Type':None,'NewNorm':None}]*2,
            'NormAcceptanceTbl':[],
            'NormsInSleepModeTbl':[{'SKUCode':'A','WhCode':'W','StartDate':'2026-10-25'}],
        }
        images={};bindings={}
        for name,rows in self.rows.items():
            logical='phase/DBM/dbm/'+name
            fields=[[key,key,'int' if key in ('Norm','Type','NewNorm') else 'str']
                    for key in (rows[0] if rows else ())]
            images[logical]=dict(image=logical,table='DBM/'+name,count=len(rows),fields=fields,digest='a'*64)
            bindings[name]={'image':logical}
        self.prefix=[]
        for phase in ('PRE_BPR','BPR','DBM'):
            manifest=dict(schema=phase_state.SCHEMA,phase=phase,references={'frozen':'identity'},
                          metadata={},images=images,state={'final_dbm':bindings})
            self.prefix.append(NS(pk=phase,digest=phase,phase=phase,snapshot=NS(manifest=manifest)))
        self.receipt=self.prefix[-1]
        stack=self.enterContext(ExitStack())
        stack.enter_context(patch.object(actions,'connection',NS(in_atomic_block=True)))
        self.input=stack.enter_context(patch('mta.runtime.input_reader.read_input',return_value={}))
        self.accepted=stack.enter_context(patch('mta.runtime.scoped_final.accepted_prefix',return_value=(self.prefix,NS())))
        self.load=stack.enter_context(patch('mta.runtime.relational_state.load_image',
            side_effect=lambda run,item,**kwargs:deepcopy(self.rows[item['table'].split('/')[1]])))

    def test_exact_four_tables_keep_nulls_duplicates_empty_controls_and_field_roster(self):
        state,initial=actions._dbm_action_base(self.run,self.receipt)
        self.assertEqual(state,storage(self.rows));self.assertEqual(initial,0)
        self.assertEqual(self.load.call_count,4)
        self.input.assert_called_once_with(self.run,components=())
        self.accepted.assert_called_once_with(self.run,lock_capture=False)
        for call in self.load.call_args_list:
            self.assertIs(call.kwargs['table_registry'],phase_state.REGISTRY)

    def test_missing_or_malformed_table_bindings_are_denied(self):
        original=deepcopy(self.receipt.snapshot.manifest)
        def alias(m):m['state']['final_dbm']['Suggestions']={'image':'phase/BPR/dbm/Suggestions'}
        def table(m):m['images']['phase/DBM/dbm/Suggestions']['table']='DBM/DBMMaster'
        def count(m):m['images']['phase/DBM/dbm/Suggestions']['count']=True
        def fields(m):m['images']['phase/DBM/dbm/Suggestions']['fields']=[['SKUCode','WhCode','str']]
        def duplicate(m):m['images']['phase/DBM/dbm/Suggestions']['fields']=[['SKUCode','SKUCode','str']]*2
        def checksum(m):m['images']['phase/DBM/dbm/Suggestions']['digest']='bad'
        for change in (alias,table,count,fields,duplicate,checksum):
            with self.subTest(change=change.__name__):
                self.receipt.snapshot.manifest=deepcopy(original)
                change(self.receipt.snapshot.manifest)
                with self.assertRaises(ValueError):actions._dbm_action_base(self.run,self.receipt)

    def test_prefix_schema_dependencies_revision_and_owner_are_checked(self):
        for key,value in (('schema','bad'),('phase','BPR'),('references',{'other':'owner'})):
            with self.subTest(key=key):
                old=self.receipt.snapshot.manifest[key]
                self.receipt.snapshot.manifest[key]=value
                with self.assertRaises(ValueError):actions._dbm_action_base(self.run,self.receipt)
                self.receipt.snapshot.manifest[key]=old
        for value in (True,-1,'4'):
            self.receipt.snapshot.manifest['metadata']['action_revision']=value
            with self.assertRaises(ValueError):actions._dbm_action_base(self.run,self.receipt)
        with self.assertRaisesRegex(ValueError,'accepted owner'):
            actions._dbm_action_base(self.run,NS(pk='foreign',digest='foreign'))

    def test_failed_input_prefix_or_typed_checksum_never_returns_state(self):
        for mock in (self.input,self.accepted,self.load):
            with self.subTest(boundary=mock):
                prior=mock.side_effect;mock.side_effect=ValueError('corrupt owner')
                with self.assertRaisesRegex(ValueError,'corrupt owner'):
                    actions._dbm_action_base(self.run,self.receipt)
                mock.side_effect=prior

    def test_requires_transaction(self):
        with patch.object(actions,'connection',NS(in_atomic_block=False)):
            with self.assertRaisesRegex(ValueError,'owning transaction'):
                actions._dbm_action_base(self.run,self.receipt)
        self.input.assert_not_called()

    def test_each_chain_verification_starts_with_fresh_immutable_base(self):
        def consume(run,receipt,state,initial,*,expected_revision):
            self.assertEqual(state,storage(self.rows));self.assertEqual(initial,0)
            state['Suggestions'].clear()
            return expected_revision
        with patch.object(actions,'_state_after',side_effect=consume), \
                patch.object(actions,'restore',side_effect=AssertionError('Full restore')):
            reader=actions._action_reader(self.run,self.receipt)
            self.assertEqual(reader(4),4);self.assertEqual(reader(5),5)
        self.assertEqual(self.load.call_count,4)

    def test_bpr_and_uncertified_component_paths_keep_full_restore(self):
        for phase,manifest in (('BPR',self.run.production_manifest),('DBM',{})):
            with self.subTest(phase=phase),patch.object(actions,'restore',return_value=('phase',None)) as restore, \
                    patch.object(actions,'state_after',return_value='state') as state:
                self.run.production_manifest=manifest
                receipt=NS(phase=phase)
                reader=actions._action_reader(self.run,receipt)
                self.assertEqual(reader(7),'state')
                restore.assert_called_once_with(self.run,receipt)
                state.assert_called_once_with(self.run,receipt,'phase',expected_revision=7)


if __name__=='__main__':unittest.main()
