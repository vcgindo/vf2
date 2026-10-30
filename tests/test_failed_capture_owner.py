"""Narrow failed-capture admission retains the original input and failure."""
from copy import deepcopy
from datetime import date
import os
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'failed-capture-owner-unit-only')
import django
django.setup()

from mta.runtime import captured_recovery as service
from mta.runtime import captured_input
from mta.runtime.input_v3 import V3

SOURCE = 'b' * 40
REVISION = 'native-failed-capture-' + SOURCE
FAILURE = dict(type='TypeError', message='Immutable history row; create a transformed generation')


def owners():
    run = Obj(pk=uuid4(), predecessor_id=uuid4(), business_date=date(2026, 4, 9),
              status='FAILED', failure=dict(FAILURE), input_payload={'schema': V3},
              input_digest='3' * 64, input_manifest_digest='4' * 64)
    attempt = Obj(status='FAILED', error=dict(FAILURE), phase='VALIDATED', run_id=run.pk,
                  predecessor_id=run.predecessor_id, business_date=run.business_date,
                  accepted_facts={'accepted': True}, prepared_context={'context': True},
                  initialization=Obj(source_id=1))
    capture = Obj(run_id=run.pk, status='CAPTURED', origin_id=None, source_id=1)
    return run, attempt, capture


class FailedCaptureOwnerTests(unittest.TestCase):
    def test_exact_origin_retains_every_metadata_field(self):
        run, attempt, capture = owners()
        before = deepcopy((vars(run), vars(attempt), vars(capture)))
        release = dict(source_commit=SOURCE, manifest_sha256='a' * 64)
        with patch('release.native_identity.require_current', return_value=release) as current:
            self.assertEqual(service._failed_capture_owner(run, attempt, capture, REVISION), release)
            current.assert_called_once_with()
        self.assertEqual((vars(run), vars(attempt), vars(capture)), before)

    def test_foreign_changed_or_nonoriginal_failure_is_denied(self):
        variants = [('run', 'status', 'RUNNING'), ('run', 'failure', dict(FAILURE, message='other')),
                    ('run', 'input_payload', {'schema': captured_input.SCHEMA}),
                    ('attempt', 'status', 'RUNNING'), ('attempt', 'phase', 'CALCULATE'),
                    ('attempt', 'error', dict(FAILURE, type='ValueError')),
                    ('attempt', 'run_id', uuid4()), ('attempt', 'predecessor_id', uuid4()),
                    ('attempt', 'business_date', date(2026, 4, 8)),
                    ('attempt', 'accepted_facts', {}), ('attempt', 'prepared_context', {}),
                    ('capture', 'run_id', uuid4()), ('capture', 'status', 'CONSUMED'),
                    ('capture', 'origin_id', uuid4()), ('capture', 'source_id', 2)]
        for owner, field, value in variants:
            run, attempt, capture = owners()
            setattr(dict(run=run, attempt=attempt, capture=capture)[owner], field, value)
            with self.subTest(owner=owner, field=field), \
                    patch('release.native_identity.require_current') as current:
                with self.assertRaisesRegex(ValueError, 'exact original immutable-row failure'):
                    service._failed_capture_owner(run, attempt, capture, REVISION)
                current.assert_not_called()

    def test_revision_is_explicitly_bound_to_current_packaged_source(self):
        with patch('release.native_identity.require_current', return_value={'source_commit': SOURCE}):
            for revision in ('other', 'native-failed-capture-' + 'c' * 40):
                with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, 'packaged source'):
                    service._failed_capture_owner(*owners(), revision)

    def test_only_normal_failure_metadata_epoch_updates_are_admitted(self):
        expected = {'capture_cut': [10, 20, 30, 40, 50]}
        self.assertEqual(service._failed_capture_cut(expected), [10, 20, 31, 41, 50])
        self.assertEqual(expected, {'capture_cut': [10, 20, 30, 40, 50]})
        for cut in (None, (), [1] * 4, [1] * 6, [1, 2, -1, 4, 5], [1, 2, True, 4, 5]):
            with self.subTest(cut=cut), self.assertRaisesRegex(ValueError, 'sealed capture cut'):
                service._failed_capture_cut({'capture_cut': cut})

    def test_failed_mode_cannot_mix_with_any_interruption_or_other_recovery(self):
        for name, value in [('second_hop', {}), ('final_third_hop', True),
                            ('final_interrupted_fourth_hop', True), ('final_failed_fifth_hop', True),
                            ('final_interrupted_sixth_hop', True), ('finite_continuation', {}),
                            ('terminal_continuation', {}), ('terminal_retry', {}),
                            ('one_additional_attempt', {}), ('interruption', {})]:
            with self.subTest(mode=name), self.assertRaisesRegex(ValueError, 'combine continuation modes'):
                service.resume(origin_run_id=str(uuid4()), execution_revision=REVISION,
                               expected={}, archive_path='/unused', failed_capture=True, **{name: value})
        for value in (1, None, 'true'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'combine continuation modes'):
                service.resume(origin_run_id=str(uuid4()), execution_revision=REVISION,
                               expected={}, archive_path='/unused', failed_capture=value)

    def test_existing_capture_manifest_retains_exact_original_content_root(self):
        run, _, _ = owners()
        child = Obj(pk=uuid4())
        with patch('mta.runtime.input_v3._live_identity', return_value={'owner_id': str(child.pk)}):
            body = captured_input.manifest(child, run)
        self.assertEqual(body['schema'], captured_input.SCHEMA)
        self.assertEqual(body['content_digest'], run.input_digest)
        self.assertEqual(body['origin_run_id'], str(run.pk))
        self.assertEqual(body['origin_manifest_digest'], run.input_manifest_digest)
        self.assertEqual(body['images'], {})
        self.assertEqual(run.status, 'FAILED')
        self.assertEqual(run.failure, FAILURE)


if __name__ == '__main__':
    unittest.main()
