"""Lossless scalar cells; no settings selection or business interpretation.

Decimal text is its canonical ``str`` representation, preserving coefficient
precision, signed zero and exponent. ABSENT is not a scalar NULL: reading an
absent cell raises ValueError. Metadata is data and is never evaluated.
"""
from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math


def encode_scalar(value):
    """Return an exact type tag and canonical text, without coercion."""
    kind = type(value)
    if value is None:
        return 'null', None
    if kind is bool:
        return 'bool', 'true' if value else 'false'
    if kind is int:
        return 'int', str(value)
    if kind is float:
        if not math.isfinite(value):
            raise ValueError('Setting float must be finite')
        return 'float', repr(value)
    if kind is Decimal:
        if not value.is_finite():
            raise ValueError('Setting Decimal must be finite')
        return 'decimal', str(value)
    if kind is str:
        return 'text', value
    raise TypeError('Unsupported setting scalar type: ' + kind.__name__)


def decode_scalar(kind, text):
    """Decode only canonical encodings; whitespace/defaults are not inferred."""
    if type(kind) is not str:
        raise ValueError('Setting scalar tag must be text')
    if kind == 'null':
        if text is not None:
            raise ValueError('NULL setting scalar must have no text')
        return None
    if type(text) is not str:
        raise ValueError('Setting scalar requires exact text')
    try:
        if kind == 'bool':
            if text not in ('true', 'false'):
                raise ValueError('Noncanonical setting boolean')
            value = text == 'true'
        elif kind == 'int':
            value = int(text)
        elif kind == 'float':
            value = float(text)
        elif kind == 'decimal':
            value = Decimal(text)
        elif kind == 'text':
            value = text
        else:
            raise ValueError('Unknown setting scalar tag: ' + kind)
        if encode_scalar(value) != (kind, text):
            raise ValueError('Noncanonical setting scalar text')
    except (InvalidOperation, OverflowError) as error:
        raise ValueError('Invalid setting scalar text') from error
    return value


@dataclass(frozen=True)
class SettingCell:
    path: str
    module: str
    parameter: str
    ordinal: int
    value_kind: str
    value_text: str | None
    value_state: str = 'VALUE'

    def __post_init__(self):
        for name in ('path', 'module', 'parameter'):
            if type(getattr(self, name)) is not str:
                raise ValueError('Setting cell metadata must be exact text: ' + name)
        if type(self.ordinal) is not int or self.ordinal < 0:
            raise ValueError('Setting cell ordinal must be a nonnegative integer')
        if type(self.value_kind) is not str or (self.value_text is not None and type(self.value_text) is not str):
            raise ValueError('Setting cell requires exact scalar tag/text types')
        if type(self.value_state) is not str or self.value_state not in ('VALUE', 'NULL', 'ABSENT'):
            raise ValueError('Unknown setting cell value state')
        if self.value_state == 'ABSENT':
            if self.value_kind != 'absent' or self.value_text is not None:
                raise ValueError('ABSENT setting cell requires absent tag and no text')
        elif self.value_state == 'NULL':
            if self.value_kind != 'null' or self.value_text is not None:
                raise ValueError('NULL setting cell requires null tag and no text')
        else:
            if self.value_kind == 'null':
                raise ValueError('NULL setting scalar requires explicit NULL state')
            decode_scalar(self.value_kind, self.value_text)

    def value(self):
        """Return the exact scalar; ABSENT deliberately raises rather than NULL."""
        if self.value_state == 'ABSENT':
            raise ValueError('ABSENT setting cell has no scalar value')
        return decode_scalar(self.value_kind, self.value_text)

    def as_dict(self):
        return {field.name: getattr(self, field.name) for field in fields(self)}

    @classmethod
    def from_value(cls, path, module, parameter, ordinal, value):
        kind, text = encode_scalar(value)
        return cls(path, module, parameter, ordinal, kind, text,
                   'NULL' if value is None else 'VALUE')

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict or set(value) != {field.name for field in fields(cls)}:
            raise ValueError('Exact setting cell fields required')
        return cls(**value)


def rows_digest(rows):
    """Hash canonical cell rows in supplied order, including duplicates/tags."""
    checksum = hashlib.sha256(b'[')
    for ordinal, row in enumerate(rows):
        cell = row if type(row) is SettingCell else SettingCell.from_dict(row)
        if ordinal:
            checksum.update(b',')
        checksum.update(json.dumps(cell.as_dict(), sort_keys=True, ensure_ascii=True,
                                   separators=(',', ':'), allow_nan=False).encode('utf-8'))
    checksum.update(b']')
    return checksum.hexdigest()


def set_path(root, path, value):
    """Replace an existing trusted dictionary path, copying only its ancestors.

    This internal helper does not parse user paths, create keys, traverse lists
    or copy unrelated populations. The caller owns the replacement value.
    """
    if type(path) is not tuple or not path or any(type(key) is not str for key in path):
        raise ValueError('Trusted path must be a nonempty tuple of text keys')
    owners = []
    current = root
    for key in path:
        if type(current) is not dict or key not in current:
            raise ValueError('Trusted setting dictionary path does not exist')
        owners.append((current, key))
        current = current[key]
    result = value
    for owner, key in reversed(owners):
        copied = owner.copy()
        copied[key] = result
        result = copied
    return result
