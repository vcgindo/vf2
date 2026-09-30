"""Unit stubs prove the narrow limitation never hides deterministic differences."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from parity.report_flaws import compare_reports, validate_scope
from parity.replay_temporal import independent_contracts_pass

SCOPE=json.loads((Path(__file__).resolve().parents[1]/'baseline/norm0-occurrence-limitation.json').read_text())


class ReportFlawTest(unittest.TestCase):
    def pair(self):
        state=dict(DBMMaster=[dict(SKUCode='5405',WhCode='LP001',Norm=0)],
                   SKUDescriptionTbl=[dict(SKUCode='5405',SKUDescription='retained')],
                   DailyConsumption=[dict(SKUCode='5405',WhCode='LP001',ReportDate=d,Consumption=1)
                                     for d in ('2026-06-05','2026-06-06')])
        raw='[06/06/26 - 1], [05/06/26 - 1]'
        left={'norm0-data':{'Norm0Norm1Norm2Report':[
            dict(SKUCode='5405',WHCode='LP001',Count=2,TotalSale=2,Occurances=raw)]},
            'norm1-data':{'ReportRows':[{'values':['5405','retained','LP001','site','parent',0,2,2,raw]}]}}
        right=deepcopy(left)
        right['norm0-data']['Norm0Norm1Norm2Report'][0]['Occurances']=None
        right['norm1-data']['ReportRows'][0]['values'][8]=' '
        return left,right,state

    def compare(self,left,right,state):return compare_reports(left,right,state,'2026-06-06',SCOPE)

    def test_only_proven_text_is_unproven_and_raw_values_survive(self):
        left,right,state=self.pair();original=deepcopy((left,right))
        result=self.compare(left,right,state)
        self.assertEqual(result['status'],'LEGACY_FLAW')
        self.assertEqual(result['deterministic_status'],'PASS')
        self.assertFalse(result['parity_claim_for_affected_field'])
        self.assertEqual(len(result['raw_values']),4)
        self.assertEqual((left,right),original)
        self.assertTrue(independent_contracts_pass([dict(contract='emitted-reports',**result)]))

    def test_changed_quantity_fails(self):
        left,right,state=self.pair()
        right['norm0-data']['Norm0Norm1Norm2Report'][0]['TotalSale']=3
        self.assertEqual(self.compare(left,right,state)['status'],'FAIL')

    def test_duplicate_population_fails(self):
        left,right,state=self.pair()
        rows=right['norm0-data']['Norm0Norm1Norm2Report']
        rows.append(deepcopy(rows[0]))
        self.assertEqual(self.compare(left,right,state)['status'],'FAIL')

    def test_invented_modern_order_is_not_accepted(self):
        left,right,state=self.pair()
        right['norm0-data']['Norm0Norm1Norm2Report'][0]['Occurances']='[05/06/26 - 1], [06/06/26 - 1]'
        with self.assertRaisesRegex(ValueError,'not invented'):self.compare(left,right,state)

    def test_missing_legacy_fragment_is_not_called_order_ambiguity(self):
        left,right,state=self.pair()
        left['norm0-data']['Norm0Norm1Norm2Report'][0]['Occurances']='[05/06/26 - 1]'
        with self.assertRaisesRegex(ValueError,'source observations'):self.compare(left,right,state)

    def test_scope_cannot_expand_to_other_norms_or_input(self):
        changed=deepcopy(SCOPE);changed['norm012_occurrence_order_scope']['norms']=[0,1]
        with self.assertRaises(ValueError):validate_scope(changed,SCOPE['evidence']['input_sha256'])
        with self.assertRaises(ValueError):validate_scope(SCOPE,'wrong')

    def test_no_generic_legacy_flaw_escape_for_calculations(self):
        result=self.compare(*self.pair())
        self.assertFalse(independent_contracts_pass([dict(contract='calculation/requirements',**result)]))
        result['deterministic_status']='FAIL'
        self.assertFalse(independent_contracts_pass([dict(contract='emitted-reports',**result)]))
