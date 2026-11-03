"""Atomic typed rationing deltas; no unchanged-history payload writes.

The outer execute_day transaction remains the publication boundary. Normal
finish_run supplies its frozen input once. This module adds a savepoint so
even a caller catching a late mismatch cannot retain a partial storage prefix.
"""
import hashlib
from contextlib import closing

from django.db import connection, transaction

from mta.application.stage_observation import stage, summary
from mta.domain.btr_rationing_history import COLUMNS, FIELDS
from mta.serialization import canonical_parts, digest
from mta.runtime.rationing_delta import changes, Fact, DispatchRevision, Expiry, Counts
from mta.runtime.rationing_delta import Occurrence
from mta.runtime.rationing_reader import (Cut, FAMILY, FORMAT, image_metadata,
                                        read_cut, iter_occurrences)
from mta.runtime.rationing_shape import require_fields
from mta.runtime.relational_state import copy_rows, db_value, quote, wire_type, wire_value
from mta.runtime.state_cut_models import OperationalStateCut


BATCH = 500


class _Digest:
    def __init__(self):
        self.hash = hashlib.sha256(b'[')
        self.count = 0
        # Canonical hash-input bytes, including array delimiters. This is not
        # physical PostgreSQL storage, WAL, network traffic or a memory peak.
        self.canonical_bytes = 2

    def add(self, value):
        if self.count:
            self.hash.update(b',')
            self.canonical_bytes += 1
        for part in canonical_parts(value):
            self.hash.update(part)
            self.canonical_bytes += len(part)
        self.count += 1

    def value(self):
        copy = self.hash.copy()
        copy.update(b']')
        return copy.hexdigest()


class _Shape:
    """Observe the classifier's existing pass, without another history scan."""
    def __init__(self, rows, inherited_order):
        self.rows = rows
        self.inherited_order = inherited_order
        self.kinds = [set() for _ in COLUMNS]
        self.order = None
        self.count = 0

    def __iter__(self):
        for row in self.rows:
            order = tuple(row)
            if order not in (FIELDS, self.inherited_order):
                raise ValueError('Rationing produced row order differs')
            if self.order is None:
                self.order = order
            for kinds, column in zip(self.kinds, COLUMNS):
                value = row[column['name']]
                if value is not None:
                    kinds.add(wire_type(value))
                    if len(kinds) > 1:
                        raise ValueError('Mixed rationing wire types')
            self.count += 1
            yield row

    def fields(self):
        kinds = dict(zip(FIELDS, self.kinds))
        value = [[name, name, next(iter(kinds[name]), 'str')] for name in self.order or ()]
        require_fields(value, self.count, source_order=True)
        return value


def _facts(cut, rows):
    copy_rows('mta_state.rationing_fact', ['cut_id', 'vf_ordinal', *[c['name'] for c in COLUMNS]],
        ((cut.pk, e.occurrence.ordinal, *[db_value(e.values[c['name']], c['type']) for c in COLUMNS])
         for e in rows))
    copy_rows('mta_state.rationing_lifetime',
        ['fact_cut_id', 'original_ordinal', 'initialization_id', 'born_position'],
        ((cut.pk, e.occurrence.ordinal, cut.initialization_id, cut.position) for e in rows))


def _flush(cut, events):
    facts = [e for e in events if type(e) is Fact]
    if facts:
        _facts(cut, facts)
    existing = [e for e in events if type(e) in (DispatchRevision, Expiry)]
    if not existing:
        return
    positions = {e.occurrence.position for e in existing}
    owners = dict(OperationalStateCut.objects.filter(initialization_id=cut.initialization_id,
        family=FAMILY, position__in=positions).values_list('position', 'id'))
    if set(owners) != positions:
        raise ValueError('Rationing original occurrence owner missing')
    revisions = [e for e in existing if type(e) is DispatchRevision]
    if revisions:
        copy_rows('mta_state.rationing_dispatch',
            ['cut_id', 'position', 'original_cut_id', 'original_ordinal', 'dispatch'],
            ((cut.pk, cut.position, owners[e.occurrence.position], e.occurrence.ordinal, e.dispatch)
             for e in revisions))
    expired = [e for e in existing if type(e) is Expiry]
    if expired:
        identities = [owners[e.occurrence.position] for e in expired]
        ordinals = [e.occurrence.ordinal for e in expired]
        copy_rows('mta_state.rationing_expiry',
            ['cut_id', 'position', 'original_cut_id', 'original_ordinal'],
            ((cut.pk, cut.position, identity, ordinal) for identity, ordinal in zip(identities, ordinals)))
        # Update only this batch, not every earlier expiry in the same day.
        with connection.cursor() as cursor:
            cursor.execute('UPDATE mta_state.rationing_lifetime L SET end_position=%s,closing_cut_id=%s'
                ' FROM unnest(%s::uuid[],%s::bigint[]) AS X(identity,ordinal)'
                ' WHERE L.fact_cut_id=X.identity AND L.original_ordinal=X.ordinal AND L.end_position IS NULL',
                [cut.position, cut.pk, identities, ordinals])
            if cursor.rowcount != len(expired):
                raise ValueError('Rationing expiry did not close its exact occurrence batch')


