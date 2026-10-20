"""Lossless storage representation shared by calculation, evidence and persistence."""
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from mta.row_sequences import RecordRows, CanonicalWireRows


def storage(value):
    if isinstance(value,RecordRows):
        if isinstance(value,CanonicalWireRows):
            return value
        return RecordRows(len(value),lambda:(storage(row) for row in value),
            getitem=lambda index:storage(value[index]))
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: storage(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [storage(v) for v in value]
    return value


def canonical_parts(value, *, ensure_ascii=True):
    # Identical canonical JSON bytes without another full graph, JSON string,
    # and encoded-byte copy at once. Large temporal traces otherwise multiply
    # peak memory even though the calculation itself has already completed.
    class RowList(list):
        def __init__(self,rows):self.rows=rows
        def __len__(self):return len(self.rows)
        def __iter__(self):return iter(self.rows)
    def scalar(item):
        if isinstance(item,RecordRows):return RowList(item)
        if isinstance(item, Decimal):
            return format(item, 'f')
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        raise TypeError('Unsupported canonical JSON value: ' + type(item).__name__)
    encoder = json.JSONEncoder(default=scalar, sort_keys=True, ensure_ascii=ensure_ascii,
                               separators=(',', ':'), allow_nan=False)
    for part in encoder.iterencode(value):
        yield part.encode()


def digest(value):
    checksum = hashlib.sha256()
    for part in canonical_parts(value):
        checksum.update(part)
    return checksum.hexdigest()


def rows_digest(rows):
    """Canonical list digest over a repeatable or streaming row source."""
    checksum=hashlib.sha256(b'[')
    for index,row in enumerate(rows):
        if index:checksum.update(b',')
        for part in canonical_parts(row):checksum.update(part)
    checksum.update(b']')
    return checksum.hexdigest()
