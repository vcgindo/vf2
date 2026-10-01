"""Focused mechanics; canonical retained consumer parity is a separate proof."""
import os
import unittest
os.environ.setdefault('VF_SECRET_KEY','unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation import btr
from mta.presentation.btr_filters import BtrPredicate
from mta.presentation.context import PublicationUnavailable
from tests.test_btr_presentation import output


def payload(group,attribute,operator,value,**extra):
    return dict(filters={group:dict(filters=[dict(attributeName=attribute,operator=operator,value=value,**extra)])})


class BTRFilterTest(unittest.TestCase):
    def test_count_grid_E_column_distinction(self):
        data=output(); data['BPRStages'][0]['state']['vf_RationedReqReport'][0]['Stock']=3
        rows=btr.joined_rows(data,'tech'); request=payload('availabilityFilter','Stock','greaterthan','0')
        self.assertEqual(BtrPredicate(request,[],count=True)(rows[0]),1)
        with self.assertRaises(PublicationUnavailable): BtrPredicate(request,[],count=False)

    def test_category_is_raw_standard_LIKE_not_display(self):
        row=btr.joined_rows(output(),'tech')[0]
        self.assertEqual(BtrPredicate(payload('availabilityFilter','category','equalto','5'),[])(row),1)
        self.assertEqual(BtrPredicate(payload('availabilityFilter','category','equalto','SE'),[])(row),0)

    def test_colour_age_and_count(self):
        row=btr.joined_rows(output(),'tech')[0]
        self.assertEqual(BtrPredicate(payload('colorFilter','green','greaterthan','0',type='colorcount'),[])(row),1)
        self.assertEqual(BtrPredicate(payload('colorFilter','green','equalto','2',type='colorage'),[])(row),1)
        self.assertEqual(BtrPredicate(payload('colorFilter','black/red','greaterthan','0',type='colorage'),[])(row),0)

    def test_raw_custom_NULL_does_not_become_display_empty(self):
        row=btr.joined_rows(output(),'tech')[0]
        self.assertEqual(BtrPredicate(payload('customAttributeFilter','SKUAttr15','hasnovalue',''),[])(row),1)
        self.assertEqual(BtrPredicate(payload('customAttributeFilter','SKUAttr15','equalto',''),[])(row),0)

    def test_parent_join_applies_again_after_paged_keys(self):
        data=output(); data['BTRFinal'][0]['LocationAttributeData']=[dict(WHCode='LDC001',LocationType='LDC')]*2
        pred=BtrPredicate(payload('supplyChainFilter','forchildren','equalto','LDC'),data['BTRFinal'][0]['LocationAttributeData'])
        rows=btr.joined_rows(data,'tech'); selected=[r for r in rows for _ in range(pred(r))]
        self.assertEqual(len(selected),2)
        self.assertEqual(len(btr.project_rows(data,'tech',selected,('D90',),10,join_multiplicity=pred.join_multiplicity)),4)

    def test_group_OR_cross_attribute_AND(self):
        row=btr.joined_rows(output(),'tech')[0]; row['_sa']={'SL2':'Selected','SL3':'Leaf'}
        request=dict(filters=dict(productFilter=dict(filters=[
            dict(attributeName='p2',operator='equalto',value='Selected'),
            dict(attributeName='p2',operator='equalto',value='Other'),
            dict(attributeName='p3',operator='equalto',value='Leaf')])))
        self.assertEqual(BtrPredicate(request,[])(row),1)
        row['_sa']['SL3']='Different'; self.assertEqual(BtrPredicate(request,[])(row),0)

    def test_source_invalid_sql_not_repaired(self):
        for request in (payload('availabilityFilter','availability','equalto','1'),
                        payload('colorFilter','black/red','hasvalue','',type='colorcount'),
                        payload('productFilter','p9','equalto','x')):
            with self.assertRaises(PublicationUnavailable): BtrPredicate(request,[])


if __name__=='__main__': unittest.main()
