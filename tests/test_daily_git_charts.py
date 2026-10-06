"""Declared connector cases for the pure deployed GIT chart port."""
from decimal import Decimal
import unittest

from mta.presentation.daily_git_charts import datasets,response


class DailyGitChartTests(unittest.TestCase):
    def inputs(self):
        truck=dict(SKUCode='A',WhCode='L',ParentWhCode='P',TransporterCode='T',
                   TransporterName='Carrier',OrderNo='O',IsReceiving=True,
                   PhysicalInventoryColor='Red',LRCode='LR1')
        transporter=[dict(truck,SKUStatus='SuperDelay',TruckStatus='SuperDelay'),
                     dict(truck,LRCode='LR2',SKUStatus='Delay',TruckStatus='Delay')]
        transit=[dict(SKUCode='A',WhCode='L',TLT=5,SLT=2),
                 dict(SKUCode='A',WhCode='L',TLT=9,SLT=2),
                 dict(SKUCode='A',WhCode='L',TLT=99,SLT=None)]
        git=[dict(SKUCode='A',WhCode='L',ParentWhCode='P',PhysicalInventoryColor='Black',Git=1,IsParent=True)]
        attrs=[dict(WHCode='L',LogisticsLocation='LOG',LL1='North',LL2=None,LL3=None,LL4=None,LL5=None,c1='Dynamic')]
        descriptions=[dict(WHCode='L',WHDescription="L'ocation")]
        return dict(transporter=transporter,transit=transit,git_master=git,
                    location_attributes=attrs,location_descriptions=descriptions,
                    product_scope={'A':2},location_scope={'P':1,'L':1},
                    dynamic_attributes=[('custom1','c1')],
                    dynamic_ui_config=[dict(header='Custom 1',colCode='custom1',colPosition=7)])

    def test_four_datasets_preserve_scope_join_multiplicity_and_null_slt(self):
        result=datasets(**self.inputs())
        self.assertEqual(len(result['tables']),4)
        location_status,location_delay,transporter_status,transporter_delay=result['tables']
        self.assertEqual([(row['SKUStatus'],row['counts']) for row in location_status],
                         [('SuperDelay',2),('Delay',2)])
        self.assertEqual([(row['TruckStatus'],row['counts']) for row in transporter_status],
                         [('SuperDelay',2),('Delay',2)])
        # 2 transporter occurrences x 2 qualifying raw rows x scope weight 2,
        # then the outer transporter join: each location group counts 16 LR rows.
        self.assertEqual(location_delay[0]['LRCount'],16)
        self.assertEqual(transporter_delay[0]['LRCount'],16)
        for row in (location_delay[0],transporter_delay[0]):
            self.assertEqual(row['MinDelayDays'],3)
            self.assertEqual(row['MaxDelayDays'],7)
            self.assertEqual(row['Mean'],Decimal('5.00'))
            self.assertEqual(row['Median'],Decimal('5.00'))
            self.assertEqual(row['Q1'],Decimal('3.00'))
            self.assertEqual(row['Q3'],Decimal('7.00'))

    def test_actual_response_shape_and_string_values(self):
        wire=response(datasets(**self.inputs()))['data']
        location=wire['locationWise']
        columns=location['maxTechBlackRedColumn']['data']
        self.assertEqual(columns,[dict(superdelay='2',delay='2',name='Location',
                                       custom1='Dynamic',ll1='North',ll2='',ll3='',ll4='',ll5='')])
        stats=location['delayDaysStatisticalBox']['data'][0]
        self.assertEqual(stats['LogisticsLocation'],'LOG')
        self.assertEqual((stats['mean'],stats['median'],stats['Q1'],stats['Q3']),
                         ('5.00','5.00','3.00','7.00'))
        transporter=wire['transporterWise']['maxTechBlackRedColumn']['data'][0]
        self.assertEqual(transporter['name'],'Carrier')
        self.assertEqual((transporter['superdelay'],transporter['delay']),('2','2'))
        self.assertEqual([row['colCode'] for row in location['maxTechBlackRedColumn']['uiconfig']],
                         ['custom1','ll1','ll2','ll3','ll4','ll5'])

    def test_dynamic_location_configuration_is_explicit_and_exact(self):
        inputs=self.inputs();inputs['dynamic_ui_config']=[]
        with self.assertRaisesRegex(ValueError,'configuration differ'):
            datasets(**inputs)
        inputs=self.inputs();inputs['dynamic_attributes']=None
        with self.assertRaisesRegex(ValueError, 'Explicit'):
            datasets(**inputs)


if __name__=='__main__':unittest.main()
