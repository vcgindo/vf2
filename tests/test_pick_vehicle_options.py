"""Approved independent vehicle options; no database or legacy fixture runner."""
from collections import defaultdict
from copy import deepcopy
import unittest

from mta.application.complete_daily_pick import calculate_native_pick


def source(quantity=7, capacities=(3, 4)):
    return dict(pick_rows=[dict(SKUCode='A',WhCode='W',ParentWhCode='P',
        RationedReq=quantity,DispatchColor='Black',TOR_B=quantity,TOR_R=0,TOY=0,TOG=0,TOBlue=0)],
        sku_attributes=[dict(SKUCode='A',Weight='1.000',Volume='1.000')],
        location_attributes=[dict(WHCode='W',LogisticsLocation='L')],
        vehicles=[dict(VehicleID=i,VehicleName='V'+str(i),Weight=str(cap),Volume='100.000')
                  for i,cap in enumerate(capacities)],
        location_vehicles=[dict(LocationID='P',VehicleID=i) for i in range(len(capacities))])


class IndependentVehicleOptionsTest(unittest.TestCase):
    def test_different_capacities_conserve_each_option_without_cross_subtraction(self):
        raw=source();saved=deepcopy(raw);result=calculate_native_pick(**raw)
        totals=defaultdict(int)
        for table in ('LogisticPickList','PickListDataForTruckFormation'):
            for row in result[table]:
                self.assertGreaterEqual(row['ColorWiseAlloction'],0)
                totals[row['VehicleName']]+=row['ColorWiseAlloction']
        self.assertEqual(dict(totals),{'V0':7,'V1':7})
        self.assertEqual(raw,saved)
        for row in result['LogisticPickList']:
            self.assertLessEqual(row['ColorWiseAlloction'],3 if row['VehicleName']=='V0' else 4)

    def test_underfilled_options_remain_separate(self):
        result=calculate_native_pick(**source(quantity=2))
        self.assertEqual(result['LogisticPickList'],[])
        self.assertEqual(sorted((r['VehicleName'],r['ColorWiseAlloction'])
            for r in result['PickListDataForTruckFormation']),[('V0',2),('V1',2)])

    def test_equal_capacity_options_are_independent(self):
        result=calculate_native_pick(**source(quantity=2,capacities=(3,3)))
        self.assertEqual(result['LogisticPickList'],[])
        self.assertEqual(len(result['PickListDataForTruckFormation']),2)

    def test_single_vehicle_retains_two_trucks_and_residual(self):
        result=calculate_native_pick(**source(capacities=(3,)))
        self.assertEqual([r['ColorWiseAlloction'] for r in result['LogisticPickList']],[3,3])
        self.assertEqual([r['ColorWiseAlloction'] for r in result['PickListDataForTruckFormation']],[1])

    def test_dimension_ambiguity_is_still_denied(self):
        raw=source();raw['sku_attributes'].append(dict(SKUCode='A',Weight='2.000',Volume='1.000'))
        with self.assertRaisesRegex(ValueError,'differing dimension candidates'):
            calculate_native_pick(**raw)

    def test_both_null_dimensions_remain_excluded(self):
        raw=source();raw['sku_attributes'][0].update(Weight=None,Volume=None)
        result=calculate_native_pick(**raw)
        self.assertEqual(result['LogisticPickList'],[])
        self.assertEqual(result['PickListDataForTruckFormation'],[])


if __name__=='__main__':unittest.main()
