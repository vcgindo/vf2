"""Production input boundary: typed daily images or an owned current-day input.

Historical daily snapshots belong to development.validation_storage. Never
consult validation files to satisfy a production read.
"""
from mta.runtime import input_storage
from mta.serialization import digest


def read_input(run, *, components=None):
    value = run.input_payload
    if value.get('schema') == input_storage.SCHEMA:
        return input_storage.read_input(run, components=components)
    # The separate current-day entry persists its ordinary request inline.
    # A daily-chain input must always use the typed owner/manifest boundary.
    if (run.kind != 'CURRENT_DAY' or value.get('schema') == 'fresh-input-reference-v1'
            or digest(value) != run.input_digest):
        raise ValueError('Production input requires an intact native input')
    return value if components is None else {k: v for k, v in value.items() if k in components}
