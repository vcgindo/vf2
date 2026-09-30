from collections import Counter
import json
from mta.application.r1_supplier_input import CHECKPOINT_TABLES, STAGES
from mta.application.r1_supplier_entry import SUPPLIER_STATE_FIELDS
def compare_supplier_validation(legacy, modern):
    for side in (legacy, modern):
        if not isinstance(side, dict) or set(side) != set(STAGES):
            raise ValueError("Incomplete supplier stage checkpoints")
        for stage in STAGES:
            checkpoint = side[stage]
            if (not isinstance(checkpoint, dict) or set(checkpoint) != {"outcome", "tables"}
                    or checkpoint["outcome"] not in {"APPLIED", "EARLY_RETURN", "SQL_ERROR"}
                    or set(checkpoint["tables"]) != set(CHECKPOINT_TABLES)):
                raise ValueError(f"Incomplete supplier checkpoint: {stage}")
            for table, fields in CHECKPOINT_TABLES.items():
                rows = checkpoint["tables"][table]
                if not isinstance(rows, list) or any(not isinstance(r, dict) or set(r) != set(fields) for r in rows):
                    raise ValueError(f"Incomplete supplier fields: {stage}/{table}")
    results = {}
    for stage in STAGES:
        a, b = legacy[stage], modern[stage]
        results[stage + ":outcome"] = {"status": "PASS" if a["outcome"] == b["outcome"] else "FAIL",
                                       "legacy": a["outcome"], "modern": b["outcome"]}
        for table in CHECKPOINT_TABLES:
            left, right = a["tables"][table], b["tables"][table]
            bag = lambda rows: Counter(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows)
            x, y = bag(left), bag(right)
            results[stage + ":" + table] = {
                "status": "PASS" if x == y else "FAIL", "legacy_rows": len(left), "modern_rows": len(right),
                "legacy_only": [json.loads(r) for r in (x - y).elements()],
                "modern_only": [json.loads(r) for r in (y - x).elements()],
            }
    return results
def compare_supplier_state(legacy, modern):
    for side in (legacy, modern):
        if set(side) != set(SUPPLIER_STATE_FIELDS):
            raise ValueError("Incomplete supplier state tables")
        for table, fields in SUPPLIER_STATE_FIELDS.items():
            if not isinstance(side[table], list) or any(not isinstance(r, dict) or set(r) != set(fields) for r in side[table]):
                raise ValueError("Incomplete supplier state fields")
    results = {}
    for table in SUPPLIER_STATE_FIELDS:
        a, b = legacy[table], modern[table]
        bag = lambda rows: Counter(json.dumps(r, sort_keys=True) for r in rows)
        x, y = bag(a), bag(b)
        results[table] = {"status": "PASS" if x == y else "FAIL", "legacy_rows": len(a), "modern_rows": len(b),
            "legacy_only": [json.loads(r) for r in (x - y).elements()], "modern_only": [json.loads(r) for r in (y - x).elements()]}
    return results
