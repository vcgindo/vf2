"""Regression cases qualified through the pinned DLL BOR filter wrapper."""
import os
import unittest

os.environ.setdefault('VF_SECRET_KEY','unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation.bor_sql import BorFilters,BorQueryError
from mta.presentation.context import PublicationUnavailable


def item(name,value='0',operator='greaterthan',**extra):
    return dict(attributeName=name,value=value,operator=operator,**extra)


class BorFilterContractTests(unittest.TestCase):
    # Native queries: bor-family-20261006-001/native-filters-001.json.
    # DLL 0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346.
    def compile(self,filters):
        compiler=BorFilters(dict(filters=filters))
        return compiler.compile(),compiler.params

    def test_swallowed_null_builder_keeps_only_flushed_predicates(self):
        for filters in (None,{'productFilter':{'filters':None}},
                        {'availabilityFilter':{'filters':[item('norm',None)]}}):
            self.assertEqual(self.compile(filters),('TRUE',[]))
        location={'locationFilter':{'filters':[item('location','P001')]}}
        self.assertEqual(self.compile(location),self.compile({**location,'productFilter':{'filters':None}}))
        norm={'availabilityFilter':{'filters':[item('norm')]}}
        self.assertEqual(self.compile(norm),self.compile({'availabilityFilter':{'filters':[item('norm'),item(None)]}}))
        # The local SKU list is not flushed before a later item throws.
        self.assertEqual(self.compile({'productFilter':{'filters':[item('sku','A'),item(None)]}}),('TRUE',[]))

    def test_provider_failures_are_not_swallowed_builder_failures(self):
        for filters in (
            {'availabilityFilter':{'filters':[item('norm'),item('stock',None)]}},
            {'availabilityFilter':{'filters':[item('norm'),item('stock',operator='unknown')]}},
            {'availabilityFilter':{'filters':[item('category','x','contains')]}},
            {'availabilityFilter':{'filters':[item('availability')]}},
            {'colorFilter':{'filters':[item('red',type='colorage')]}},
            {'supplyChainFilter':{'filters':[item('forchildren','Plant'),item(None)]}},
        ):
            with self.subTest(filters=filters),self.assertRaises((BorQueryError,PublicationUnavailable)):
                self.compile(filters)
        self.assertEqual(self.compile({'availabilityFilter':{'filters':[item('norm',operator='unknown')]}}),('TRUE',[]))
        self.assertEqual(self.compile({'colorFilter':{'filters':[item('red')]}}),('TRUE',[]))

    def test_values_are_parameters_and_native_owners_are_allowlisted(self):
        value="FG'); DROP TABLE example; --"
        sql,params=self.compile({'productFilter':{'filters':[item('p1',value,'equalto')]}})
        self.assertNotIn(value,sql)
        self.assertEqual(params,[value])
        with self.assertRaises(BorQueryError): BorFilters({}).column('B','availability')


if __name__=='__main__': unittest.main()
