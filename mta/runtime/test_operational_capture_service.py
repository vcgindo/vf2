"""Service-level operational capture protocol; calculation is deliberately stubbed."""
from copy import deepcopy
import unittest
import uuid
from unittest.mock import patch

from django.test import override_settings

from mta.application.operational_capture import CAPTURE_POLICY, capture_rows
from mta.runtime.models import CalculationRun
from mta.runtime.operational_source import read_source
from mta.runtime.operational_source_models import (
    OperationalCaptureAuthorization,
    OperationalCalculationSource,
)
from mta.runtime import test_temporal as temporal_fixture
from tests.test_operational_capture import calculated


class OperationalCaptureServiceProtocol(unittest.TestCase):
    """Runs against the existing owned protocol database without Django flush."""

    setUp = temporal_fixture.TemporalPersistenceTest.setUp
    run_day = temporal_fixture.TemporalPersistenceTest.run_day

    def calculate(self, *args):
        result = temporal_fixture.TemporalPersistenceTest.calculate(self, *args)
        sources = calculated()
        for row in sources[0]["rows"]:
            row.update(parent_location_code=None, norm_req_red=None)
        self.live_sources = deepcopy(sources)
        result["CalculationOutputs"].extend(sources)
        return result

    def reset_request(self, *, opted_in, identity=None, revision=None):
        self.profile = {"delivery": {"site_code": "VECTORFLOW-DEMO"}}
        if opted_in:
            self.profile["operational_sources"] = CAPTURE_POLICY
        self.opening = {
            "identity": identity or "operational-capture-" + uuid.uuid4().hex,
            "opening_date": "2026-06-05",
            "state": deepcopy(self.state),
        }
        self.revision = revision or "capture-service-" + uuid.uuid4().hex

    def test_opt_in_opt_out_failure_retry_and_exact_replay(self):
        settings = override_settings(VF_MTA_DAILY_PUBLICATION=False)
        settings.enable()
        self.addCleanup(settings.disable)

        self.reset_request(opted_in=True)
        opted_in = self.run_day()
        expected = capture_rows(self.live_sources)
        self.assertEqual(read_source(opted_in), expected)
        self.assertEqual(expected["requirement_bands"][0],
                         expected["requirement_bands"][1])
        self.assertIsNone(expected["requirement_bands"][0]["ParentWhCode"])
        self.assertIsNone(expected["requirement_bands"][0]["NormReqRed"])
        self.assertTrue(OperationalCaptureAuthorization.objects.filter(run=opted_in).exists())

        self.reset_request(opted_in=False)
        opted_out = self.run_day()
        self.assertFalse(OperationalCaptureAuthorization.objects.filter(run=opted_out).exists())
        self.assertFalse(OperationalCalculationSource.objects.filter(run=opted_out).exists())

        retry_identity = "operational-capture-retry-" + uuid.uuid4().hex
        self.reset_request(opted_in=True, identity=retry_identity,
                           revision="capture-failed-" + uuid.uuid4().hex)
        with patch("mta.presentation.expedite_storage.write_expedite",
                   side_effect=RuntimeError("injected after operational capture")):
            with self.assertRaisesRegex(RuntimeError, "after operational capture"):
                self.run_day()
        failed = CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(failed.status, "FAILED")
        self.assertTrue(OperationalCaptureAuthorization.objects.filter(run=failed).exists())
        self.assertFalse(OperationalCalculationSource.objects.filter(run=failed).exists())

        self.revision = "capture-retry-" + uuid.uuid4().hex
        retry = self.run_day()
        self.assertNotEqual(retry.pk, failed.pk)
        self.assertEqual(retry.input_digest, failed.input_digest)
        self.assertTrue(OperationalCaptureAuthorization.objects.filter(run=retry).exists())
        retry_rows = read_source(retry)
        self.assertEqual(retry_rows, capture_rows(self.live_sources))
        calculation_calls = len(self.seen)
        source_count = OperationalCalculationSource.objects.filter(run=retry).count()

        replay = self.run_day()
        self.assertEqual(replay.pk, retry.pk)
        self.assertEqual(read_source(replay), retry_rows)
        self.assertEqual(len(self.seen), calculation_calls)
        self.assertEqual(OperationalCalculationSource.objects.filter(run=retry).count(),
                         source_count)
