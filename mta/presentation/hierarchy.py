"""Explicit approved presentation metadata; never an engine/state input.

Only six hierarchy fields can be filled, using exact retained entity identities.
Native rows/checksums remain untouched. Absent opt-in preserves NULL denial.
"""
import hashlib
import json
from pathlib import Path

from django.conf import settings


class HierarchyUnavailable(ValueError):
    pass


FIELDS = {'products': ['SL1', 'SL2', 'SL3'], 'locations': ['LL1', 'LL2', 'LL3']}


def selected_manifest(run):
    path = settings.VF_MTA_HIERARCHY_FILE
    expected = settings.VF_MTA_HIERARCHY_SHA256
    if not path and not expected:
        return None
    if not path or not expected:
        raise HierarchyUnavailable('hierarchy_supplement_identity_required')
    try:
        raw = Path(path).read_bytes()
        manifest = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise HierarchyUnavailable('hierarchy_supplement_unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != expected:
        raise HierarchyUnavailable('hierarchy_supplement_hash_mismatch')
    binding = dict(run_id=str(run.pk), business_date=str(run.business_date), output_digest=run.output_digest)
    if (manifest.get('version') != 'fresh-presentation-hierarchy-v1' or
            manifest.get('role') != 'presentation-only-retained-hierarchy' or
            manifest.get('allowed_fields') != FIELDS or
            manifest.get('catalogue_sha256') != settings.VF_MTA_PERMISSIONS_SHA256 or
            binding not in manifest.get('publications', [])):
        raise HierarchyUnavailable('hierarchy_supplement_scope_mismatch')
    return manifest


def project_attributes(state, catalogue, manifest):
    result = dict(state)
    for kind, table, code in (('products', 'SkuAttributeData', 'SKUCode'),
                              ('locations', 'LocationAttributeData', 'WHCode')):
        attributes = catalogue[kind]['attributes']
        by_code = {row['code']: row for row in attributes}
        if len(by_code) != len(attributes) or len(attributes) != manifest['catalogue_counts'][kind]:
            raise HierarchyUnavailable('hierarchy_catalogue_population_mismatch')
        rows = []
        for original in state[table]:
            if original[code] not in by_code:
                raise HierarchyUnavailable('hierarchy_entity_not_in_retained_catalogue')
            retained = by_code[original[code]]
            row = dict(original)
            for i, field in enumerate(FIELDS[kind], 1):
                value = retained['level_' + str(i)]
                if not isinstance(value, str) or not value:
                    raise HierarchyUnavailable('hierarchy_retained_value_missing')
                if original[field] not in (None, value):
                    raise HierarchyUnavailable('hierarchy_conflicts_with_native_value')
                row[field] = value
            rows.append(row)
        # Keep every original occurrence and ordering; no joins/deduplication.
        result[table] = rows
    return result


def project(output, dbm, catalogue, manifest):
    if manifest is None:
        return output, dbm
    projected = dict(output)
    for name in ('DBMFinal', 'BTRFinal'):
        projected[name] = [project_attributes(output[name][0], catalogue, manifest)]
    closing = output['ClosingState'][0]
    projected['ClosingState'] = [{**closing,
        'importer': project_attributes(closing['importer'], catalogue, manifest)}]
    return projected, project_attributes(dbm, catalogue, manifest)
