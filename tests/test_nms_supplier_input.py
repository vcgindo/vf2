"""Focused native supplier importer semantics; no day or calculated fixture."""
from copy import deepcopy
import unittest

from mta.mdm.supplier_input import (compose_supplier_inputs, archive_populations,
                                    cleared_populations, QUEUES)


def fixture():
    # Identities retained in catalogue2ecf4e07; supplier values/requests are
    # explicitly authored test facts, not imported calculation outputs.
    row = dict(SKUCode='337', WHCode='DP010290', SupplierCode='LDC001',
               SupplierDescription='external opening', SOB=37.125)
    raw = {'SOBDataRaw': [row, dict(row)],
           'MOQDataRaw1': [dict(SKUCode='337', SupplierCode='LDC001',
                               SupplierDescription='external opening', MOQ=20)],
           'MOQDataRaw2': [dict(SKUCode='337', WHCode='DP010290',
                               SupplierCode='LDC001', SupplierDescription=None, MOQ=30)]}
    queues = {name: [] for name in QUEUES}
    locations = [dict(WHCode='LDC001', WHDescription='LDC001 Virtual Warehouse')]
    return raw, queues, locations


def approved(**values):
    return dict(SKUCode='337', WhCode='DP010290', SupplierCode='LDC001',
                SOB=12.375, ActionType=1, Approved=True, Reverted=False, **values)


class SupplierInputTests(unittest.TestCase):
    def test_duplicate_replacement_and_fractional_float(self):
        raw, queues, locations = fixture()
        queues['NMSSOB'] = [approved(), approved()]
        before = deepcopy((raw, queues, locations))
        actual = compose_supplier_inputs(raw, queues, moq_format='WithoutDestLoc', locations=locations)
        self.assertEqual(actual['SOBDataRaw'], [dict(SKUCode='337', WHCode='DP010290',
            SupplierCode='LDC001', SupplierDescription='LDC001 Virtual Warehouse', SOB=12.375)] * 2)
        self.assertEqual((raw, queues, locations), before)

    def test_native_marker_two_deletes_without_inserting(self):
        raw, queues, locations = fixture()
        queues['NMSMOQWithoutDestination'] = [dict(SKUCode='337', SupplierCode='LDC001',
            MOQ=99, Approved=True, Reverted=False, ActionType=2)]
        actual = compose_supplier_inputs(raw, queues, moq_format='WithoutDestLoc', locations=locations)
        self.assertEqual(actual['MOQDataRaw1'], [])
        self.assertEqual(actual['MOQDataRaw2'], raw['MOQDataRaw2'])

    def test_with_destination_and_zero(self):
        raw, queues, locations = fixture()
        raw['MOQDataRaw2'].append(dict(raw['MOQDataRaw2'][0], WHCode='DP020819'))
        queues['NMSMOQWithDestination'] = [dict(SKUCode='337', WhCode='DP010290',
            SupplierCode='LDC001', MOQ=0, Approved=True, Reverted=True, ActionType=1)]
        actual = compose_supplier_inputs(raw, queues, moq_format='WithDestLoc', locations=locations)
        self.assertEqual([r['MOQ'] for r in actual['MOQDataRaw2']], [30, 0])
        self.assertEqual(actual['MOQDataRaw1'], raw['MOQDataRaw1'])

    def test_null_raw_identity_does_not_join(self):
        raw, queues, locations = fixture()
        raw['SOBDataRaw'] = [dict(raw['SOBDataRaw'][0], SKUCode=None, SupplierCode=None, SOB=None)]
        queues['NMSSOB'] = [approved()]
        actual = compose_supplier_inputs(raw, queues, moq_format='WithDestLoc', locations=[])
        self.assertEqual(actual['SOBDataRaw'][0], dict(raw['SOBDataRaw'][0], SupplierDescription='ND'))
        self.assertEqual(len(actual['SOBDataRaw']), 2)

    def test_unapproved_rows_preserved_archive_all_clear_both_formats(self):
        raw, queues, locations = fixture()
        queues['NMSSOB'] = [dict(approved(), Approved=False)]
        for name in QUEUES[1:]:
            queues[name] = [dict(SKUCode='337', SupplierCode='LDC001', WhCode='DP010290',
                MOQ=None, ActionType=3, Approved=True, Reverted=True)]
        self.assertEqual(archive_populations(queues, moq_format='WithDestLoc'),
                         {name: queues[name] for name in ('NMSSOB', 'NMSMOQWithDestination')})
        self.assertEqual(cleared_populations(queues),
                         {'NMSSOB': queues['NMSSOB'], 'NMSMOQWithDestination': [], 'NMSMOQWithoutDestination': []})

    def test_conflicting_description_update_is_incomparable(self):
        raw, queues, locations = fixture()
        locations.append(dict(WHCode='LDC001', WHDescription='different'))
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            compose_supplier_inputs(raw, queues, moq_format='WithDestLoc', locations=locations)

    def test_missing_populations_or_format_is_not_defaulted(self):
        raw, queues, locations = fixture()
        for format_value in ('', None, 'withdestloc'):
            with self.assertRaises(ValueError):
                compose_supplier_inputs(raw, queues, moq_format=format_value, locations=locations)
        del queues['NMSSOB']
        with self.assertRaises(ValueError):
            compose_supplier_inputs(raw, queues, moq_format='WithDestLoc', locations=locations)
