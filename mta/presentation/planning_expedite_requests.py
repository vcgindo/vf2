from mta.presentation.native_mode import removed_mode
"""Exact retained April empty request source, distinct from the June preview exception."""
import hashlib
import json
from pathlib import Path
from mta.presentation.context import PublicationUnavailable

SOURCE = Path(__file__).resolve().parents[2]/'baseline/planning-april-empty-requests-v1.json'
SOURCE_SHA = '0cec4bea850da03b9e57d59fe114a15d68fb60254637988451b609995757a33c'


def empty_requests(run):
    from mta.presentation.daily_preparation import production_branch
    if production_branch(run):
        from mta.presentation.selective import image_rows
        return image_rows(run, 'sources/planning/OpenExpediteRequests')
    selected, source_digest = removed_mode('historical_fixture')
    try:
        raw = SOURCE.read_bytes()
        if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
            raise ValueError('source bytes changed')
        value = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise PublicationUnavailable('planning_expedite_request_source_missing_or_changed') from exc
    raise PublicationUnavailable('planning_expedite_request_source_wrong_fixture')
