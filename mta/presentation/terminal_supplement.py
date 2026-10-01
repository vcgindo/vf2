"""Explicit terminal-only consumer input; never a fallback or engine state.

This version cannot supply populated or other-date facts. Native run images
remain immutable. The external audit proves ledger completeness; deployments
pin this small manifest's bytes, not a mutable pointer to an input generator.
"""
import hashlib
import json
from pathlib import Path
from django.conf import settings
from mta.presentation.context import PublicationUnavailable

ARTIFACT_SHA = '0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546'
AUDIT_SHA = 'cbe38c447eb538f25fd7596ef6a82c00e63e4da8910283cc1f728373acdd23ba'
POPULATIONS = {'InTransitData': [], 'BPRReport_RemarkDetails': []}


def terminal_ancillary(run):
    path, expected = settings.VF_MTA_TERMINAL_FILE, settings.VF_MTA_TERMINAL_SHA256
    if not path or not expected:
        raise PublicationUnavailable('terminal_ancillary_supplement_not_configured')
    try:
        raw = Path(path).read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise PublicationUnavailable('terminal_ancillary_supplement_unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != expected:
        raise PublicationUnavailable('terminal_ancillary_supplement_hash_mismatch')
    binding = dict(run_id=str(run.pk), business_date=str(run.business_date), output_digest=run.output_digest)
    if (value.get('version') != 'fresh-presentation-terminal-v1' or
            value.get('role') != 'approved-terminal-only-empty-populations' or
            value.get('publication') != binding or
            value.get('artifact_sha256') != ARTIFACT_SHA or
            value.get('audit_receipt_sha256') != AUDIT_SHA or
            value.get('populations') != POPULATIONS):
        raise PublicationUnavailable('terminal_ancillary_supplement_scope_mismatch')
    return value['populations']
