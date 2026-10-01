"""Predicate/multiplicity unit tests; independent parity is a separate receipt."""
from copy import deepcopy
from decimal import Decimal
import os
import unittest

os.environ.setdefault('VF_SECRET_KEY','unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr_filters import compare, rrr_predicate
from tests.test_rrr_presentation import RrrProjectionTest
from mta.presentation.rrr import selected_rows


class RrrFilterTest(unittest.TestCase):
    def predicate(self,groups,importer=None):
        return rrr_predicate(dict(filters={g:dict(filters=items) for g,items in groups.items()}),
                             importer or {'LocationAttributeData':[]})

    def item(self,attribute,operator,value):
        return dict(attributeName=attribute,operator=operator,value=value)

    def test_group_OR_and_cross_group_AND(self):
        pred=self.predicate({'productFilter':[self.item('p2','equalto','Selected'),self.item('p2','equalto','Other')],
            'locationFilter':[self.item('l2','equalto','Receiving')]})
        self.assertEqual(pred({}, {}, {'SL2':'Selected'}, {'LL2':'Receiving'}),1)
        self.assertEqual(pred({}, {}, {'SL2':'Other'}, {'LL2':'Receiving'}),1)
        self.assertEqual(pred({}, {}, {'SL2':'Other'}, {'LL2':'Parent'}),0)

    def test_exact_operators_decimal_and_raw_NULL(self):
        self.assertTrue(compare(Decimal('10.25'),'greaterthan','10'))
        self.assertTrue(compare(Decimal('10.25'),'smallerthanequalto','10.25'))
        self.assertTrue(compare(None,'notequalto','-'))
        self.assertTrue(compare(None,'doesnotcontain','-'))
        self.assertTrue(compare(None,'hasnovalue',''))
        self.assertFalse(compare(None,'equalto','-'))
        self.assertTrue(compare(0,'hasnovalue',''))
        self.assertTrue(compare('  ','hasnovalue',''))
        with self.assertRaises(PublicationUnavailable): compare(1,'equals','1')

    def test_SQL_like_and_case_trailing_equality(self):
        self.assertTrue(compare('B1 Product','contains','[Pp]ro_uct'))
        self.assertTrue(compare('B1 Product','startswith','B%'))
        self.assertTrue(compare('Leaf  ','equalto','leaf'))
        self.assertTrue(compare('B1 Product','doesnotendwith','Other'))

    def test_parent_join_duplicate_multiplicity(self):
        importer={'LocationAttributeData':[dict(WHCode='LDC001',LocationType='LDC')]*2}
        pred=self.predicate({'supplyChainFilter':[self.item('forchildren','equalto','LDC')]},importer)
        self.assertEqual(pred({'ParentWhCode':'LDC001'}, {}, {}, {}),2)
        self.assertEqual(pred({'ParentWhCode':None}, {}, {}, {}),0)

    def test_filter_before_ISNULL_projection_preserves_join_bags(self):
        probe=RrrProjectionTest(); probe.setUp()
        importer=probe.output['ClosingState'][0]['importer']
        importer['SkuLocAttributeData']*=2
        original=deepcopy(probe.output)
        pred=self.predicate({'customAttributeFilter':[self.item('SKULocAttr15','hasnovalue','')]},importer)
        rows=selected_rows(probe.output,[probe.band],predicate=pred)
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]['SKULocAttr15'],'-')
        self.assertEqual(probe.output,original)

    def test_source_invalid_columns_are_not_repaired(self):
        for group,attribute in (('coverageFilter','coverage'),('availabilityFilter','category'),
                                ('availabilityFilter','availability'),('productFilter','p9')):
            with self.subTest(group=group),self.assertRaises(PublicationUnavailable):
                self.predicate({group:[self.item(attribute,'equalto','1')]})


if __name__=='__main__': unittest.main()
