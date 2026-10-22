"""Bounded v6 admission proofs without a database or daily calculation."""
from copy import copy
from inspect import signature
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID
import importlib, os
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','final-attempt-admission-unit-only')
import django
django.setup()

from mta.runtime import captured_input as ci
from mta.runtime.daily_feed_models import DailyFeedAttempt
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.serialization import digest


class FinalAttemptAdmissionTests(unittest.TestCase):
    def leaf(self):
        physical=SimpleNamespace(pk=UUID(int=1),input_manifest_digest='a'*64,
                                 input_digest='b'*64)
        leaf=SimpleNamespace(pk=UUID(int=10),status='FAILED',
            input_payload={'schema':ci.RETRY},input_manifest_digest='c'*64,
            input_digest=physical.input_digest,output_digest='',output_roster=[],
            production_digest='')
        origin_run=SimpleNamespace(pk=UUID(int=9))
        capture=SimpleNamespace(status='CAPTURED',origin=SimpleNamespace(run=origin_run))
        attempt=SimpleNamespace(attempt_id=UUID(int=10),status='FAILED',phase='CALCULATE',
                                accepted_facts={},recovery_origin_id=9)
        rows=[{'attempt':{'attempt_id':str(UUID(int=index+1))}}
              for index in range(9)]
        return physical,leaf,capture,attempt,rows

    def test_exact_failed_v5_has_sql_owned_ten_record_prefix(self):
        physical,leaf,capture,attempt,rows=self.leaf()
        cursor=MagicMock();cursor.__enter__.return_value.fetchone.return_value=['d'*64]
        with patch.object(ci,'terminal_origin',return_value=physical), \
                patch.object(MdmDailyInputCapture.objects,'select_related') as captures, \
                patch.object(DailyFeedAttempt.objects,'get',return_value=attempt), \
                patch.object(ci,'retry_prefix',return_value=(physical,rows,'e'*64)), \
                patch.object(ci,'_metadata',side_effect=lambda value:{'id':str(value.pk)} if value is leaf else {'owned':True}), \
                patch('django.db.connection.cursor',return_value=cursor):
            captures.return_value.get.return_value=capture
            resolved,complete,prefix=ci.final_prefix(leaf)
        self.assertIs(resolved,physical)
        self.assertEqual(len(complete),10)
        self.assertEqual(prefix,'d'*64)
        cursor.__enter__.return_value.execute.assert_called_once_with(
            'SELECT mta.final_capture_prefix_digest(%s)',[leaf.pk])

    def test_non_v5_status_outputs_and_bad_manifest_modes_are_denied(self):
        physical,leaf,capture,attempt,rows=self.leaf()
        for field,value in (('schema',ci.TERMINAL),('status','RUNNING'),
                            ('output_digest','nonempty'),('output_roster',['row']),
                            ('production_digest','nonempty')):
            candidate=copy(leaf)
            if field=='schema':candidate.input_payload={'schema':value}
            else:setattr(candidate,field,value)
            with self.subTest(field=field),patch.object(ci,'terminal_origin',return_value=physical), \
                    patch.object(MdmDailyInputCapture.objects,'select_related') as captures, \
                    patch.object(DailyFeedAttempt.objects,'get',return_value=attempt), \
                    patch.object(ci,'retry_prefix',return_value=(physical,rows,'e'*64)):
                captures.return_value.get.return_value=capture
                with self.assertRaises(ValueError):ci.final_prefix(candidate)
        run=SimpleNamespace(pk=UUID(int=11),execution_revision='native-final-attempt-'+'f'*40)
        with patch('mta.runtime.input_v3._live_identity',return_value={}), \
                patch.object(ci,'final_prefix',return_value=(physical,rows+[rows[0]],'d'*64)):
            value=ci.terminal_manifest(run,leaf,expected_prefix_digest='d'*64,
                packaged_source='f'*40,additional=True)
            self.assertEqual(value['schema'],ci.FINAL)
            self.assertEqual(value['execution_revision'],run.execution_revision)
            with self.assertRaises(ValueError):ci.terminal_manifest(run,leaf,
                expected_prefix_digest='d'*64,packaged_source='f'*40,retry=True,additional=True)

    def test_python_entry_requires_named_one_additional_attempt(self):
        from mta.runtime import captured_recovery
        resume=captured_recovery.resume
        self.assertIn('one_additional_attempt',signature(resume).parameters)
        with patch.object(captured_recovery.transaction,'get_autocommit',return_value=True), \
                self.assertRaisesRegex(ValueError,'cannot combine recovery modes'):
            resume(origin_run_id=str(UUID(int=1)),execution_revision='revision',expected={},
                archive_path='unused',terminal_retry={},one_additional_attempt={})

    def test_v6_cannot_be_used_by_the_older_reference_writer(self):
        with patch.object(ci,'validate',return_value={'schema':ci.FINAL}), \
                self.assertRaisesRegex(ValueError,'cannot supply another continuation'):
            ci._origin(SimpleNamespace(input_payload={}),second_allowed=True)

    def test_migration_is_one_fixed_v6_extension_and_preserves_v5_dispatch(self):
        migration=importlib.import_module('mta.runtime.migrations.0167_final_attempt_admission')
        sql=migration.SQL
        self.assertIn('row_count<>10 OR distinct_runs<>10',sql)
        self.assertIn('FOR i IN 0..9 LOOP',migration.final_admit)
        self.assertIn("WHEN i=0 THEN 'fresh-captured-input-reference-v5'",migration.final_admit)
        self.assertIn("WHEN i=1 THEN 'fresh-captured-input-reference-v4'",migration.final_admit)
        self.assertIn("WHEN i=2 THEN 'fresh-captured-input-reference-v3'",migration.final_admit)
        self.assertIn('mta.retry_capture_prefix_digest(P.run_id)',migration.final_admit)
        self.assertEqual(sql.count("IF child.input_payload->>'schema'='fresh-captured-input-reference-v6'"),1)
        self.assertIn("IF child.input_payload->>'schema'='fresh-captured-input-reference-v5'",sql)
        self.assertIn('WHERE P.depth<9 AND C.origin_id IS NOT NULL',sql)
        self.assertIn("input_payload->>'schema'='fresh-captured-input-reference-v6'",migration.REVERSE)


if __name__=='__main__':unittest.main()
