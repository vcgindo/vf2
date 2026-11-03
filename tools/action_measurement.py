"""Durable evidence for one explicitly authorized action; never retries it.

This is observer tooling, not an application transaction or approval owner.
The caller must use the real submit boundary and perform independent audits.
"""
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import time
from uuid import UUID


def _json_value(value):
    # Explicit supported evidence types; do not silently stringify unknown data.
    if isinstance(value, UUID):
        return {"type": "uuid", "value": str(value)}
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": str(value)}
    if isinstance(value, (datetime, date)):
        return {"type": type(value).__name__, "value": value.isoformat()}
    raise TypeError("Unsupported evidence type: " + type(value).__name__)


class ActionMeasurement:
    """Reserve a new evidence file before work; fsync each boundary immediately."""

    def __init__(self, path, identity):
        self.path = Path(path)
        # Serialize before reserving the path: invalid setup must not run work.
        initial = self._encode({"stage": "prepared", "identity": identity})
        self.stream = self.path.open("x", encoding="utf-8")
        self.started = False
        try:
            self._write(initial)
        except BaseException:
            self.stream.close()
            raise

    @staticmethod
    def _encode(value):
        return json.dumps(value, default=_json_value, allow_nan=False,
                          separators=(",", ":")) + "\n"

    def _write(self, encoded):
        self.stream.write(encoded)
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def record(self, stage, **values):
        self._write(self._encode({"stage": stage,
            "recorded_utc": datetime.now(timezone.utc).isoformat(), **values}))

    def submit(self, connection, call):
        if self.started:
            raise RuntimeError("An action measurement cannot submit twice")
        self.started = True
        self.record("submit_started")
        statements = Counter()

        def count(execute, sql, params, many, context):
            words = sql.lstrip().split(None, 1)
            statements[words[0].upper() if words else "EMPTY"] += 1
            return execute(sql, params, many, context)

        start = time.perf_counter()
        cpu = time.process_time()
        try:
            with connection.execute_wrapper(count):
                result = call()
        except BaseException as error:
            self.record("submit_raised", elapsed_seconds=time.perf_counter()-start,
                        cpu_seconds=time.process_time()-cpu,
                        sql_statements=dict(statements), error_type=type(error).__name__)
            raise
        # Save scalar measurements BEFORE serializing results or auditing state.
        self.record("submit_returned", elapsed_seconds=time.perf_counter()-start,
                    cpu_seconds=time.process_time()-cpu, sql_statements=dict(statements),
                    qualification="Submit returned; independent correctness audit pending")
        return result

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        try:
            if error is not None:
                self.record("observer_or_submit_failed", error_type=kind.__name__)
        finally:
            self.stream.close()
