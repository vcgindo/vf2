"""Lossless storage representation shared by calculation, evidence and persistence."""
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json


def storage(value):
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: storage(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [storage(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(storage(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
