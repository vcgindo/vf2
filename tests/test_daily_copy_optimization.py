"""Complete stage equivalence and mutation ownership for daily copy reduction.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from mta.application import daily_finalization
from mta.domain.complete_daily_completion import mark_script_executed
from mta.domain.complete_daily_scalars import ascii_equal


class DailyCopyTests(unittest.TestCase):
    def test_only_final_source_is_hashed_and_its_exact_checksum_is_unchanged(self):
        import hashlib
        import json
        from tests.test_h3_daily_integration import frame, coupled
        from mta.temporal import chain
        original=chain.calculation_source
        checks=[]
        def source(*args,**kwargs):
            result=original(*args,**kwargs)
            snapshot=result['foundation']['snapshot']
            checksum=snapshot.pop('source_manifest_checksum')
            try:
                expected=hashlib.sha256(json.dumps(chain.json_value(result),sort_keys=True,
                    separators=(',',':')).encode()).hexdigest()
                self.assertEqual(checksum,expected)
            finally:
                snapshot['source_manifest_checksum']=checksum
            checks.append(checksum)
            return result
        f=frame()
        with patch.object(chain,'calculation_source',side_effect=source):
            coupled(f['profile'],f['opening']['state'],'2037-04-09','2037-04-10')
        self.assertEqual(len(checks),1)

    def test_dbm_owned_stages_equal_pure_stages_and_retained_reports_are_stable(self):
        from tests.test_h3_daily_integration import frame, coupled
        from mta.temporal import chain
        from mta.domain.dbm_selected_chain import selected_stages
        original_dispatch=chain.connected_dbm_stages
        inspected=[]
        def dispatch(today,state,facts,delivery,report_exceptions=None):
            before=deepcopy(state)
            expected=list(selected_stages(today,state,facts,delivery['batch'],report_exceptions,
                conditional_settings=delivery.get('conditional_dbm',{}).get('importer_vf_settings')))
            retained=[]
            for (name,current),(other,wanted) in zip(original_dispatch(
                    today,state,facts,delivery,report_exceptions),expected,strict=True):
                self.assertEqual(name,other)
                self.assertEqual(current,wanted,name)
                for previous,frozen in retained:
                    self.assertEqual(previous,frozen,name)
                retained.append((current,deepcopy(current)))
                yield name,current
            self.assertEqual(state,before)
            inspected.append(len(retained))
        f=frame()
        with patch.object(chain,'connected_dbm_stages',side_effect=dispatch):
            coupled(f['profile'],f['opening']['state'],'2037-04-09','2037-04-10')
        self.assertTrue(inspected and inspected[0]>15)

    def test_compound_flags_equal_ordered_domain_updates_and_isolate_input(self):
        original = deepcopy(daily_finalization.FLAG_SEED)
        complete = dict(ScriptExecutedFlag=original)
        scripts = ('StockCalculation.sql', 'GenerateAddionalMasterData.sql',
                   'StockCalculation.sql', None, 'missing')
        expected = original
        for script in scripts:
            expected = mark_script_executed(expected, script, equal=ascii_equal)
        daily_finalization.mark(complete, *scripts)
        self.assertEqual(complete['ScriptExecutedFlag'], expected)
        self.assertEqual(original, daily_finalization.FLAG_SEED)
        self.assertIsNot(complete['ScriptExecutedFlag'], original)

    def test_btr_all_owned_stages_equal_pure_stages_and_remain_stable(self):
        from tests.test_h3_daily_integration import frame, coupled
        from mta.temporal import chain
        from mta.domain.btr_finalization import btr_stages
        original_dispatch = chain.connected_btr_stages
        inspected = []

        def dispatch(today, prior, facts, delivery, **extra):
            prior_before, facts_before = deepcopy(prior), deepcopy(facts)
            current = {**facts, 'LastBatchRunTbl':[{'LastRunDate':today+'T00:00:00'}],
                'BPRDailyConsumption':extra['bpr_daily'],
                'SupplierDispatchReq':extra['supplier_dispatch_req']}
            expected = list(btr_stages(today, prior, current, delivery['btr_settings'],
                importer_vf_settings=delivery.get('btr_history',{}).get('importer_vf_settings')))
            retained = []
            for (name, state), (expected_name, expected_state) in zip(
                    original_dispatch(today, prior, facts, delivery, **extra), expected, strict=True):
                self.assertEqual(name, expected_name)
                self.assertEqual(state, expected_state, name)
                for previous, frozen in retained:
                    self.assertEqual(previous, frozen, name)
                retained.append((state, deepcopy(state)))
                yield name, state
            self.assertEqual(prior, prior_before)
            self.assertEqual(facts, facts_before)
            inspected.append(len(retained))

        f = frame()
        original = deepcopy(f)
        with patch.object(chain, 'connected_btr_stages', side_effect=dispatch):
            coupled(f['profile'], f['opening']['state'], '2037-04-09', '2037-04-10')
        self.assertTrue(inspected and inspected[0] >= 11)
        self.assertEqual(f, original)


if __name__ == '__main__':
    unittest.main()
