"""Planning-specific SQL filter activation and canonical owner selection."""
import os
import unittest
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.presentation.planning_grid_sql import GridFilters
from mta.runtime.models import ExcessInventoryRow

class PlanningGridFiltersTests(unittest.TestCase):
    def test_custom_only_is_ignored_by_deployed_activation_rule(self):
        query=GridFilters({'filters':{'customAttributeFilter':{'filters':[
            {'attributeName':'skulocattr1','operator':'hasnovalue','value':''}]}}},'excess',ExcessInventoryRow)
        self.assertEqual(query.compile(),'TRUE')
        self.assertEqual(query.owners,set())

    def test_standard_group_activates_custom_owner(self):
        query=GridFilters({'filters':{'availabilityFilter':{'filters':[]},'customAttributeFilter':{'filters':[
            {'attributeName':'skulocattr1','operator':'hasnovalue','value':''}]}}},'excess',ExcessInventoryRow)
        self.assertIn('B."c1"',query.compile())
        self.assertEqual(query.owners,{'B'})

    def test_pipeline_filter_uses_planning_pipeline_not_rrr_dispatch(self):
        query=GridFilters({'filters':{'availabilityFilter':{'filters':[
            {'attributeName':'pic','value':'Red'}]}}},'excess',ExcessInventoryRow)
        self.assertIn('A."PipelineInventoryColor"',query.compile())
        self.assertEqual(query.params,['Red'])
