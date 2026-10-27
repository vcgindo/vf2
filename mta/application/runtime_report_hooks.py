"""Explicit hook configuration, separate from native report definitions.

No production hook executor exists yet. Only a provenance-backed declared no-op
is representable here; an enabled site script needs its own qualified producer.
This declaration alone neither executes a hook nor authorizes a publication.
"""
from copy import deepcopy
import re

SCHEMA = 'fresh-runtime-report-hook-configuration-v1'


def configuration(value):
    from mta.runtime.production_scope_policy import HOOK_SCHEMA, hook
    if isinstance(value, dict) and value.get('schema') == HOOK_SCHEMA:
        return hook(value)
    if (type(value) is not dict or set(value) != {
            'schema', 'site_code', 'placement', 'mode', 'authority', 'source_sha256'}
            or value['schema'] != SCHEMA or value['placement'] != 'PostBPR'
            or value['mode'] != 'declared-no-op'
            or type(value['site_code']) is not str or not 1 <= len(value['site_code']) <= 100
            or not value['site_code'].strip() or '\0' in value['site_code']
            or type(value['authority']) is not str or not 1 <= len(value['authority']) <= 1000
            or not value['authority'].strip() or '\0' in value['authority']
            or type(value['source_sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', value['source_sha256']) is None):
        raise ValueError('Explicit qualified PostBPR no-op hook configuration required')
    return deepcopy(value)
