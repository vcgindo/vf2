"""One typed-input admission per pure traversal, with independent consumers."""
import os
import unittest
from copy import deepcopy
from uuid import uuid4
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from mta.presentation import request_scope
from mta.runtime import input_storage, input_v3
from mta.runtime.models import CalculationRun
from mta.serialization import digest
from mta.row_sequences import RecordRows
from test_remark_validation_scope import Database


class InputValidationAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.database = Database()
        self.connection = patch('django.db.connection', self.database)
        self.connection.start(); self.addCleanup(self.connection.stop)
        self.run = CalculationRun(id=uuid4(), kind='DAILY_CHAIN', status='RUNNING',
            input_digest='d'*64, production_manifest={})
        self.identity = dict(database_name='owned', database_oid=1, source_digest='a'*64,
            owner_kind='run', owner_id=str(self.run.pk))
        self.run.input_payload = dict(schema=input_v3.V3, content_digest=self.run.input_digest,
            identity=self.identity, aliases={}, images={'values': {'image': 'values'}},
            tree={'object': [['profile', {'object': [['values', {'scalars': 'values'}]]}],
                             ['scope_request', {'scalar': 'accepted'}]]})
        self.run.input_manifest_digest = digest(self.run.input_payload)
        self.identity_check = patch.object(input_v3, '_identity', return_value=self.identity)
        self.verify = self.identity_check.start(); self.addCleanup(self.identity_check.stop)
        self.images = patch.object(input_storage, 'load_image',
            return_value=[{'value': 1}, {'value': None}, {'value': 1}])
        self.reader = self.images.start(); self.addCleanup(self.images.stop)
        self.normal_reader = patch('mta.runtime.relational_state.load_image', self.reader)
        self.normal_reader.start(); self.addCleanup(self.normal_reader.stop)

    def read(self, owner=None, components=('profile',), **kwargs):
        return input_storage.read_input(owner or self.run, components=components, **kwargs)

    def test_components_are_admitted_once_and_consumers_do_not_share_mutable_rows(self):
        with request_scope.remark_validation(), request_scope.validation_reads():
            first = self.read()
            first['profile']['values'][0] = 999
            second = self.read(deepcopy(self.run))
            self.assertEqual(second, {'profile': {'values': [1, None, 1]}})
            self.assertEqual(self.reader.call_count, 1)
            self.assertEqual(self.verify.call_count, 1)
            self.assertEqual(self.read(components=('scope_request',)), {'scope_request': 'accepted'})
            self.assertEqual(self.verify.call_count, 1)

    def test_new_phase_and_connection_revalidate_and_failures_are_not_reused(self):
        with request_scope.remark_validation():
            with request_scope.validation_reads():
                self.read(); self.read()
                self.database.connection = type('Physical', (), {'closed': False})()
                self.read()
                self.assertEqual(self.reader.call_count, 2)
            self.reader.side_effect = ValueError('corrupt physical image')
            with request_scope.validation_reads():
                for _ in range(2):
                    with self.assertRaisesRegex(ValueError, 'corrupt physical image'): self.read()
            self.assertEqual(self.reader.call_count, 4)

    def test_changed_caller_manifest_or_preparation_cannot_inherit_admission(self):
        with request_scope.remark_validation(), request_scope.validation_reads():
            self.read()
            damaged = deepcopy(self.run)
            damaged.input_payload['tree']['object'][1][1]['scalar'] = 'forged'
            with self.assertRaisesRegex(ValueError, 'manifest identity drift'): self.read(damaged)
            self.verify.side_effect = ValueError('invalid preparation claim')
            damaged = deepcopy(self.run)
            damaged.production_manifest = {'ingestion_preparation': {'initialization_id': 'forged'}}
            with self.assertRaisesRegex(ValueError, 'invalid preparation claim'): self.read(damaged)
            damaged = deepcopy(self.run); damaged._state.db = 'another_alias'
            with self.assertRaisesRegex(ValueError, 'invalid preparation claim'): self.read(damaged)

    def test_outside_validation_and_custom_resolvers_remain_independent(self):
        self.read(); self.read()
        with request_scope.read_request('/api/GetBPRData'): self.read(); self.read()
        self.assertEqual(self.verify.call_count, 4)
        with request_scope.remark_validation(), request_scope.validation_reads():
            self.read(image_reader=self.reader, identity_resolver=lambda owner: self.identity)
            self.read(image_reader=self.reader, identity_resolver=lambda owner: self.identity)
        self.assertEqual(self.verify.call_count, 6)

    def test_writes_end_reuse_and_large_immutable_rows_are_not_copied(self):
        with request_scope.remark_validation():
            with request_scope.validation_reads():
                self.read()
                with self.assertRaises(ValueError): self.database.execute('UPDATE source SET revision=2')
            self.database.execute('UPDATE source SET revision=2')
            with request_scope.validation_reads(): self.read()
        self.assertEqual(self.verify.call_count, 2)
        lazy = RecordRows(10001, lambda: ({'x': n} for n in range(10001)))
        with patch.object(input_v3, '_input_reader', return_value=lambda components: {'rows': lazy}) as read:
            with request_scope.remark_validation(), request_scope.validation_reads():
                self.assertIs(self.read()['rows'], lazy)
                self.assertIs(self.read()['rows'], lazy)
                self.assertEqual(read.call_count, 1)


if __name__ == '__main__': unittest.main()
