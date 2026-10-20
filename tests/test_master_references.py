"""Exact canonical-capture ownership; no database or calculation invocation."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','master-reference-unit')
import django
django.setup()
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock,patch
from uuid import uuid4
from mta.runtime.run_input_references import owners
from mta.runtime.ingestion_models import MasterInputRevision

PATH='input/mdm_input/rows/sku/attributes'

class MasterReferenceTests(TestCase):
    def make(self,rows):
        return {'opening':None,'mdm_input':{'rows':{'sku':{'attributes':rows}}}}

    def select(self,current,previous,*,flatten=False):
        init=SimpleNamespace(pk=uuid4(),input_manifest_digest='a'*64,input_digest='b'*64)
        original=dict(kind='RUN',owner_id=str(uuid4()),path=PATH,
            manifest_digest='c'*64,content_digest='d'*64)
        parent=SimpleNamespace(pk=uuid4(),input_manifest_digest='e'*64,input_digest='f'*64,
            input_payload={'owner_references':{PATH:original}})
        revision=SimpleNamespace(run_id=uuid4(),run=SimpleNamespace(pk=uuid4()))
        query=Mock();query.get.return_value=revision
        def node(_manifest,path):
            if path!=PATH:raise ValueError('absent optional component')
            return {'owner_reference':PATH} if flatten else {'shape':['dict',[]]}
        with patch.object(MasterInputRevision.objects,'select_related',return_value=query), \
                patch('mta.runtime.run_input_references._node_at',side_effect=node), \
                patch('mta.runtime.input_reader.read_input',return_value=self.make(previous)):
            result=owners(init,self.make(current),uuid4(),unchanged=True,parent=parent)
        return result,parent,original

    def test_matching_current_capture_uses_direct_parent_physical_owner(self):
        rows=[{'id':1,'SKUCode':'S1','Weight':None},{'id':2,'SKUCode':'S1','Weight':'1.000'}]
        result,parent,_=self.select(rows,deepcopy(rows))
        self.assertEqual(result[PATH]['owner_id'],str(parent.pk))
        self.assertEqual(result[PATH]['content_digest'],parent.input_digest)

    def test_first_normalization_change_is_captured_instead_of_referencing_old_values(self):
        result,_,_=self.select([{'id':1,'c1':''}],[{'id':1,'c1':None}])
        self.assertNotIn(PATH,result)
        self.assertIn('input/profile',result)

    def test_order_or_duplicate_identity_change_cannot_reuse_old_capture(self):
        rows=[{'id':1,'value':None},{'id':2,'value':None}]
        result,_,_=self.select(rows,list(reversed(rows)))
        self.assertNotIn(PATH,result)

    def test_equal_reference_flattens_to_original_physical_owner(self):
        rows=[{'id':1,'SKUCode':'S1'}]
        result,_,original=self.select(rows,rows,flatten=True)
        self.assertEqual(result[PATH],original)
