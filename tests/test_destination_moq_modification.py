"""Approved destination MOQ replacement; retain other native marker semantics."""
import os
import unittest
from copy import deepcopy
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from mta.mdm import moq
from mta.mdm.supplier_input import compose_supplier_inputs, QUEUES


def case():
    row = dict(SKUCode='337', WHCode='LDC001', SupplierCode='PL002',
               SupplierDescription='Plant', MOQ=1)
    raw = dict(SOBDataRaw=[], MOQDataRaw1=[], MOQDataRaw2=[row,
        dict(row, WHCode='OTHER'), dict(row, SupplierCode='OTHER')])
    queue = dict(SKUCode='337', WhCode='LDC001', SupplierCode='PL002',
                 MOQ=2, ActionType=2, Approved=True, Reverted=False)
    queues = {name: [] for name in QUEUES}
    queues['NMSMOQWithDestination'] = [queue]
    return raw, queues, [dict(WHCode='PL002', WHDescription='Plant')]


class DestinationMoqModificationTests(unittest.TestCase):
    def test_replaces_only_exact_destination_and_supplier_keeps_action_and_input(self):
        raw, queues, loc = case(); before = deepcopy((raw, queues, loc))
        out = compose_supplier_inputs(raw, queues, moq_format='WithDestLoc', locations=loc)
        self.assertEqual([(r['WHCode'], r['SupplierCode'], r['MOQ']) for r in out['MOQDataRaw2']],
                         [('OTHER','PL002',1),('LDC001','OTHER',1),('LDC001','PL002',2)])
        self.assertEqual((raw, queues, loc), before)

    def test_unapproved_modification_does_not_remove_or_insert(self):
        raw, queues, loc = case(); queues['NMSMOQWithDestination'][0]['Approved'] = False
        out = compose_supplier_inputs(raw, queues, moq_format='WithDestLoc', locations=loc)
        self.assertEqual([r['MOQ'] for r in out['MOQDataRaw2']], [1,1,1])

    def test_remove_still_removes_without_replacement(self):
        raw, queues, loc = case(); queues['NMSMOQWithDestination'][0]['ActionType'] = 3
        out = compose_supplier_inputs(raw, queues, moq_format='WithDestLoc', locations=loc)
        self.assertEqual([r['WHCode'] for r in out['MOQDataRaw2']], ['OTHER','LDC001'])

    def test_equal_duplicate_approved_rows_remain_occurrences(self):
        raw, queues, loc = case(); queues['NMSMOQWithDestination'] *= 2
        out = compose_supplier_inputs(raw, queues, moq_format='WithDestLoc', locations=loc)
        self.assertEqual([r['MOQ'] for r in out['MOQDataRaw2']], [1,1,2,2])

    def test_null_or_zero_modification_is_not_invented_or_rounded(self):
        for value in (None, 0):
            raw, queues, loc = case(); queues['NMSMOQWithDestination'][0]['MOQ'] = value
            out = compose_supplier_inputs(raw, queues, moq_format='WithDestLoc', locations=loc)
            self.assertIs(out['MOQDataRaw2'][-1]['MOQ'], value)

    def test_other_format_retains_historical_action_two_behavior(self):
        raw, queues, loc = case()
        raw['MOQDataRaw1'] = [dict(SKUCode='337',SupplierCode='PL002',MOQ=1)]
        queues['NMSMOQWithoutDestination'] = [dict(queues['NMSMOQWithDestination'][0])]
        out = compose_supplier_inputs(raw, queues, moq_format='WithoutDestLoc', locations=loc)
        self.assertEqual(out['MOQDataRaw1'], [])

    def test_destination_column_visible_but_immutable(self):
        with patch('mta.mdm.supplier.setting', return_value='WithDestLoc'):
            for screen in ('modify', 'view', 'add'):
                field = next(f for f in moq.configuration(screen, source=object())[0]['fields'] if f['key']=='wc')
                self.assertTrue(field['visible']); self.assertFalse(field['isEdit'])
                self.assertEqual(field['isAdd'], screen=='add')

    def test_other_format_metadata_stays_hidden(self):
        with patch('mta.mdm.supplier.setting', return_value='WithoutDestLoc'):
            field = next(f for f in moq.configuration('modify', source=object())[0]['fields'] if f['key']=='wc')
            self.assertFalse(field['visible']); self.assertFalse(field['isAdd'])


if __name__ == '__main__': unittest.main()
