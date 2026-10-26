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
