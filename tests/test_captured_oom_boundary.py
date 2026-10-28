"""Nonproducing OOM receipt/dispatch checks; actual SQL protocol is separate."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','captured-oom-unit-only')
import django
django.setup()

from mta.runtime import captured_recovery as recovery


def receipt():
    return dict(kind='ContainerOOM',container_id='a'*64,exit_code=137,
        memory_limit_bytes=8*1024**3,kernel_constraint='CONSTRAINT_MEMCG',evidence_sha256='b'*64)


class CapturedOomBoundaryTests(unittest.TestCase):
    def test_explicit_bounded_receipt_is_copied_and_default_is_unchanged(self):
        source=receipt()
        actual=recovery._interruption_receipt(source,original=True)
        self.assertEqual(actual,source);self.assertIsNot(actual,source)
        source['memory_limit_bytes']=1
        self.assertEqual(actual['memory_limit_bytes'],8*1024**3)
        self.assertIsNone(recovery._interruption_receipt(None,original=False))

    def test_invalid_and_unbounded_diagnostics_are_denied(self):
        invalid=[[],{},dict(receipt(),extra='not admitted'),dict(receipt(),kind='deadline'),
            dict(receipt(),exit_code=True),dict(receipt(),exit_code=1),
            dict(receipt(),memory_limit_bytes=True),dict(receipt(),memory_limit_bytes=0),
            dict(receipt(),memory_limit_bytes=2**63),dict(receipt(),memory_limit_bytes=8.0),
            dict(receipt(),container_id='a'*12),dict(receipt(),container_id='A'*64),
            dict(receipt(),evidence_sha256='/secret/path'),dict(receipt(),kernel_constraint='unknown')]
        for value in invalid:
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'exact evidence'):
                recovery._interruption_receipt(value,original=True)
        with self.assertRaisesRegex(ValueError,'original captured owner'):
            recovery._interruption_receipt(receipt(),original=False)

    def test_historical_external_and_human_stop_failures_are_exactly_preserved(self):
        for human_stop,label,message in ((False,'ExternalInterruption',
                'Explicit external-deadline interruption reconciled; immutable input retained'),
                (True,'HumanInterruption','Explicit human-stop interruption reconciled; immutable input retained')):
            error,metadata=recovery._interruption_failure(None,human_stop=human_stop)
            self.assertIs(type(error),RuntimeError);self.assertEqual(str(error),message)
            self.assertEqual(metadata,dict(type=label,message='Original input retained; explicit distinct continuation'))

    def test_oom_cause_is_truthful_and_contains_only_the_bounded_evidence(self):
        value=recovery._interruption_receipt(receipt(),original=True)
        error,metadata=recovery._interruption_failure(value)
        self.assertIs(type(error),recovery.ContainerOOM)
        self.assertEqual(str(error),'Explicit container memory-limit OOM reconciled; immutable input retained')
        self.assertEqual(metadata,dict(type='ContainerOOM',
            message='Original input retained; explicit distinct continuation',interruption=value))

    def test_oom_cannot_combine_with_any_retained_recovery_mode_before_owner_read(self):
        from mta.runtime.models import CalculationRun
        for name in ('second_hop','finite_continuation','terminal_continuation','terminal_retry','one_additional_attempt'):
            with self.subTest(mode=name),patch.object(recovery.transaction,'get_autocommit',return_value=True), \
                    patch.object(CalculationRun.objects,'get') as get:
                with self.assertRaisesRegex(ValueError,'original captured owner'):
                    recovery.resume(origin_run_id='unused',execution_revision='unit-only',expected={},
                        archive_path='unused',interruption=receipt(),**{name:{}})
                get.assert_not_called()

    def test_existing_execute_day_dispatch_forwards_receipt_and_keeps_frozen_argument_denial(self):
        from mta.runtime.temporal import execute_day
        arguments=dict(origin_run_id='original',expected={'pins':'unchanged'},archive_path='sibling',
            interruption=receipt())
        with patch.object(recovery,'resume',return_value='delegated') as resume:
            self.assertEqual(execute_day(day=None,profile=None,execution_revision='explicit',
                _captured_retry=arguments),'delegated')
            resume.assert_called_once_with(execution_revision='explicit',**arguments)
            resume.reset_mock()
            with self.assertRaisesRegex(ValueError,'cannot replace its frozen native arguments'):
                execute_day(day={'replacement':'forbidden'},profile=None,execution_revision='explicit',
                    _captured_retry=arguments)
            resume.assert_not_called()
