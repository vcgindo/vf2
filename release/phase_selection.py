"""Shared, bounded phase-anchor codec; no application or database imports."""
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID

SCHEMA = 'fresh-test-bpr-selection-v1'
DBM_SCHEMA = 'fresh-test-dbm-selection-v1'
FIELDS = frozenset(('schema', 'run_id', 'phase_id', 'phase_digest', 'snapshot_digest',
    'input_digest', 'input_manifest_digest', 'capture_digest', 'configuration_digest',
    'native_digest', 'permissions_sha256', 'recipe_digest', 'business_date', 'selection_digest'))


def validate(value):
    if type(value) is not dict or set(value) != FIELDS or value['schema'] not in (SCHEMA,DBM_SCHEMA):
        raise ValueError('Complete explicit test phase selection required')
    if any(type(v) is not str for v in value.values()):
        raise ValueError('Phase selection fields must be strings')
    for field in ('run_id', 'phase_id'):
        UUID(value[field])
    if date.fromisoformat(value['business_date']).isoformat() != value['business_date']:
        raise ValueError('Phase selection date differs')
    for field in FIELDS - {'schema', 'run_id', 'phase_id', 'business_date'}:
        if not re.fullmatch('[0-9a-f]{64}', value[field]):
            raise ValueError('An exact SHA256 identity is required')
    raw = json.dumps({k:v for k,v in value.items() if k!='selection_digest'},
        sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()
    if value['selection_digest'] != hashlib.sha256(raw).hexdigest():
        raise ValueError('Phase selection checksum differs')
    return value


def decode(raw):
    if len(raw) > 8192:
        raise ValueError('Phase selection exceeds bound')
    def unique(pairs):
        value = {}
        for key,item in pairs:
            if key in value:
                raise ValueError('Duplicate phase selection field')
            value[key] = item
        return value
    return validate(json.loads(raw, object_pairs_hook=unique))


def read(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(8193)
    return decode(raw)
