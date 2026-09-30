from collections import Counter
import json
from mta.application.r1_importer_master import TABLE_COLUMNS, process_importer_master
def _bag(rows):
    return Counter(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows)
def compare_master_validation(legacy, modern):
    required = {"outcome", "tables", "rejects_added", "retired_events_added"}
    for side in (legacy, modern):
        if not required <= set(side) or set(side["tables"]) != set(TABLE_COLUMNS):
            raise ValueError("Incomplete raw-master checkpoint set")
        for table, fields in TABLE_COLUMNS.items():
            rows = side["tables"][table]
            if not isinstance(rows, list) or any(not isinstance(r, dict) or set(r) != set(fields) for r in rows):
                raise ValueError(f"Incomplete raw-master fields: {table}")
        for delta, table in (("rejects_added", "RejectedMaster"), ("retired_events_added", "RetiredNormsTbl")):
            if not isinstance(side[delta], list) or any(not isinstance(r, dict) or set(r) != set(TABLE_COLUMNS[table]) for r in side[delta]):
                raise ValueError(f"Incomplete raw-master delta fields: {delta}")
    results = {"outcome": {"status": "PASS" if legacy["outcome"] == modern["outcome"] else "FAIL",
                            "legacy": legacy["outcome"], "modern": modern["outcome"]}}
    for name, left, right in [(t, legacy["tables"][t], modern["tables"][t]) for t in TABLE_COLUMNS] + [
        (t, legacy[t], modern[t]) for t in ("rejects_added", "retired_events_added")
    ]:
        a, b = _bag(left), _bag(right)
        results[name] = {"status": "PASS" if a == b else "FAIL", "legacy_rows": len(left), "modern_rows": len(right),
                         "legacy_only": [json.loads(r) for r in (a - b).elements()], "modern_only": [json.loads(r) for r in (b - a).elements()]}
    return results
