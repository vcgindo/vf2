"""One atomic operator-owned selection file; no service mutation or latest-run fallback."""
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID
from mta.serialization import digest

SCHEMA = 'fresh-production-selection-v1'
FIELDS = frozenset(('schema', 'run_id', 'output_digest', 'business_date', 'initialization_id',
    'publication_seal', 'configuration_digest', 'btr_generation', 'summary_generation',
    'summary_digest', 'selection_digest'))


def validate(value):
    if not isinstance(value, dict) or set(value) != FIELDS or value['schema'] != SCHEMA:
        raise ValueError('Complete native selection bundle required')
    if any(not isinstance(value[field], str) for field in FIELDS):
        raise ValueError('Selection fields must be strings')
    for field in ('run_id', 'initialization_id', 'btr_generation', 'summary_generation'):
        UUID(value[field])
    from datetime import date
    if date.fromisoformat(value['business_date']).isoformat() != value['business_date']:
        raise ValueError('Selection date differs')
    for field in ('output_digest', 'publication_seal', 'configuration_digest', 'summary_digest', 'selection_digest'):
        if not isinstance(value[field], str) or len(value[field]) != 64 or any(c not in '0123456789abcdef' for c in value[field]):
            raise ValueError('Selection digest differs')
    if value['selection_digest'] != digest({k:v for k,v in value.items() if k != 'selection_digest'}):
        raise ValueError('Selection bundle checksum differs')
    return value


def read(path):
    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError('Duplicate selection field')
            result[name] = value
        return result
    return validate(json.loads(Path(path).read_bytes(), object_pairs_hook=unique))


def write(path, value):
    """Replace all selection values together only after full admission succeeds."""
    validate(value)
    target = Path(path).resolve()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent, prefix='.'+target.name+'.', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((json.dumps(value, sort_keys=True)+'\n').encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        if read(temporary) != value:
            raise ValueError('Selection file readback differs')
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def candidate(run, publication, summary, native):
    value = dict(schema=SCHEMA, run_id=str(run.pk), output_digest=run.output_digest,
        business_date=run.business_date.isoformat(), initialization_id=native['initialization']['id'],
        publication_seal=publication.seal_digest, configuration_digest=publication.configuration_digest,
        btr_generation=publication.layers['btr']['receipt']['generation'],
        summary_generation=str(summary.pk), summary_digest=summary.rows_digest)
    value['selection_digest'] = digest(value)
    return validate(value)


def require_selected(run):
    from django.conf import settings
    from mta.presentation.context import PublicationUnavailable
    if not getattr(settings, 'VF_MTA_SELECTION_FILE', '') or not getattr(settings, 'VF_MTA_SELECTION', None):
        raise PublicationUnavailable('native_atomic_selection_required')
    from mta.presentation.native_publication import identity
    from mta.presentation.daily_publication import require_ready
    from mta.presentation.planning_summary_admission import require_ready as summary_ready
    expected = candidate(run, require_ready(run), summary_ready(run), identity(run))
    try:
        actual = read(settings.VF_MTA_SELECTION_FILE)
    except (OSError, ValueError) as exc:
        raise PublicationUnavailable('native_selection_unavailable') from exc
    if actual != expected or settings.VF_MTA_SELECTION != expected:
        raise PublicationUnavailable('native_selection_changed_restart_required')
