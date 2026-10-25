"""Actual BPR processed-table exports; no archive, readiness or native claim."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

from tests import test_scoped_pick_files_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class ScopedInputSourceTests(unittest.TestCase):
    for _name in ('setUp', 'rollback', 'owner', 'accept', 'bpr'):
        locals()[_name] = getattr(fixtures.ScopedPickFileTests, _name)

    def captured(self):
        from tests.test_h3_daily_integration import frame
        from mta.application.operational_capture import CAPTURE_POLICY
        from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY
        value = deepcopy(frame())
        value['profile'].update(operational_sources=CAPTURE_POLICY,
                                operational_input_sources=INPUT_CAPTURE_POLICY)
        with patch('tests.test_h3_daily_integration.frame', return_value=value):
            self.bpr()

    def export(self, **overrides):
        from django.db import connection
        from mta.runtime.scoped_input_source import exports
        arguments = dict(expected_digest=self.receipt.digest, action_revision=0,
                         importer_database=connection.settings_dict['NAME'])
        arguments.update(overrides)
        return exports(self.receipt.pk, **arguments)

    def test_complete_exports_equal_actual_producer_and_remain_read_only(self):
        from django.db import connection
        from mta.application.operational_inputs import PHYSICAL_TABLES
        from mta.application.operational_sqlcmd import input_table_bytes
        from mta.application.operational_upload_logs import _schema
        self.captured()
        expected = {connection.settings_dict['NAME'] + '_' + name + '.CSV':
            input_table_bytes(_schema['tables']['Importer/' + name],
                             self.phase.operational_input_tables[name]) for name in PHYSICAL_TABLES}
        before = [(str(r.pk), r.digest) for r in self.run.phase_acceptances.all()]

        def readonly(execute, sql, params, many, context):
            self.assertEqual(sql.lstrip().split(None, 1)[0].upper(), 'SELECT')
            return execute(sql, params, many, context)

        with connection.execute_wrapper(readonly), \
                patch('mta.temporal.chain.produce_bpr', side_effect=AssertionError('BPR replay')), \
                patch('mta.runtime.phase_state.read', side_effect=AssertionError('phase reconstruction')):
            self.assertEqual(self.export(), expected)
            self.assertEqual(self.export(), expected)
        self.assertEqual([(str(r.pk), r.digest) for r in self.run.phase_acceptances.all()], before)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, 'RUNNING')
        self.assertFalse(self.run.output_digest)
        self.assertFalse(self.run.commands.exists())

    def test_missing_policy_cannot_mean_empty_processed_inputs(self):
        self.bpr()
        with self.assertRaisesRegex(ValueError, 'capture policies'):
            self.export()

    def test_wrong_phase_digest_action_and_database_are_denied(self):
        from mta.runtime.scoped_input_source import exports
        from django.db import connection
        self.captured()
        for change in (dict(expected_digest='f' * 64), dict(action_revision=True),
                       dict(action_revision=-1), dict(action_revision=1),
                       dict(importer_database='VFTEST_Fresh_other_owner'),
                       dict(importer_database='../foreign'), dict(importer_database=None)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.export(**change)
        with self.assertRaisesRegex(ValueError, 'accepted BPR'):
            exports(self.pre_receipt.pk, expected_digest=self.pre_receipt.digest,
                    action_revision=0, importer_database=connection.settings_dict['NAME'])

    def test_action_change_during_export_is_rejected_before_return(self):
        self.captured()
        with patch('mta.runtime.scoped_input_source.revision', side_effect=[0, 1]), \
                self.assertRaisesRegex(ValueError, 'action cut changed'):
            self.export()
        self.run.refresh_from_db()
        self.assertFalse(self.run.commands.exists())
        self.assertEqual(self.run.status, 'RUNNING')


if __name__ == '__main__':
    unittest.main()
