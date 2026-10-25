"""Explicit empty RuntimeReports configuration for newly owned scoped tests.

This declaration does not certify production configuration, other downloads or
site hooks. Nonempty report rosters need their applicable query/template owner.
The existing captured scope request owns these bounded metadata bytes.
"""
from copy import deepcopy
import hashlib
import json

from mta.serialization import digest

SCHEMA='fresh-scoped-test-runtime-reports-v1'
REFERENCE='fresh-scoped-runtime-reports-reference-v1'
LIMIT=4096


def configuration(value):
    if (type(value) is not dict or set(value)!={'schema','purpose','provenance','RuntimeReports'}
            or value['schema']!=SCHEMA or value['purpose']!='owned-scoped-test'
            or type(value['provenance']) is not str or not 1<=len(value['provenance'])<=1000
            or not value['provenance'].strip()
            or type(value['RuntimeReports']) is not list or value['RuntimeReports']):
        raise ValueError('Explicit authorized empty test RuntimeReports roster required')
    return deepcopy(value)


def validate(value):
    from mta.runtime.ingestion_context import sha
    if type(value) is not dict or set(value)!={'schema','sha256','configuration','configuration_digest'} or value['schema']!=REFERENCE:
        raise ValueError('Complete scoped RuntimeReports reference required')
    sha(value['sha256'])
    checked=configuration(value['configuration'])
    if value['configuration_digest']!=digest(checked):
        raise ValueError('Scoped RuntimeReports configuration digest differs')
    return deepcopy(value)


def decode(raw,expected_sha256):
    from mta.mdm.initialization_contract import object_pairs,sha
    sha(expected_sha256,'RuntimeReports file')
    if type(raw) is not bytes or not 0<len(raw)<=LIMIT or hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('Bounded RuntimeReports file bytes differ')
    def nonfinite(value):raise ValueError('Nonfinite RuntimeReports value')
    checked=configuration(json.loads(raw,object_pairs_hook=object_pairs,parse_constant=nonfinite))
    return validate(dict(schema=REFERENCE,sha256=expected_sha256,configuration=checked,configuration_digest=digest(checked)))


def load(path,expected_sha256):
    # Read at most the bound even when the supplied file is unexpectedly large.
    with path.open('rb') as stream:raw=stream.read(LIMIT+1)
    return decode(raw,expected_sha256)


def require_test_database():
    """Additional restriction, after the native installer's ownership check."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        name=cursor.fetchone()[0]
    if not name.lower().startswith('vftest_fresh_'):
        raise ValueError('Empty test RuntimeReports declaration requires an owned VFTEST_Fresh database')


def status(value):
    if value is None:return dict(configured=False)
    checked=validate(value)
    return dict(configured=True,purpose='owned-scoped-test',row_count=0,
        sha256=checked['sha256'],configuration_digest=checked['configuration_digest'])