def _stored_digests(cut, fields):
    """One pass over this cut's new deltas, never its whole logical history."""
    checks = {name: _Digest() for name in ('facts', 'revisions', 'expiry')}
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT vf_ordinal'+(','+','.join(quote(name) for _, name, _ in fields) if fields else '')+
                       ' FROM mta_state.rationing_fact WHERE cut_id=%s ORDER BY vf_ordinal', [cut.pk])
        while batch := cursor.fetchmany(BATCH):
            for record in batch:
                if record[0] != checks['facts'].count:
                    raise ValueError('Rationing fact ordinal differs')
                row = {name: wire_value(value, kind)
                       for (name, _, kind), value in zip(fields, record[1:])}
                checks['facts'].add([record[0], row])
    for name, table in (('revisions', 'rationing_dispatch'), ('expiry', 'rationing_expiry')):
        with connection.chunked_cursor() as cursor:
            cursor.execute('SELECT P.position,E.original_ordinal'+(',E.dispatch' if name == 'revisions' else '')+
                ' FROM mta_state.'+table+' E JOIN mta.fresh_mta_operationalstatecut P ON P.id=E.original_cut_id'
                ' WHERE E.cut_id=%s ORDER BY P.position,E.original_ordinal', [cut.pk])
            while batch := cursor.fetchmany(BATCH):
                for record in batch:
                    checks[name].add(list(record))
    return checks


def _seal(cut, *, parent, fields, counts, checks, anchor=None):
    with stage('rationing_delta_readback', facts=checks['facts'].count,
               revisions=checks['revisions'].count, expiry=checks['expiry'].count):
        stored = _stored_digests(cut, fields)
    if any((stored[name].count, stored[name].value()) != (expected.count, expected.value())
           for name, expected in checks.items()):
        raise ValueError('Rationing persisted delta values/type/order differ')
    body = dict(format=FORMAT, cut=str(cut.pk), initialization=str(cut.initialization_id),
        family=FAMILY, position=cut.position, run=str(cut.run_id) if cut.run_id else None,
        parent=str(cut.parent_id) if cut.parent_id else None,
        parent_root=parent.root_digest if parent else '0'*64,
        input_digest=cut.input_digest, settings_digest=cut.settings_digest,
        fields=fields, count=counts.closing, inserted=counts.inserted, revised=counts.revised,
        expired=counts.expired, facts_digest=checks['facts'].value(),
        revisions_digest=checks['revisions'].value(), expiry_digest=checks['expiry'].value(), anchor=anchor)
    cut.root_body = b''.join(canonical_parts(body)).decode('utf-8')
    cut.root_digest = digest(body)
    cut.save(update_fields=['root_body', 'root_digest'])
    summary('rationing_delta_work', position=cut.position,
        logical_prior_rows=counts.prior, logical_closing_rows=counts.closing,
        inserted_facts=checks['facts'].count, dispatch_revisions=checks['revisions'].count,
        expired_occurrences=checks['expiry'].count,
        canonical_delta_hash_bytes=sum(check.canonical_bytes for check in checks.values()),
        canonical_readback_hash_bytes=sum(check.canonical_bytes for check in stored.values()),
        root_bytes=len(cut.root_body.encode('utf-8')))
    return image_metadata(Cut(cut.pk, cut.initialization_id, cut.run_id, cut.position, cut.root_digest, body))


@stage('rationing_delta_write')
def _write_delta(cut, parent, rows, *, today, capture_enabled, horizon):
    """Private storage operation, called only inside the owner/savepoint below."""
    inherited = tuple(field[0] for field in parent.body['fields']) or FIELDS
    observed = _Shape(rows, inherited)
    checks = {name: _Digest() for name in ('facts', 'revisions', 'expiry')}
    batch = []
    counts = None
    # Close the named prior cursor BEFORE a failed savepoint is rolled back.
    # Leaving it in an exception traceback can otherwise issue CLOSE against
    # an already-removed portal later and poison the caller's recovered TX.
    with closing(iter_occurrences(parent)) as prior:
        with closing(changes(prior, observed, today=today, position=cut.position, inherited_order=inherited,
                             capture_enabled=capture_enabled, horizon=horizon)) as events:
            for event in events:
                if type(event) is Counts:
                    counts = event
                    continue
                if type(event) is Fact:
                    checks['facts'].add([event.occurrence.ordinal, event.values])
                elif type(event) is DispatchRevision:
                    checks['revisions'].add([event.occurrence.position, event.occurrence.ordinal, event.dispatch])
                elif type(event) is Expiry:
                    checks['expiry'].add([event.occurrence.position, event.occurrence.ordinal])
                else:
                    raise ValueError('Unknown rationing storage event')
                batch.append(event)
                if len(batch) == BATCH:
                    _flush(cut, batch)
                    batch = []
    if (counts is None or counts.closing != observed.count or observed.count != len(rows)
            or counts.prior != parent.body['count']):
        raise ValueError('Rationing storage classification did not complete')
    if batch:
        _flush(cut, batch)
    return _seal(cut, parent=parent, fields=observed.fields(), counts=counts, checks=checks)


