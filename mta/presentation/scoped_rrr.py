"""Existing RRR wire contract over an explicitly admitted phase Pick owner."""
from mta.presentation.context import PublicationUnavailable
from mta.presentation.scoped_pick_storage import PickBinding


def read(run, payload, *, read_binding, paging, count=False, export=False):
    # A retained binding owns this request. Admission belongs to scoped_view;
    # this reader neither reselects a generation nor prepares missing data.
    if not isinstance(read_binding, PickBinding) or read_binding.run_id != run.pk:
        raise PublicationUnavailable('rrr_phase_owner_differs')
    from mta.presentation.rrr_prepared_sql import read_prepared
    relation, params = read_binding.query('rrr')
    return read_prepared(run, payload, paging=paging, count=count,
        relation=relation, relation_params=params, read_binding=read_binding, export=export)
