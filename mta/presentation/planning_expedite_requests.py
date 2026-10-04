"""Exact retained April empty request source, distinct from the June preview exception."""
import hashlib
import json
from pathlib import Path
from mta.presentation import fixture
from mta.presentation.context import PublicationUnavailable

SOURCE = Path(__file__).resolve().parents[2]/'baseline/planning-april-empty-requests-v1.json'
SOURCE_SHA = '0cec4bea850da03b9e57d59fe114a15d68fb60254637988451b609995757a33c'


def empty_requests(run):
    selected, source_digest = fixture.binding()
    try:
        raw = SOURCE.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:
            raise ValueError('source bytes changed')
        value = json.loads(raw)
    except (OSError,ValueError) as exc:
        raise PublicationUnavailable('planning_expedite_request_source_missing_or_changed') from exc
    if (getattr(run,'kind',None)!='LEGACY_UI_FIXTURE' or selected.pk!=run.pk
            or str(run.pk)!=value['run_id'] or str(run.business_date)!=value['business_date']
            or source_digest!=value['fixture_source_digest']
            or fixture.policy()['manifest_sha256']!=value['manifest_sha256']
            or value['rows']!=[]):
        raise PublicationUnavailable('planning_expedite_request_source_wrong_fixture')
    return []
