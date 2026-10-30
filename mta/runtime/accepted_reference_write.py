"""Private, operation-local authority for the native capture's owned references.

This is an in-process capability, not a request option. Live reference metadata
is still checked by the v3 writer; only previously admitted cells are not read.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
from django.db import connection

from mta.runtime.opening_scope import current_certified_opening, require_certified_opening

_current = ContextVar('native_capture_reference_writer', default=None)


@dataclass(frozen=True)
class _Capture:
    run: object
    raw: object
    initialization: object
    handle: object
    readiness: object
    identity: dict
    seed: dict
    owners: dict
    batches: dict
    attempt_id: str | None
    predecessor_id: str | None
    transaction: object
    targets: tuple
    content_digest: str


@contextmanager
def _capture(run, raw, initialization, readiness, attempt, parent, *,
             owner_references, batch_references, content_identity):
    """Issue only after the native transaction binds its new run and feed."""
    from mta.runtime.ingestion_admission import CertifiedReadiness
    from mta.runtime.capture_preparation import seed
    from mta.runtime.input_v3 import _at, MASTER_PATH
    if not connection.in_atomic_block or not connection.atomic_blocks:
        raise ValueError('Accepted reference capture requires its atomic transaction')
    handle = current_certified_opening(initialization)
    metadata = require_certified_opening(initialization, handle)
    if (not isinstance(readiness, CertifiedReadiness) or len(metadata) != 8
            or metadata[:5] != (str(initialization.pk), initialization.source.digest,
                initialization.configuration_digest, readiness.certification_digest,
                readiness.master_revision_id)
            or readiness.initialization_id != str(initialization.pk)
            or readiness.source_digest != initialization.source.digest
            or readiness.configuration_digest != initialization.configuration_digest
            or run.kind != 'DAILY_CHAIN' or run.status != 'RUNNING'
            or run.evidence_mode != 'production'
            or str(run.predecessor_id or '') != str(getattr(parent, 'pk', '') or '')
            or run.mdm_input_capture.source_id != initialization.source_id
            or run.mdm_input_capture.source.digest != readiness.source_digest
            or content_identity['initialization_id'] != str(initialization.pk)
            or content_identity['source_digest'] != readiness.source_digest):
        raise ValueError('Accepted reference capture ownership differs')
    preparation = run.production_manifest.get('ingestion_preparation')
    if not isinstance(preparation, dict):
        raise ValueError('Accepted reference capture preparation is absent')
    expected = seed(readiness, reused=preparation.get('qualified_master_reuse') is True)
    if preparation != expected:
        raise ValueError('Accepted reference capture preparation differs')
    if attempt is not None and (attempt.initialization_id != initialization.pk
            or attempt.run_id != run.pk or attempt.status != 'RUNNING'
            or attempt.business_date != run.business_date):
        raise ValueError('Accepted reference capture feed differs')
    if batch_references and attempt is None:
        raise ValueError('Accepted reference capture feed is absent')
    paths = tuple(owner_references) + tuple(batch_references)
    from mta.application.persistent_master import NmsMasterRows
    try:
        master = _at(raw, MASTER_PATH)
    except ValueError:
        master = None
    if isinstance(master, NmsMasterRows):
        paths += (MASTER_PATH,)
    capability = _Capture(run, raw, initialization, handle, readiness,
        deepcopy(content_identity), deepcopy(preparation), deepcopy(owner_references),
        deepcopy(batch_references), str(attempt.attempt_id) if attempt is not None else None,
        str(parent.pk) if parent is not None else None, connection.atomic_blocks[-1],
        tuple((path, _at(raw, path)) for path in paths), run.input_digest)
    if _current.get() is not None:
        raise ValueError('Accepted reference capture is already active')
    token = _current.set(capability)
    try:
        yield
    finally:
        _current.reset(token)


def _for_write(run, raw, identity, owner_references, batch_references, content_identity):
    capability = _current.get()
    if capability is None:
        return None
    from mta.runtime.input_v3 import _at
    require_certified_opening(capability.initialization, capability.handle)
    if (not connection.in_atomic_block or not connection.atomic_blocks
            or connection.atomic_blocks[-1] is not capability.transaction
            or run is not capability.run or raw is not capability.raw
            or str(run.pk) != identity['owner_id'] or identity['owner_kind'] != 'run'
            or {key: identity[key] for key in ('database_name', 'database_oid', 'source_digest')}
               != {key: capability.identity[key] for key in ('database_name', 'database_oid', 'source_digest')}
            or run.status != 'RUNNING' or run.production_manifest.get('ingestion_preparation') != capability.seed
            or str(run.predecessor_id or '') != (capability.predecessor_id or '')
            or (owner_references or {}) != capability.owners
            or (batch_references or {}) != capability.batches
            or content_identity != capability.identity):
        raise ValueError('Accepted reference writer capability is foreign or stale')
    if run.input_digest != capability.content_digest or any(
            _at(raw, path) is not target for path, target in capability.targets):
        raise ValueError('Accepted reference writer graph differs')
    return capability