def write_day(run, rows):
    """Derive controls from this run's frozen input, never caller/live settings."""
    if not connection.in_atomic_block:
        raise ValueError('Rationing storage requires the existing day transaction')
    from mta.runtime.input_reader import read_execution_input
    frozen = read_execution_input(run, components=('profile', 'execution_settings', 'initialization_binding'))
    return write_frozen_day(run, rows, frozen=frozen, profile_digest=digest(frozen['profile']))


def write_frozen_day(run, rows, *, frozen, profile_digest):
    """Internal commit adapter: reuse finish_run's decoded input and local hash.

    The caller computes the profile digest from this same frozen profile once.
    SQL independently binds the cut to the actual captured settings reference.
    No live management values or operator-supplied policy enters this path.
    """
    if not connection.in_atomic_block:
        raise ValueError('Rationing storage requires the existing day transaction')
    from mta.runtime.initialization_models import ProductionInitialization
    from mta.runtime.execution_settings import _check_snapshot_digest
    with transaction.atomic():
        owner = ProductionInitialization.objects.select_for_update().get(pk=frozen['initialization_binding']['id'])
        profile = frozen['profile']
        _check_snapshot_digest(owner, profile_digest, frozen.get('execution_settings'), run.business_date)
        policy = profile['delivery']['btr_settings']
        # The engine already qualified the Importer flag/COUNT=1 relationship.
        # Here the exact frozen flag controls only storage correspondence.
        flag = policy.get('CaptureDispatchExecutionEfficiency')
        if type(flag) not in (int, str) or flag not in (0, 1, '0', '1'):
            raise ValueError('Rationing storage requires its frozen capture flag')
        enabled = str(flag) == '1'
        parent_row = OperationalStateCut.objects.get(initialization=owner, family=FAMILY, run_id=run.predecessor_id)
        parent = read_cut(parent_row.pk)
        cut = OperationalStateCut.objects.create(initialization=owner, family=FAMILY, position=parent.position+1,
            run=run, parent=parent_row, input_digest=run.input_digest, settings_digest=profile_digest)
        return _write_delta(cut, parent, rows, today=run.business_date,
                            capture_enabled=enabled, horizon=policy.get('RationingHistoryHorizonBTR'))


def begin_initial_anchor(owner):
    """Called inside normal initialization before its existing immutable seal."""
    if not connection.in_atomic_block:
        raise ValueError('Rationing anchor requires the existing initialization transaction')
    return OperationalStateCut.objects.create(initialization=owner, family=FAMILY, position=0,
        input_digest=owner.input_digest, settings_digest=owner.configuration_digest)


def seal_initial_anchor(cut, owner):
    """One-time opening materialization, using its existing audited reader."""
    if not connection.in_atomic_block or cut.initialization_id != owner.pk or cut.position != 0 or cut.run_id:
        raise ValueError('Rationing opening anchor owner differs')
    from mta.runtime.opening_storage import iter_image
    from mta.runtime.btr_history_storage import OPENING
    with transaction.atomic():
        item = owner.input_payload['images'][OPENING]
        anchor = dict(owner_kind='INITIALIZATION', owner_id=str(owner.pk),
            manifest_digest=owner.input_manifest_digest, image=OPENING,
            digest=item['digest'], count=item['count'])
        with closing(iter_image(owner, item)) as rows:
            return seal_anchor_rows(cut, item, rows, anchor)


def seal_anchor_rows(cut, item, rows, anchor):
    """Private one-time transport of an independently audited opening/prefix."""
    require_fields(item['fields'], item['count'], source_order=True)
    checks = {name: _Digest() for name in ('facts', 'revisions', 'expiry')}
    batch = []
    for ordinal, row in enumerate(rows):
        event = Fact(Occurrence(0, ordinal), row)
        checks['facts'].add([ordinal, row])
        batch.append(event)
        if len(batch) == BATCH:
            _facts(cut, batch)
            batch = []
    if batch:
        _facts(cut, batch)
    if checks['facts'].count != item['count']:
        raise ValueError('Rationing anchor source population differs')
    counts = Counts(0, 0, item['count'], 0, 0, item['count'])
    return _seal(cut, parent=None, fields=item['fields'], counts=counts, checks=checks, anchor=anchor)
