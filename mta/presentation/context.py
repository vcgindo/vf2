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
from mta.presentation import hierarchy
from mta.presentation.request_scope import once_per_request
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
    native_output: dict | None = None
    hierarchy_receipt: dict | None = None

    @property
    def storage_output(self):
        """Projection checksum validation must always use immutable native inputs."""
        return self.native_output if self.native_output is not None else self.output

    @property
    def business_date(self):
        return self.run.business_date


def configured_run():
    """Resolve the configured accepted header; this does not admit selection."""
    from mta.presentation import native_publication
    from mta.presentation.native_mode import require_configuration
    require_configuration()
    native_publication.require_mode()
    from mta.presentation.daily_preparation import roster_identity
    roster_identity()
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
    return run


@once_per_request
def selected_run():
    run = configured_run()
    from mta.presentation.native_selection import require_selected
    require_selected(run)
    return run


def publication():
    run = selected_run()
    output = read_outputs(run)
    dbm, _ = command_state(run, output['DBMFinal'][0])
    output = {**output, 'BPRStages': [{'state': output['BPRReports'][0]}]}
    native_output = output
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            output, dbm = hierarchy.project(output, dbm, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    receipt = None if manifest is None else dict(version=manifest['version'], sha256=settings.VF_MTA_HIERARCHY_SHA256, catalogue_sha256=manifest['catalogue_sha256'], run_id=str(run.pk), fields=manifest['allowed_fields'], native_state_unchanged=True)
    return Publication(run, output, dbm, native_output, receipt)


@once_per_request
def permission_catalogue():
    path, expected = (settings.VF_MTA_PERMISSIONS_FILE, settings.VF_MTA_PERMISSIONS_SHA256)
    if not path or not expected:
        raise PublicationUnavailable('permission_catalogue_not_configured')
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise PublicationUnavailable('permission_catalogue_unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != expected:
        raise PublicationUnavailable('permission_catalogue_identity_mismatch')
    value = json.loads(raw)
    expected_version = 'block1-permissions-v1'
    if value.get('version') != expected_version:
        raise PublicationUnavailable('unsupported_permission_catalogue')
    for kind in ('products', 'locations'):
        records = value[kind]['records']
        if len({r['id'] for r in records}) != len(records):
            raise PublicationUnavailable('duplicate_permission_id')
    return value


def scope(payload, *, attributes):
    """Expand permission IDs against THIS publication's producer attributes.

    The registered permission artifact owns IDs/hierarchy definitions only.
    Without an explicitly approved, run-bound presentation supplement, its
    historical memberships cannot override native NULL/missing hierarchy.
    With that supplement, actual projected attributes still undergo the same
    canonical permission join; no direct membership shortcut is permitted.
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
