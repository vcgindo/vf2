"""DBM raw predicate mechanics; independent deployed SQL proof is separate."""
import os
import unittest
os.environ.setdefault('VF_SECRET_KEY','unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation.context import PublicationUnavailable
from mta.presentation.dbm_filters import dbm_predicate


def request(group,attribute,operator,value):
    return dict(filters={group:dict(filters=[dict(attributeName=attribute,operator=operator,value=value)])})


class DBMFilterTest(unittest.TestCase):
    state={'LocationAttributeData':[dict(WHCode='LDC001',LocationType='LDC')]*2}
    raw=(dict(SKUCode='337',WhCode='AG515802'),dict(Norm=220,ParentWhCode='LDC001'),
         dict(c1='B1 Product',SL2='Selected',c15=None),dict(LL2='Receiving'),{})

    def test_custom_only_gate_is_ignored(self):
        self.assertEqual(dbm_predicate(request('customAttributeFilter','SKUAttr1','invented','Missing'),self.state)(*self.raw),1)

    def test_empty_standard_group_activates_raw_custom_NULL(self):
        payload=request('customAttributeFilter','SKUAttr15','hasnovalue','')
        payload['filters']['productFilter']=dict(filters=[])
        self.assertEqual(dbm_predicate(payload,self.state)(*self.raw),1)
        payload['filters']['customAttributeFilter']['filters'][0].update(operator='equalto',value='')
        self.assertEqual(dbm_predicate(payload,self.state)(*self.raw),0)

    def test_norm_belongs_to_raw_master_and_group_AND(self):
        payload=request('availabilityFilter','norm','greaterthan','210')
        payload['filters']['productFilter']=dict(filters=[dict(attributeName='p2',operator='equalto',value='Selected')])
        self.assertEqual(dbm_predicate(payload,self.state)(*self.raw),1)
        payload['filters']['availabilityFilter']['filters'][0]['value']='300'
        self.assertEqual(dbm_predicate(payload,self.state)(*self.raw),0)

    def test_parent_inner_join_bag(self):
        self.assertEqual(dbm_predicate(request('supplyChainFilter','forchildren','equalto','LDC'),self.state)(*self.raw),2)

    def test_source_missing_columns_not_repaired(self):
        for attribute in ('stock','category','virtualnorm','availability'):
            with self.assertRaises(PublicationUnavailable):dbm_predicate(request('availabilityFilter',attribute,'equalto','1'),self.state)


if __name__=='__main__':unittest.main()
