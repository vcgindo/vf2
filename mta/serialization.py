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


def canonical_parts(value):
    # Identical canonical JSON bytes without another full graph, JSON string,
    # and encoded-byte copy at once. Large temporal traces otherwise multiply
    # peak memory even though the calculation itself has already completed.
    def scalar(item):
        if isinstance(item, Decimal):
            return format(item, 'f')
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        raise TypeError('Unsupported canonical JSON value: ' + type(item).__name__)
    encoder = json.JSONEncoder(default=scalar, sort_keys=True,
                               separators=(',', ':'), allow_nan=False)
    for part in encoder.iterencode(value):
        yield part.encode()


def digest(value):
    checksum = hashlib.sha256()
    for part in canonical_parts(value):
        checksum.update(part)
    return checksum.hexdigest()
