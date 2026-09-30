from collections import Counter
import json
from mta.application.r1_daily_input import CHECKPOINT_TABLES, STAGES
def compare_daily_validation(legacy, modern):
    for side in (legacy, modern):
        if not isinstance(side, dict) or set(side) != set(STAGES):
            raise ValueError("Incomplete daily stage checkpoints")
        for stage in STAGES:
            c = side[stage]
            if (not isinstance(c, dict) or set(c) != {"outcome", "tables"}
                    or c["outcome"] not in {"APPLIED", "EARLY_RETURN", "SQL_ERROR"}
                    or set(c["tables"]) != set(CHECKPOINT_TABLES)):
                raise ValueError(f"Incomplete daily checkpoint: {stage}")
            for table, fields in CHECKPOINT_TABLES.items():
                rows = c["tables"][table]
                if not isinstance(rows, list) or any(not isinstance(r, dict) or set(r) != set(fields) for r in rows):
                    raise ValueError(f"Incomplete daily fields: {stage}/{table}")
    results = {}
    for stage in STAGES:
        a, b = legacy[stage], modern[stage]
        results[stage + ":outcome"] = {"status": "PASS" if a["outcome"] == b["outcome"] else "FAIL",
                                       "legacy": a["outcome"], "modern": b["outcome"]}
        for table in CHECKPOINT_TABLES:
            left, right = a["tables"][table], b["tables"][table]
            bag = lambda rows: Counter(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows)
            x, y = bag(left), bag(right)
            results[stage + ":" + table] = {"status": "PASS" if x == y else "FAIL", "legacy_rows": len(left), "modern_rows": len(right),
                "legacy_only": [json.loads(r) for r in (x - y).elements()], "modern_only": [json.loads(r) for r in (y - x).elements()]}
    return results
