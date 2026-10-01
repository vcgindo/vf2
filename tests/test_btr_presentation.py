"""BTR consumer mechanics; canonical retained-data receipt is separate."""
import unittest
from mta.presentation import btr


def output():
    pair=dict(SKUCode='337',WhCode='AG515802')
    state=dict(BPPTrendPhysicalInv=[dict(pair,D90=12)],
        BufferTrendPhysicalInv=[dict(pair,ParentWhCode='LDC001',D90='Green',Age=2,GreenCount=1)],
        LocationAttributeData=[],SkuAttributeData=[],SkuLocAttributeData=[])
    closing=dict(dbm=dict(SKULocStandardAttributes=[dict(pair,Category='5',Tags=None)]),
        importer=dict(SKUDescriptionTbl=[dict(SKUCode='337',SKUDescription='Retained SKU')],
            SiteDescriptionTbl=[dict(WHCode='AG515802',WHDescription='Retained location'),
                dict(WHCode='LDC001',WHDescription='Retained parent')]),
        consumer_context=dict(CategoryColDescription=[dict(CategoryId=5,CategoryAlias='SE')]))
    return dict(BTRFinal=[state],ClosingState=[closing],BPRStages=[dict(state=dict(
        vf_RationedReqReport=[dict(pair,ParentWhCode='LDC001',Norm=220,VirtualNorm=230)]))])


class BTRTest(unittest.TestCase):
    def test_selected_horizon_inclusive_and_default(self):
        self.assertEqual(btr.horizon_columns('2026-06-17',{}),tuple(f'D{i}' for i in range(1,91)))
        payload=dict(filters=dict(horizonFilter=dict(filters=[dict(attributeName='startDate',value='2026-06-06'),
            dict(attributeName='endDate',value='2026-06-17')])))
        self.assertEqual(btr.horizon_columns('2026-06-17',payload),tuple(f'D{i}' for i in range(79,91)))

    def test_two_pass_join_preserves_duplicates_and_final_limit(self):
        value=output(); value['BTRFinal'][0]['SkuAttributeData']=[dict(SKUCode='337'),dict(SKUCode='337')]
        joined=btr.joined_rows(value,'tech'); self.assertEqual(len(joined),2)
        rows=btr.project_rows(value,'tech',joined,('D90',),10)
        self.assertEqual(len(rows),4)
        self.assertTrue(all(r==rows[0] for r in rows))
        self.assertEqual(btr.project_rows(value,'tech',joined,('D90',),3),rows[:3])

    def test_wire_strings_parent_description_and_sql_null(self):
        value=output(); rows=btr.project_rows(value,'tech',btr.joined_rows(value,'tech'),('D90',),10)
        row=rows[0]
        self.assertEqual((row['Norm'],row['VirtualNorm'],row['D90'],row['CD90']),('220','230','12','Green'))
        self.assertEqual((row['Availability'],row['Tags'],row['rc']),('','',''))
        self.assertEqual((row['pc'],row['pn'],row['Category']),('LDC001','Retained parent','SE'))


if __name__=='__main__': unittest.main()
