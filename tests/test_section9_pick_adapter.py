"""Closed persisted Pick representations and independent auxiliary rounding.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from decimal import Decimal
import unittest

from mta.application.complete_daily_batch_files import reports_from_pick_state, sqlcmd_bytes
from mta.application.complete_daily_pick_files import project_reports
from mta.domain.remaining_capabilities import calculate_pick_list_state, calculate_bor_oa
from mta.row_sequences import RecordRows
from mta.serialization import storage
from tests.test_pick_stage_state import fixture


class Section9PickAdapterTests(unittest.TestCase):
    def test_exact_four_files_mixed_representations_and_no_mutation(self):
        source=calculate_pick_list_state(fixture())
        names=('LogisticPickList','PickListDataForTruckFormation')
        expected=project_reports(logistic_pick_list=source[names[0]],pick_list_data_for_truck_formation=source[names[1]])
        wire=storage(source);before=deepcopy(wire)
        for mask in range(4):
            state={name:RecordRows.from_rows(wire[name]) if mask & (1<<i) else wire[name]
                for i,name in enumerate(names)}
            actual=reports_from_pick_state(state)
            self.assertEqual(actual,expected)
            self.assertEqual({key:sqlcmd_bytes(value['resultsets']) for key,value in actual.items()},
                {key:sqlcmd_bytes(value['resultsets']) for key,value in expected.items()})
            self.assertEqual(wire,before)

    def test_missing_empty_malformed_nonfinite_and_undeclared_populations(self):
        names=('LogisticPickList','PickListDataForTruckFormation')
        self.assertEqual(len(reports_from_pick_state(dict.fromkeys(names,[]))),4)
        for name in names:
            state=storage(calculate_pick_list_state(fixture()))
            del state[name]
            with self.assertRaises(KeyError):reports_from_pick_state(state)
        for replacement in (None,(),iter([]),{'rows':[]}):
            with self.assertRaises(ValueError):reports_from_pick_state(dict(zip(names,(replacement,[]))))
        for bad in ('NaN','Infinity','-Infinity',1.5):
            state=storage(calculate_pick_list_state(fixture()))
            state[names[0]][0]['TotalWeight']=bad
            with self.assertRaises(ValueError):reports_from_pick_state(state)
        state=storage(calculate_pick_list_state(fixture()))
        del state[names[0]][0]['RemainingWeigt']
        with self.assertRaisesRegex(ValueError,'column roster'):reports_from_pick_state(state)

    def test_auxiliary_percentage_uses_native_half_up_only(self):
        bands=dict.fromkeys(('order_black','order_red','order_yellow','order_green','order_blue',
            'norm_black','norm_red','norm_yellow','norm_green','order_black_band','order_red_band',
            'order_yellow_band','order_green_band'),'0')
        item=dict(case='rounding',sku='A',location='W',supplier='P',sob='100',norm='10',
            virtual_norm='10',stock='0',git='0',moq='1',bands=bands)
        for numerator,denominator,expected in (('1','32','3.13'),('627','20000','3.14'),
                ('1','8','12.50'),('0','0','0.00')):
            source=deepcopy(item);source['bands'].update(order_black=numerator,order_black_band=denominator)
            before=deepcopy(source)
            result=calculate_bor_oa({'items':[source]})[0]
            self.assertEqual(result['order_unsatisfied_percent']['black'],expected)
            self.assertEqual(source,before)


if __name__=='__main__':unittest.main()
