"""Authenticated immutable phase images for placement report preparation.

Physical identity is deliberately separate from logical SQL table equivalence.
An Importer image remains Importer: a consumer must separately prove any BPR
copy/hook lineage. This reader neither enables definitions nor grants readiness.
"""
from copy import deepcopy
from dataclasses import dataclass

from mta.serialization import digest
from mta.runtime.runtime_report_sources import image_rows


@dataclass(frozen=True)
class PhaseSources:
    phase: object
    identity: dict
    manifests: tuple

    def image(self, node, *, logical_image, physical_table, fields):
        """Read one exact declared image, never a same-schema/date substitute."""
        from mta.runtime.phase_state import REGISTRY
        if (type(node) is not tuple or not node
                or any(type(part) not in (str, int) for part in node)
                or type(logical_image) is not str or type(physical_table) is not str):
            raise ValueError('Explicit phase report source path/table required')
        manifest = self.manifests[0]
        value = manifest
        for part in node:
            if isinstance(value, dict) and type(part) is str and part in value:
                value = value[part]
            elif isinstance(value, list) and type(part) is int and 0 <= part < len(value):
                value = value[part]
            else:
                raise ValueError('Required phase report source is absent')
        if value != {'image': logical_image} or not logical_image.startswith('phase/'+self.phase.phase+'/'):
            raise ValueError('Phase report logical source owner differs')
        meta = manifest['images'].get(logical_image)
        if not isinstance(meta, dict) or meta.get('table') != physical_table:
            raise ValueError('Phase report physical table owner differs')
        # Storage may reuse an identical ancestor image. Require the exact
        # corresponding path and metadata in an authenticated ancestor, not
        # merely a PRE_BPR/BPR prefix or an empty matching table schema.
        from mta.runtime.phase_image_storage import owns_physical_image
        if not owns_physical_image(self.manifests, logical_image, meta):
            raise ValueError('Phase report physical image lineage differs')
        rows = image_rows(self.phase.run, meta, expected_table=physical_table,
                          fields=fields, registry=REGISTRY)
        reference = dict(self.identity, node=list(node), logical_image=logical_image,
            physical_image=meta['image'], physical_table=physical_table,
            row_count=meta['count'], rows_digest=meta['digest'], fields=list(fields))
        reference['digest'] = digest(reference)
        return rows, reference


def bind(phase_id, *, expected_digest, expected_phase, expected_action_revision,
         expected_profile_digest, expected_request_digest):
    """Authenticate a selected accepted cut before reading any report image.

    Action identity is the producer's accepted cut, not today's live revision.
    This does not authorize showing a stale actionable UI view. The caller's
    publication owner must recheck its required revision before registration.
    """
    from mta.runtime.scoped_pick_files import _accepted
    from mta.runtime.input_reader import read_input
    from mta.runtime.ingestion_context import sha
    from mta.runtime.phase_state import SCHEMA
    for value in (expected_digest, expected_profile_digest, expected_request_digest):
        sha(value)
    if (expected_phase not in ('PRE_BPR', 'BPR', 'DBM')
            or type(expected_action_revision) is not int or expected_action_revision < 0):
        raise ValueError('Explicit phase report generation required')
    phase = _accepted(phase_id, expected_digest)
    run = phase.run
    manifest = phase.snapshot.manifest
    if (phase.phase != expected_phase or manifest.get('schema') != SCHEMA
            or manifest.get('phase') != expected_phase
            or manifest.get('metadata', {}).get('identity') != str(run.pk)
            or digest(manifest) != phase.snapshot.state_digest
            or manifest.get('references', {}).get('day', {}).get('business_date') != digest(run.business_date.isoformat())
            or type(phase.metadata.get('action_revision', 0)) is not int
            or type(manifest.get('metadata', {}).get('action_revision', 0)) is not int
            or phase.metadata.get('action_revision', 0) != expected_action_revision
            or manifest.get('metadata', {}).get('action_revision', 0) != expected_action_revision):
        raise ValueError('Phase report generation identity differs')
    raw = read_input(run, components=('profile', 'scope_request'))
    if (not isinstance(raw.get('scope_request'), dict)
            or digest(raw['scope_request']) != expected_request_digest
            or digest(raw.get('profile')) != expected_profile_digest
            or manifest['references'].get('profile') != expected_profile_digest):
        raise ValueError('Phase report captured configuration differs')
    manifests = [deepcopy(manifest)]
    current = phase
    while current.snapshot.parent_id is not None:
        parent_snapshot = current.snapshot.parent
        parent_digest = current.metadata.get('effects', {}).get('parent_acceptance_digest')
        parent = _accepted(parent_snapshot.acceptance_id, parent_digest)
        if (parent.run_id != run.pk or parent.snapshot.pk != parent_snapshot.pk
                or parent.snapshot.manifest['references'] != manifest['references']):
            raise ValueError('Phase report ancestor generation differs')
        manifests.append(deepcopy(parent.snapshot.manifest))
        current = parent
    identity = dict(schema='fresh-runtime-report-phase-source-v1', run_id=str(run.pk),
        phase_id=str(phase.pk), phase=phase.phase, phase_digest=phase.digest,
        snapshot_digest=phase.snapshot.state_digest, input_digest=run.input_digest,
        input_manifest_digest=run.input_manifest_digest,
        business_date=run.business_date.isoformat(), action_revision=expected_action_revision,
        profile_digest=expected_profile_digest, captured_request_digest=expected_request_digest)
    return PhaseSources(phase, identity, tuple(manifests))
