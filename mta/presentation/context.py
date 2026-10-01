"""Read the explicitly selected relational publication, never the latest trial.

No calculation, evidence-trace read, fixture fallback or publication mutation.
The run service verifies its operational checksum and immutable input identity.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from uuid import UUID

from django.conf import settings

from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from mta.runtime.temporal import command_state
from mta.presentation.permissions import (
    PermissionCodes, expand_permission_ids, materialize_permission_memberships,
)


class PublicationUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class Publication:
    run: CalculationRun
    output: dict
    dbm: dict

    @property
    def business_date(self):
        return self.run.business_date


def publication():
    identifier = settings.VF_MTA_PUBLISHED_RUN
    expected = settings.VF_MTA_PUBLISHED_DIGEST
    if not identifier or not expected:
        raise PublicationUnavailable('explicit_publication_identity_required')
    try:
        identifier = UUID(identifier)
    except (ValueError, TypeError, AttributeError) as exc:
        raise PublicationUnavailable('invalid_publication_identity') from exc
    run = CalculationRun.objects.filter(pk=identifier, kind='DAILY_CHAIN', status='SUCCEEDED').first()
    if run is None or not run.production_manifest or run.output_digest != expected:
        raise PublicationUnavailable('publication_identity_or_status_mismatch')
    if run.parity_summary.get('status') not in ('PASS', 'PASS_WITH_LEGACY_FLAWS'):
        raise PublicationUnavailable('publication_acceptance_required')
    output = read_outputs(run)
    dbm, _ = command_state(run, output['DBMFinal'][0])
    # Compatibility input shape only: the BTR consumer needs final ration rows,
    # not a persisted or reconstructed internal calculation-stage trace.
    output = {**output, 'BPRStages': [{'state': output['BPRReports'][0]}]}
    return Publication(run, output, dbm)


def permission_catalogue():
    path, expected = settings.VF_MTA_PERMISSIONS_FILE, settings.VF_MTA_PERMISSIONS_SHA256
    if not path or not expected:
        raise PublicationUnavailable('permission_catalogue_not_configured')
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise PublicationUnavailable('permission_catalogue_unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != expected:
        raise PublicationUnavailable('permission_catalogue_identity_mismatch')
    value = json.loads(raw)
    if value.get('version') != 'block1-permissions-v1':
        raise PublicationUnavailable('unsupported_permission_catalogue')
    for kind in ('products', 'locations'):
        records = value[kind]['records']
        if len({r['id'] for r in records}) != len(records):
            raise PublicationUnavailable('duplicate_permission_id')
    return value


def scope(payload, *, attributes):
    """Expand permission IDs against THIS publication's producer attributes.

    The registered permission artifact owns IDs/hierarchy definitions only.
    Its historical attribute memberships are not authority to bypass the
    selected run's NULL/missing or changed SKU/location hierarchy values.
    """
    catalogue = permission_catalogue()
    result = []
    for key, kind in (('product_permissions', 'products'), ('location_permissions', 'locations')):
        assigned = payload.get(key, [])
        if not isinstance(assigned, list) or any(isinstance(v, bool) or not str(v).isdigit() for v in assigned):
            raise ValueError('invalid_permission_scope_id')
        assigned = {int(v) for v in assigned}
        records = catalogue[kind]['records']
        if assigned - {r['id'] for r in records}:
            raise PublicationUnavailable('permission_hierarchy_unavailable')
        table, code, prefix = (('SkuAttributeData','SKUCode','SL') if kind=='products'
                               else ('LocationAttributeData','WHCode','LL'))
        produced = [dict(code=row[code], **{f'level_{i}':row[f'{prefix}{i}'] for i in (1,2,3)})
                    for row in attributes[table]]
        memberships = materialize_permission_memberships(records, produced)
        counts = {}
        for selected in expand_permission_ids(records, assigned):
            for code, weight in memberships[selected].items():
                counts[code] = counts.get(code, 0) + weight
        result.append(PermissionCodes(counts))
    return tuple(result)
