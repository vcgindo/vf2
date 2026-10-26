import unittest
from mta.presentation.runtime_report_downloads import allowed,permission_rows,SELECTORS


class WholeFilePermissions(unittest.TestCase):
    def test_supplier_and_parent_codes_are_required(self):
        rows=[dict(SKUCode='SKU',WhCode='WH',ParentWhCode='SUPPLIER')]
        self.assertTrue(allowed(rows,10,{'SKU'},{'WH','SUPPLIER'}))
        self.assertFalse(allowed(rows,10,{'SKU'},{'WH'}))
        self.assertFalse(allowed(rows,10,{'OTHER'},{'WH','SUPPLIER'}))
        self.assertFalse(allowed(rows,10,{'SKU'},{'SUPPLIER'}))

    def test_spike_first_service_location_is_required(self):
        rows=[dict(SKUCode='SKU',WhCode='WH',FirstServicingWhCode='PARENT')]
        self.assertFalse(allowed(rows,7,{'SKU'},{'WH'}))
        self.assertTrue(allowed(rows,7,{'SKU'},{'WH','PARENT'}))

    def test_nullable_parent_is_absence_but_missing_field_denies(self):
        rows=[dict(SKUCode='SKU',WhCode='WH',ParentWhCode=None)]
        self.assertTrue(allowed(rows,10,{'SKU'},{'WH'}))
        del rows[0]['ParentWhCode']
        with self.assertRaises(KeyError):allowed(rows,10,{'SKU'},{'WH'})

    def test_empty_report_requires_nonempty_authorized_scope(self):
        self.assertTrue(allowed([],7,{'SKU'},{'WH'}))
        self.assertFalse(allowed([],7,set(),{'WH'}))
        self.assertFalse(allowed([],7,{'SKU'},set()))

    def test_partial_bag_is_not_a_filtered_download(self):
        rows=[dict(SKUCode='SKU',WhCode='WH',ParentWhCode=None),
              dict(SKUCode='OTHER',WhCode='WH',ParentWhCode=None)]
        self.assertFalse(allowed(rows,10,{'SKU'},{'WH'}))
        self.assertEqual(len(rows),2)

    def test_literal_selector_contract(self):
        self.assertEqual(SELECTORS,{'Spike_Order_Dump':7,'TotalReqReport_YYYY-MM-DD':10})

    def test_actual_positional_producers_feed_permission_projection(self):
        from tests.test_runtime_report_candidates import arguments
        from mta.application.runtime_report_projection import project
        values=arguments()
        for definition in values['report_configuration']['RuntimeReports']:
            identity=definition['Id']
            projected=project(definition,values['inputs'][identity]['sources'])
            rows=list(permission_rows(projected,identity))
            self.assertTrue(rows)
            parent='FirstServicingWhCode' if identity==7 else 'ParentWhCode'
            products={row['SKUCode'] for row in rows}
            locations={row[name] for row in rows for name in ('WhCode',parent) if row[name] is not None}
            self.assertTrue(allowed(rows,identity,products,locations))
            self.assertFalse(allowed(rows,identity,set(),locations))

    def test_postbtr_actual_producers_require_receiving_and_supplier_locations(self):
        import json
        from pathlib import Path
        from mta.application.runtime_report_projection import describe,project
        from tests.test_runtime_bor_report import sources,bor
        from tests.test_runtime_history_reports import efficiency_sources,allocation_sources
        definitions=json.loads((Path(__file__).parents[2]/'tests/fixtures/runtime_reports_retained_20261019.json').read_bytes())
        for definition in definitions:
            identity=definition['Id']
            if identity not in (2,3,4,5,6,8):continue
            with self.subTest(report=identity):
                inputs=(efficiency_sources() if identity in (2,3) else
                        allocation_sources() if identity==8 else sources())
                if identity==3:inputs['rationing_history'][0]['ParentNorm']=1
                if identity==6:inputs['bor_with_order_allocation']=[bor(WhCode='P001')]
                logical={name:([{'LastRunDate':inputs[key]}] if key=='today' else inputs[key])
                         for key,name in describe(definition)['sources'].items()}
                rows=list(permission_rows(project(definition,logical),identity))
                parent='ParentWhCode' if identity in (2,3) else 'SupplierCode'
                location='P001' if identity==6 else 'P041'
                self.assertEqual(rows,[{'SKUCode':'sku','WhCode':location,parent:'SUP'}])
                self.assertTrue(allowed(rows,identity,{'SKU'},{location,'SUP'}))
                self.assertFalse(allowed(rows,identity,{'SKU'},{location}))
                self.assertFalse(allowed(rows,identity,{'SKU'},{'SUP'}))
                self.assertFalse(allowed(rows,identity,{'OTHER'},{location,'SUP'}))

    def test_postbtr_permission_shape_cannot_hide_missing_or_duplicate_columns(self):
        from mta.presentation.context import PublicationUnavailable
        good=dict(columns=('A.SKUCode','A.WhCode','A.SupplierCode'),rows=[('sku','WH',None)])
        rows=list(permission_rows(good,4))
        self.assertTrue(allowed(rows,4,{'sku'},{'WH'}))
        for columns,cells in ((('A.SKUCode','A.WhCode'),('sku','WH')),
                (('A.SKUCode','A.WhCode','A.SupplierCode','A.SupplierCode'),('sku','WH',None,None)),
                (good['columns'],('sku','WH'))):
            with self.assertRaises(PublicationUnavailable):
                list(permission_rows(dict(columns=columns,rows=[cells]),4))
        for identity in (True,9,'4'):
            with self.assertRaises(ValueError):list(permission_rows(good,identity))
