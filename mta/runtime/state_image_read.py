"""Version-dispatched diagnostic reads; legacy recipe-bound codecs stay intact.

Normal admitted consumers use accepted_state_read. Explicit receipt audits use
this adapter to validate physical storage before returning a logical image.
No existing consumer is silently switched from audited to accepted reads.
"""
from mta.runtime import relational_state, rationing_reader
from mta.runtime.rationing_audit import audit_cut


def _new_cut(run, item, table_registry):
    registry = relational_state.STORAGE_TABLES if table_registry is None else table_registry
    if item['table'] not in registry:
        raise ValueError('Unknown operational table')
    if rationing_reader.uses_occurrences(item):
        cut = rationing_reader.require_image(run, item)
        audit_cut(cut)
        return cut
    return None


def iter_image(run, item, *, table_registry=None):
    cut = _new_cut(run, item, table_registry)
    if cut is None:
        yield from relational_state.iter_image(run, item, table_registry=table_registry)
    else:
        for _, row in rationing_reader.iter_occurrences(cut):
            yield row


def load_image(run, item, *, table_registry=None):
    cut = _new_cut(run, item, table_registry)
    if cut is None:
        return relational_state.load_image(run, item, table_registry=table_registry)
    return rationing_reader.load_cut(cut)
