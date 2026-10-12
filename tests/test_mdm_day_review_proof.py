"""HTTP200 is insufficient when native review handlers swallow effect failures."""
from copy import deepcopy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from tools.mdm_approval_day_workflow import MODELS, REVIEW_TIME, verify_review


class ReviewProofTests(unittest.TestCase):
    def test_all_exact_models_and_shared_columns_exist(self):
        from django.apps import apps
        for names in MODELS.values():
            for name in names:
                model = apps.get_model('fresh_mta', name)
                self.assertIsNotNone(model._meta.get_field('source'))

    def test_caught_queue_history_or_completion_failures_cannot_pass(self):
        requested = dict(id=1, source=1, SKUCode='6120', WhCode='MT0513',
                         NewNorm=500, Approved=True, Reverted=False)
        history = dict(Status='3', ApprovedBy='3', ApproverId='3')
        effect = dict(id=5, source=1, SKUCode='6120', WhCode='MT0513',
                      NewNorm=500, Approved=True, revision=1)
        sub = dict(ApproverId='3', TaskStatus='2',
                   ApprovedOrRejectedDate=REVIEW_TIME.strftime('%d/%m/%Y %I:%M %p'))
        with patch('mta.runtime.mdm_models.MdmTask.objects.get',
                   return_value=SimpleNamespace(TaskStatus='1')), \
             patch('mta.runtime.mdm_models.MdmSubTask.objects.filter'), \
             patch('tools.mdm_approval_day_workflow.typed_rows', return_value=[sub]), \
             patch('tools.mdm_approval_day_workflow.complete_effect', return_value=[effect]) as full, \
             patch('tools.mdm_approval_day_workflow.task_rows') as rows:
            rows.return_value = ([requested], [history], [effect])
            self.assertEqual(verify_review(None, 13, 'task', [])['effect'][0]['NewNorm'], 500)
            for r, h, e, s in (
                (requested, history, [], sub),
                (requested, history, [{**effect, 'NewNorm': 499}], sub),
                (requested, history, [{**effect, 'revision': 0}], sub),
                (requested, {**history, 'Status': '1'}, [effect], sub),
                ({**requested, 'Approved': False}, history, [effect], sub),
                (requested, history, [effect], {**sub, 'TaskStatus': '1'}),
            ):
                rows.return_value = ([deepcopy(r)], [deepcopy(h)], deepcopy(e))
                with patch('tools.mdm_approval_day_workflow.typed_rows', return_value=[s]), \
                        self.assertRaises(ValueError):
                    verify_review(None, 13, 'task', [])
            rows.return_value = ([requested], [history], [effect])
            full.return_value = [effect, {**effect, 'id': 6, 'SKUCode': 'unrelated'}]
            with self.assertRaisesRegex(ValueError, 'unrelated'):
                verify_review(None, 13, 'task', [])


if __name__ == '__main__':
    unittest.main()
