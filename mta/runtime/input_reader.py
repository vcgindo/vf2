"""Production input boundary: typed daily images or an owned current-day input.

Historical daily snapshots belong to development.validation_storage. Never
consult validation files to satisfy a production read.
"""
from mta.runtime import input_storage
from mta.serialization import digest


def read_execution_input(run, *, components=None):
    """Decode an already ingested daily owner; audits use read_input below."""
    if getattr(run, 'input_payload', {}).get('schema') in (
            input_storage.SCHEMA, input_storage.V3,
            *('fresh-captured-input-reference-v' + str(v) for v in range(1, 7))):
        from mta.runtime.accepted_input_read import read_accepted_input
        return read_accepted_input(run, components=components)
    return read_input(run, components=components)


def read_input(run, *, components=None):
    value = run.input_payload
    from mta.runtime.captured_input import SCHEMAS as CAPTURED, read as read_captured
    if value.get('schema') in CAPTURED:
        return read_captured(run, components=components)
    if value.get('schema') in (input_storage.SCHEMA, input_storage.V3):
        return input_storage.read_input(run, components=components)
    # The separate current-day entry persists its ordinary request inline.
    # A daily-chain input must always use the typed owner/manifest boundary.
    if (run.kind != 'CURRENT_DAY' or value.get('schema') == 'fresh-input-reference-v1'
            or digest(value) != run.input_digest):
        raise ValueError('Production input requires an intact native input')
    return value if components is None else {k: v for k, v in value.items() if k in components}
