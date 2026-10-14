import os
from datetime import datetime
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.mdm import skuloc_audit, skuloc_tasks
from mta.runtime.mdm_skuloc_models import (
    MdmSkuLocHistory, MdmSkuLocModifyRequested,
)
from mta.runtime.mdm_supplier_models import MdmSupplierConfiguration


class FakeQuerySet(list):
    def __init__(self, rows=(), manager=None):
        super().__init__(rows)
        self.manager = manager

    def update(self, **values):
        for row in self:
            for name, value in values.items():
                setattr(row, name, value)
        if self.manager is not None:
            self.manager.updates.append((tuple(row.pk for row in self), values))
        return len(self)

    def exclude(self, **kwargs):
        return FakeQuerySet([
            row for row in self
            if not all(getattr(row, name) == value for name, value in kwargs.items())
        ], self.manager)


class FakeManager:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.updates = []

    def filter(self, **kwargs):
        return FakeQuerySet([
            row for row in self.rows
            if all(getattr(row, name) == value for name, value in kwargs.items())
        ], self)


class AuditManager:
    def __init__(self):
        self.rows = []

    def bulk_create(self, rows):
        self.rows.extend(rows)


def decision_rows(count):
    rejected = {'sc': 'B6249', 'wc': 'DP020819', 'status': '4',
                'comments': 'Reject B'}
    approved = {'sc': 'A337', 'wc': 'DP020819', 'status': '3',
                'comments': 'Approve A'}
    if count == 999:
        return [rejected] + [approved] * 998
    return [rejected] + [approved] * 998 + [rejected]


class SkuLocReviewChunkOrderTests(unittest.TestCase):
    def setUp(self):
        self.source = object()
        self.actor = {'id': 3, 'name': 'Reviewer'}
        self.task = SimpleNamespace(MasterId='3', Actiontype=2)
        common = {'source': self.source, 'TaskId': 'task-1'}
        self.request_a = SimpleNamespace(pk=1, SKUCode='A337', WhCode='DP020819',
                                         Approved=False, **common)
        self.request_b = SimpleNamespace(pk=2, SKUCode='B6249', WhCode='DP020819',
                                         Approved=False, **common)
        self.history_a = SimpleNamespace(pk=11, SKUCode='A337', WhCode='DP020819',
                                         ApproverId='3', Status=None, Comments=None,
                                         ApprovedBy=None, **common)
        self.history_b = SimpleNamespace(pk=12, SKUCode='B6249', WhCode='DP020819',
                                         ApproverId='3', Status=None, Comments=None,
                                         ApprovedBy=None, **common)
        self.request_manager = FakeManager([self.request_a, self.request_b])
        self.history_manager = FakeManager([self.history_a, self.history_b])
        self.subtask_manager = FakeManager()
        self.payload = dict(taskId='task-1', data=decision_rows(1000),
                            product_permissions=[1], location_permissions=[10])

    def approve_patches(self):
        scope = [['A337', 'B6249'], ['DP020819']]
        return (
            patch.object(skuloc_tasks, 'header', return_value=self.task),
            patch.object(skuloc_tasks, '_scope', side_effect=scope),
            patch.object(skuloc_tasks, 'assigned', return_value=True),
            patch.object(MdmSkuLocModifyRequested, 'objects', self.request_manager),
            patch.object(MdmSkuLocHistory, 'objects', self.history_manager),
            patch.object(skuloc_tasks.MdmSubTask, 'objects', self.subtask_manager),
            patch.object(skuloc_tasks, '_copy_approved'),
            patch.object(skuloc_tasks, 'database_now',
                         return_value=datetime(2026, 7, 22, 8, 30)),
        )

    def test_1000_decisions_are_audited_as_reject_then_approve_per_chunk(self):
        audit_manager = AuditManager()
        class AuditRow:
            objects = audit_manager

            def __init__(self, **values):
                self.__dict__.update(values)
        audit_model = AuditRow
        patches = self.approve_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                patches[5], patches[6] as copy_approved, patches[7], \
                patch.object(skuloc_audit, 'enabled', return_value=True), \
                patch.dict(skuloc_audit.MODELS, {2: audit_model}), \
                patch.object(skuloc_audit, 'database_now',
                             return_value=datetime(2026, 7, 22, 8, 30)):
            skuloc_tasks.approve(self.source, self.payload, self.actor)

        ordered = [(row.SKUCode, row.ActionId) for row in audit_manager.rows]
        self.assertEqual(ordered,
                         [('B6249', 4)] + [('A337', 3)] * 998 + [('B6249', 4)])
        self.assertEqual(copy_approved.call_count, 2)
        self.assertTrue(self.request_a.Approved)
        self.assertTrue(self.request_b.Approved)  # Native rejected-Modify marking.
        self.assertEqual((self.history_a.Status, self.history_b.Status), ('3', '4'))

    def test_second_chunk_setting_failure_retains_prior_audit_and_business_effects(self):
        reviewed = MagicMock()
        patches = self.approve_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                patches[5], patches[6] as copy_approved, patches[7], \
                patch.object(skuloc_audit, 'enabled', side_effect=[True,
                    MdmSupplierConfiguration.DoesNotExist('missing')]), \
                patch.object(skuloc_audit, 'reviewed', reviewed):
            with self.assertRaises(MdmSupplierConfiguration.DoesNotExist):
                skuloc_tasks.approve(self.source, self.payload, self.actor)

        self.assertEqual(copy_approved.call_count, 2)
        self.assertEqual(len(reviewed.call_args_list), 1)
        self.assertEqual(reviewed.call_args.args[2], decision_rows(999))
        self.assertTrue(self.request_a.Approved)
        self.assertTrue(self.request_b.Approved)
        self.assertEqual((self.history_a.Status, self.history_b.Status), ('3', '4'))
        self.assertEqual(self.subtask_manager.updates, [])

    def test_conflicting_duplicate_decisions_are_denied_before_any_chunk_effect(self):
        self.payload['data'] = [
            {'sc': 'A337', 'wc': 'DP020819', 'status': '3', 'comments': 'Approve'},
            {'sc': 'A337', 'wc': 'DP020819', 'status': '4', 'comments': 'Reject'},
        ]
        patches = self.approve_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                patches[5], patches[6] as copy_approved, patches[7], \
                patch.object(skuloc_audit, 'enabled') as enabled:
            with self.assertRaisesRegex(ValueError,
                                        'native duplicate decision UPDATE is incomparable'):
                skuloc_tasks.approve(self.source, self.payload, self.actor)
        copy_approved.assert_not_called()
        enabled.assert_not_called()
        self.assertFalse(self.request_a.Approved)
        self.assertIsNone(self.history_a.Status)


if __name__ == '__main__':
    unittest.main()
