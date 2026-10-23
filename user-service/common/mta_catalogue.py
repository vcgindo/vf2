# **DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""Explicit 3005 local delivery of MTA's registered permission definitions.

No effective grants are cached. Read and validate the small immutable metadata
on each use; identity DB queries still own user grants and revocation.
"""
import hashlib
import json
import os
from datetime import date
from pathlib import Path
from uuid import UUID

from rest_framework.exceptions import APIException


class CatalogueUnavailable(APIException):
    status_code = 503
    default_code = 'mta_catalogue_unavailable'


def enabled():
    value = os.environ.get('VF_MTA_LOCAL_PERMISSIONS', '')
    if value not in ('', '0', '1'):
        raise CatalogueUnavailable('invalid_local_catalogue_mode')
    return value == '1'


def _read(prefix, *, unique_keys=False):
    path, expected = (os.environ.get(prefix + suffix, '') for suffix in ('_FILE', '_SHA256'))
    if not path or not expected:
        raise CatalogueUnavailable('catalogue_binding_not_configured')
    try:
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise CatalogueUnavailable('catalogue_binding_checksum_mismatch')
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate selection field')
                result[key] = value
            return result
        return json.loads(raw, object_pairs_hook=unique if unique_keys else None)
    except (OSError, ValueError) as exc:
        raise CatalogueUnavailable('catalogue_binding_unreadable') from exc


def payload():
    """Match presentation.views.all_permissions without using a report worker."""
    try:
        catalogue = _read('VF_MTA_PERMISSIONS')
        checksum = os.environ['VF_MTA_PERMISSIONS_SHA256']
        fixture_file, fixture_sha = (os.environ.get('VF_MTA_FIXTURE' + suffix, '')
                                     for suffix in ('_FILE', '_SHA256'))
        if bool(fixture_file) != bool(fixture_sha):
            raise CatalogueUnavailable('incomplete_fixture_catalogue_selection')
        fixture = bool(fixture_file or fixture_sha)
        native_file, native_sha = (os.environ.get('VF_MTA_SELECTION' + suffix, '')
                                  for suffix in ('_FILE', '_SHA256'))
        if bool(native_file) != bool(native_sha):
            raise CatalogueUnavailable('incomplete_native_catalogue_selection')
        native = bool(native_file)
        version = 'legacy-ui-fixture-permissions-v1' if fixture else 'block1-permissions-v1'
        if catalogue['version'] != version:
            raise CatalogueUnavailable('catalogue_selection_version_mismatch')
        if native:
            if fixture or any(os.environ.get('VF_MTA_HIERARCHY' + suffix)
                              for suffix in ('_FILE', '_SHA256')):
                raise CatalogueUnavailable('mixed_native_catalogue_selection')
            binding = _read('VF_MTA_SELECTION', unique_keys=True)
            fields = {'schema', 'run_id', 'output_digest', 'business_date',
                      'initialization_id', 'publication_seal', 'configuration_digest',
                      'btr_generation', 'summary_generation', 'summary_digest', 'selection_digest'}
            if (not isinstance(binding, dict) or set(binding) != fields
                    or any(not isinstance(binding[key], str) for key in fields)
                    or binding['schema'] != 'fresh-production-selection-v1'):
                raise CatalogueUnavailable('invalid_native_catalogue_selection')
            for key in ('run_id', 'initialization_id', 'btr_generation', 'summary_generation'):
                UUID(binding[key])
            if date.fromisoformat(binding['business_date']).isoformat() != binding['business_date']:
                raise ValueError('Invalid selection date')
            for key in ('output_digest', 'publication_seal', 'configuration_digest',
                        'summary_digest', 'selection_digest'):
                if len(binding[key]) != 64 or any(c not in '0123456789abcdef' for c in binding[key]):
                    raise ValueError('Invalid selection digest')
            canonical = json.dumps({k: v for k, v in binding.items() if k != 'selection_digest'},
                                   sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                                   allow_nan=False).encode()
            if (hashlib.sha256(canonical).hexdigest() != binding['selection_digest']
                    or binding['run_id'] != os.environ.get('VF_MTA_PUBLISHED_RUN')
                    or binding['output_digest'] != os.environ.get('VF_MTA_PUBLISHED_DIGEST')):
                raise CatalogueUnavailable('native_publication_catalogue_binding_mismatch')
        elif fixture:
            binding = _read('VF_MTA_FIXTURE')
            if (binding['version'] != 'legacy-ui-fixture-v1'
                    or binding['permissions_sha256'] != checksum
                    or binding['manifest_sha256'] != catalogue['manifest_sha256']
                    or binding['run_id'] != binding['consumer_publication']['run_id']
                    or os.environ.get('VF_MTA_HIERARCHY_FILE')
                    or os.environ.get('VF_MTA_HIERARCHY_SHA256')
                    or os.environ.get('VF_MTA_PUBLISHED_RUN')
                    or os.environ.get('VF_MTA_PUBLISHED_DIGEST')):
                raise CatalogueUnavailable('fixture_catalogue_binding_mismatch')
        else:
            if not os.environ.get('VF_MTA_PUBLISHED_RUN') or not os.environ.get('VF_MTA_PUBLISHED_DIGEST'):
                raise CatalogueUnavailable('explicit_publication_identity_required')
            binding = _read('VF_MTA_HIERARCHY')
            if (binding['version'] != 'fresh-presentation-hierarchy-v1'
                    or binding['catalogue_sha256'] != checksum
                    or not any(row['run_id'] == os.environ.get('VF_MTA_PUBLISHED_RUN')
                               and row['output_digest'] == os.environ.get('VF_MTA_PUBLISHED_DIGEST')
                               for row in binding['publications'])):
                raise CatalogueUnavailable('publication_catalogue_binding_mismatch')
        result = {}
        for kind, source, field in (('product', 'products', 'product_hierarchy_'),
                                    ('location', 'locations', 'location_heirarchy_')):
            records = catalogue[source]['records']
            if len({row['id'] for row in records}) != len(records):
                raise CatalogueUnavailable('duplicate_permission_id')
            result[kind] = [dict(id=row['id'], **{
                field + str(i): row['level_' + str(i)] for i in range(1, 4)
            }) for row in records]
        return result
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogueUnavailable('invalid_catalogue_binding') from exc


def validate_configured():
    if enabled():
        payload()


def remote_payload(response):
    """Keep upstream failure distinct from a valid empty permission catalogue."""
    if response.status_code != 200:
        raise CatalogueUnavailable('mta_permission_service_unavailable')
    try:
        value = response.json()
        if not isinstance(value, dict) or set(value) != {'product', 'location'}:
            raise ValueError('Permission response keys differ')
        for kind, prefix in [('product', 'product_hierarchy_'), ('location', 'location_heirarchy_')]:
            rows = value[kind]
            if not isinstance(rows, list):
                raise ValueError('Permission list required')
            ids = []
            for row in rows:
                if (not isinstance(row, dict) or 'id' not in row
                        or any(prefix + str(i) not in row for i in (1, 2, 3))):
                    raise ValueError('Permission record differs')
                if isinstance(row['id'], bool) or not str(row['id']).isdigit():
                    raise ValueError('Invalid permission ID')
                ids.append(str(row['id']))
            if len(ids) != len(set(ids)):
                raise ValueError('Duplicate permission ID')
        return value
    except (ValueError, TypeError, KeyError) as exc:
        raise CatalogueUnavailable('mta_permission_response_invalid') from exc
