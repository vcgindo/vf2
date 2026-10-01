"""Join unit checks, not replacement synthetic acceptance artifacts."""
from copy import deepcopy
import unittest
import json
import os
from unittest.mock import patch
os.environ.setdefault('VF_SECRET_KEY','unit-test-not-serving')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.test import Client
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_read import terminal_git_reports
from mta.presentation.planning_overview import counts
from mta.presentation.permissions import PermissionCodes


class PlanningOverviewTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(SKUCode='337', WhCode='AG515802', ParentWhCode='LP001',
            GIT=4, PhysicalInventoryColor='Red', RationedQty=3, PipelineInventoryColor='Black',
            ReportDate='2026-06-17')
        self.attributes = dict(SKUDescriptionTbl=[dict(SKUCode='337')],
            SiteDescriptionTbl=[dict(WHCode='AG515802')], SkuAttributeData=[dict(SKUCode='337')],
            LocationAttributeData=[dict(WHCode='AG515802')],
            SkuLocAttributeData=[dict(SKUCode='337', LocCode='AG515802')])
        self.standard = [self.row]
        self.reports = {name:[self.row] for name in ('git','transporter','transit','expedite','excess','fulfillment')}

    def result(self, products=None, locations=None):
        return counts(self.attributes, self.standard, self.reports, '2026-06-17',
            products=products if products is not None else PermissionCodes({'337':1}),
            locations=locations if locations is not None else PermissionCodes({'AG515802':1,'LP001':1}))

    def test_exact_response_strings_and_order(self):
        value = self.result()
        self.assertEqual([r['category'] for r in value], ['git/wip','expedite','excessInventory','orderFulfillment'])
        self.assertTrue(all(v == '1' for r in value for k,v in r.items() if k != 'category'))

    def test_missing_metadata_excludes_review_but_not_custom(self):
        self.attributes['SkuLocAttributeData'] = []
        value = self.result()
        self.assertEqual(value[1], dict(category='expedite', parentCount='0',childCount='0',custom='1'))
        self.assertEqual(value[2], dict(category='excessInventory',reviewCount='0',custom='1'))
        self.assertEqual(value[3], dict(category='orderFulfillment',reviewCount='0',custom='1'))

    def test_duplicate_joins_permissions_and_left_join_multiplicity(self):
        self.attributes['SkuLocAttributeData'] *= 2
        self.attributes['SiteDescriptionTbl'] += [dict(WHCode='LP001')]*3
        self.standard *= 2
        self.reports['transporter'] *= 2
        self.reports['transit'] *= 3
        value = self.result(products=PermissionCodes({'337':2}))
        self.assertEqual(value[0],dict(category='git/wip',parentCount='24',childCount='24',custom='12'))
        self.assertEqual(value[1],dict(category='expedite',parentCount='24',childCount='24',custom='2'))
        self.assertEqual(value[2],dict(category='excessInventory',reviewCount='12',custom='2'))
        self.assertEqual(value[3],dict(category='orderFulfillment',reviewCount='4',custom='2'))

    def test_parent_scope_and_null_exclusion(self):
        value = self.result(locations=PermissionCodes({'AG515802':1}))
        self.assertEqual((value[0]['childCount'],value[1]['childCount'],value[1]['custom']),('0','0','0'))
        self.row['WhCode'] = None
        value = self.result()
        self.assertEqual(value[1]['childCount'],'0')
        self.assertEqual(value[1]['custom'],'1')

    def test_no_permission_no_rows_and_no_input_mutation(self):
        before = deepcopy((self.attributes,self.standard,self.reports))
        self.assertTrue(all(v == '0' for r in self.result(products=PermissionCodes({}))
                            for k,v in r.items() if k != 'category'))
        self.assertEqual((self.attributes,self.standard,self.reports),before)

    def test_predicates_are_not_shared_with_custom_or_other_categories(self):
        self.row.update(GIT=0,RationedQty=0,ReportDate='2026-06-16')
        value=self.result()
        self.assertEqual(value[0]['parentCount'],'0')
        self.assertEqual(value[0]['custom'],'1')
        self.assertEqual(value[1]['custom'],'0')
        self.assertEqual(value[2]['custom'],'0')
        self.assertEqual(value[3]['custom'],'1')

    def test_terminal_producer_exclusion_requires_known_inputs(self):
        self.assertEqual(terminal_git_reports([{'GIT':0},{'GIT':None}],{'InTransitData':[]}),
                         dict(git=[],transporter=[],transit=[]))
        for rows,ancillary in (([{'GIT':1}],{'InTransitData':[]}),([],{'InTransitData':[self.row]})):
            with self.assertRaises(PublicationUnavailable): terminal_git_reports(rows,ancillary)
        with self.assertRaises(KeyError): terminal_git_reports([], {})

    def test_endpoint_denies_identity_and_filters_before_any_read(self):
        client=Client()
        with patch('mta.presentation.planning_read.planning_overview_context',side_effect=AssertionError('must not read')):
            self.assertEqual(client.post('/api/mta/GetPlanningDataCount','{}',content_type='application/json').status_code,403)
            reply=client.post('/api/mta/GetPlanningDataCount',json.dumps({'filters':{'productFilter':{
                'filters':[{'attributeName':'SKUCode','value':'337'}]}}}),content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY='{"id":"unit"}')
            self.assertEqual(reply.status_code,503)

    def test_missing_supplement_stays_unavailable(self):
        with patch('mta.presentation.planning_read.planning_overview_context',
                   side_effect=PublicationUnavailable('terminal_ancillary_supplement_not_configured')):
            reply=Client().post('/api/mta/GetPlanningDataCount','{}',content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY='{"id":"unit"}')
            self.assertEqual(reply.status_code,503)
