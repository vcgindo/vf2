"""Lazy exact MasterDataRaw compatibility views for an unchanged active NMS day.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import json

from mta.application.r1_importer_master import (
    apply_raw_ansi_padding, normalize_master_row,
)
from mta.mdm.daily_input import (
    SCHEMA, CompositionOverlayPlan, description_additions, nms_master_row,
)
from mta.row_sequences import RecordRows
from mta.serialization import digest


class UnchangedMasterPlan:
    """One-operation projection plan; indexes are built once and rows stay lazy."""

    def __init__(self, snapshot, nms_items, business_date):
        self.snapshot = snapshot
        self.nms_items = nms_items
        self.business_date = business_date
        rows = snapshot['rows']
        additions = description_additions(rows,
            (nms_master_row(item) for item in nms_items))
        self._descriptors = ([('nms', ordinal) for ordinal in range(len(nms_items))]
                             + [('metadata', ordinal) for ordinal in range(len(additions))])
        self._metadata = tuple(deepcopy(additions))
        self._overlays = CompositionOverlayPlan(rows)
        self._overlays.validate_pair_core(self._initial(descriptor)
                                          for descriptor in self._descriptors)
        # The canonical producer sorts its returned table by this exact key.
        # Retain only ordinals and transient key strings, never projected rows.
        self._canonical_ordinals = tuple(sorted(range(len(self._descriptors)),
            key=lambda ordinal: json.dumps(self._project(ordinal, canonical=True),
                                           sort_keys=True)))
        count = len(self._descriptors)
        self.raw = RecordRows(count, lambda: (self._project(i, canonical=False)
                                              for i in range(count)),
                              getitem=lambda i: self._project(i, canonical=False))
        self.canonical = RecordRows(count, lambda: (self._project(i, canonical=True)
            for i in self._canonical_ordinals),
            getitem=lambda i: self._project(self._canonical_ordinals[i], canonical=True))
        self.counts = {'nms': len(nms_items), 'metadata': len(additions), 'total': count}

    def _initial(self, descriptor):
        kind, ordinal = descriptor
        if kind == 'nms':
            return nms_master_row(self.nms_items[ordinal])
        return deepcopy(self._metadata[ordinal])

    def _project(self, ordinal, *, canonical):
        row = self._overlays.apply(self._initial(self._descriptors[ordinal]))
        if canonical:
            apply_raw_ansi_padding(row)
            normalize_master_row(row, self.business_date, trim=False)
        return row

    def view(self, canonical=False):
        return self.canonical if canonical else self.raw


def unchanged_plan(snapshot, nms_items, business_date):
    """Qualify and build an exact lazy active-NMS compatibility projection."""
    if (not isinstance(snapshot, dict) or snapshot.get('schema') != SCHEMA
            or digest({k: v for k, v in snapshot.items() if k != 'revision_digest'})
               != snapshot.get('revision_digest')):
        raise ValueError('MDM daily input revision drift')
    if snapshot.get('nms_active') is not True:
        raise ValueError('unchanged master compatibility requires active NMS')
    rows = snapshot.get('rows')
    if not isinstance(rows, dict):
        raise ValueError('unchanged master compatibility rows are absent')
    candidates = (*rows['sku']['approved'], *rows['location']['approved'],
                  *rows['skuloc']['additions'], *rows['skuloc']['modifications'],
                  *rows['skuloc']['removals'])
    if any(row.get('Approved') for row in candidates):
        raise ValueError('unchanged master compatibility denies approved family changes')
    if not isinstance(nms_items, (list, tuple, RecordRows)):
        raise ValueError('unchanged master compatibility requires an indexed NMS population')
    return UnchangedMasterPlan(snapshot, nms_items, business_date)
