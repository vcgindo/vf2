"""Observer failures must not lose completed action timing or replay actions."""
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from tools.action_measurement import ActionMeasurement


class Connection:
    @contextmanager
    def execute_wrapper(self, wrapper):
        self.query = lambda sql: wrapper(lambda *args: None, sql, None, False, {})
        yield


class ActionMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/"action.jsonl"
        self.connection = Connection()

    def records(self):
        return [json.loads(line) for line in self.path.read_text().splitlines()]

    def test_post_commit_assertion_cannot_erase_measurement(self):
        calls = []
        def submit():
            calls.append("committed")
            self.connection.query("SELECT 1")
            return object()
        with self.assertRaises(AssertionError):
            with ActionMeasurement(self.path, {"run": uuid4()}) as record:
                record.submit(self.connection, submit)
                # Verify the record is durable before the caller's audit runs.
                saved = self.records()[-1]
                self.assertEqual(saved["stage"], "submit_returned")
                self.assertEqual(saved["sql_statements"], {"SELECT": 1})
                raise AssertionError("later preservation check")
        self.assertEqual(calls, ["committed"])
        self.assertIn("submit_returned", [v["stage"] for v in self.records()])

    def test_serialization_failure_after_submit_preserves_scalar_timing(self):
        with self.assertRaises(TypeError):
            with ActionMeasurement(self.path, {}) as record:
                record.submit(self.connection, lambda: None)
                record.record("audit", unsupported=object())
        self.assertEqual(self.records()[-2]["stage"], "submit_returned")

    def test_identity_types_are_explicit_and_unknown_setup_prevents_execution(self):
        with self.assertRaises(TypeError):
            ActionMeasurement(self.path, {"unknown": object()})
        self.assertFalse(self.path.exists())
        with ActionMeasurement(self.path, {"id": uuid4(), "amount": Decimal("1.00"),
                                          "day": date(2026, 10, 24)}):
            pass
        saved = self.records()[0]["identity"]
        self.assertEqual(saved["amount"], {"type": "decimal", "value": "1.00"})
        self.assertEqual(saved["day"]["type"], "date")

    def test_existing_receipt_and_second_submit_refuse_without_calling_action(self):
        calls = []
        with ActionMeasurement(self.path, {}) as record:
            record.submit(self.connection, lambda: calls.append(1))
            with self.assertRaises(RuntimeError):
                record.submit(self.connection, lambda: calls.append(2))
        with self.assertRaises(FileExistsError):
            ActionMeasurement(self.path, {})
        self.assertEqual(calls, [1])

    def test_action_exception_is_recorded_once_and_not_retried(self):
        with self.assertRaises(ValueError):
            with ActionMeasurement(self.path, {}) as record:
                record.submit(self.connection, lambda: (_ for _ in ()).throw(ValueError("refused")))
        self.assertEqual([v["stage"] for v in self.records()].count("submit_started"), 1)
        self.assertIn("submit_raised", [v["stage"] for v in self.records()])

    def test_failed_initial_fsync_prevents_submit(self):
        with patch("tools.action_measurement.os.fsync", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                ActionMeasurement(self.path, {})


if __name__ == "__main__":
    unittest.main()
