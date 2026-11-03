"""Explicit physical audit of an accepted rationing prefix.

This is deliberately not the daily/serving reader. It streams every committed
delta once in a fixed number of queries, authenticates the root chain, and
checks the derived lifetime index. No whole-history payload or ancestor list
is built in Python. The normal reader continues to use one selected cut.
"""
from contextlib import ExitStack, closing
import hashlib

from django.db import connection

from mta.domain.btr_rationing_history import FIELDS
from mta.serialization import canonical_parts
from mta.runtime.rationing_reader import (CUT_FIELDS, FAMILY, authenticate_cut,
                                          require_image)
from mta.runtime.relational_state import quote, wire_value
from mta.runtime.state_cut_models import OperationalStateCut


class _Hash:
    def __init__(self):
        self.value = hashlib.sha256(b'[')
        self.count = 0

    def add(self, row):
        if self.count:
            self.value.update(b',')
        for part in canonical_parts(row):
            self.value.update(part)
        self.count += 1

    def finish(self):
        self.value.update(b']')
        return self.value.hexdigest()


def _records(sql, cut):
    with connection.chunked_cursor() as cursor:
        cursor.execute(sql, [cut.initialization, FAMILY, cut.position])
        while rows := cursor.fetchmany(500):
            yield from rows


class _Groups:
    """One lookahead record per physical stream, including empty cut groups."""
    def __init__(self, records):
        self.records = records
        self.next = next(records, None)

    def at(self, position):
        if self.next is not None and self.next[0] < position:
            raise ValueError('Rationing audit unexpected delta owner/order')
        while self.next is not None and self.next[0] == position:
            row = self.next
            self.next = next(self.records, None)
            yield row


def _lifetimes(cut):
    # Later valid expiry must not invalidate an earlier historical audit. Test
    # the exact physical closure, not whether it is earlier than the target.
    with connection.cursor() as cursor:
        cursor.execute('SELECT EXISTS(SELECT 1 FROM mta_state.rationing_fact F'
            ' JOIN mta.fresh_mta_operationalstatecut C ON C.id=F.cut_id'
            ' LEFT JOIN mta_state.rationing_lifetime L ON L.fact_cut_id=F.cut_id'
            ' AND L.original_ordinal=F.vf_ordinal'
            ' LEFT JOIN mta_state.rationing_expiry E ON E.original_cut_id=F.cut_id'
            ' AND E.original_ordinal=F.vf_ordinal'
            ' LEFT JOIN mta.fresh_mta_operationalstatecut Z ON Z.id=E.cut_id'
            ' WHERE C.initialization_id=%s AND C.family=%s AND C.position<=%s AND ('
            ' L.fact_cut_id IS NULL OR L.initialization_id IS DISTINCT FROM C.initialization_id'
            ' OR L.born_position IS DISTINCT FROM C.position'
            ' OR L.closing_cut_id IS DISTINCT FROM E.cut_id'
            ' OR L.end_position IS DISTINCT FROM E.position'
            ' OR E.cut_id IS NOT NULL AND (E.position IS DISTINCT FROM Z.position'
            ' OR Z.initialization_id IS DISTINCT FROM C.initialization_id'
            ' OR Z.family IS DISTINCT FROM C.family OR E.position<=C.position)))',
            [cut.initialization, FAMILY, cut.position])
        if cursor.fetchone()[0]:
            raise ValueError('Rationing audit lifetime index differs from immutable events')


def audit_cut(cut):
    """Full diagnostic audit; caller has authenticated the selected cut/image."""
    where = ' WHERE C.initialization_id=%s AND C.family=%s AND C.position<=%s'
    facts = ('SELECT C.position,F.vf_ordinal,' + ','.join('F.'+quote(f) for f in FIELDS) +
        ' FROM mta_state.rationing_fact F JOIN mta.fresh_mta_operationalstatecut C ON C.id=F.cut_id' +
        where + ' ORDER BY C.position,F.vf_ordinal')
    events = {}
    for name, table in (('revisions', 'rationing_dispatch'), ('expiry', 'rationing_expiry')):
        events[name] = ('SELECT C.position,P.position,E.original_ordinal' +
            (',E.dispatch' if name == 'revisions' else '') +
            ',P.initialization_id,P.family,E.position,L.end_position'
            ' FROM mta_state.'+table+' E JOIN mta.fresh_mta_operationalstatecut C ON C.id=E.cut_id'
            ' JOIN mta.fresh_mta_operationalstatecut P ON P.id=E.original_cut_id'
            ' LEFT JOIN mta_state.rationing_lifetime L ON L.fact_cut_id=E.original_cut_id'
            ' AND L.original_ordinal=E.original_ordinal' + where +
            ' ORDER BY C.position,P.position,E.original_ordinal')
    headers = OperationalStateCut.objects.filter(initialization_id=cut.initialization,
        family=FAMILY, position__lte=cut.position).order_by('position').values(*CUT_FIELDS).iterator(chunk_size=500)
    totals = dict(cuts=0, facts=0, revisions=0, expiry=0)
    previous = None
    with ExitStack() as stack:
        stack.enter_context(closing(headers))
        streams = {name: _Groups(stack.enter_context(closing(_records(sql, cut))))
                   for name, sql in dict(facts=facts, **events).items()}
        for header in headers:
            current = authenticate_cut(header)
            body = current.body
            position = totals['cuts']
            if (current.position != position or body['parent'] != (str(previous.identity) if previous else None)
                    or body['parent_root'] != (previous.root_digest if previous else '0'*64)):
                raise ValueError('Rationing audit prefix commitment chain differs')
            checks = {name: _Hash() for name in streams}
            anchor_hash = _Hash() if position == 0 else None
            for record in streams['facts'].at(position):
                if record[1] != checks['facts'].count:
                    raise ValueError('Rationing audit fact order differs')
                row = {f: wire_value(v, kind) for (f, _, kind), v in zip(body['fields'], record[2:])}
                checks['facts'].add([record[1], row])
                if anchor_hash is not None:
                    anchor_hash.add(row)
            for name in events:
                previous_occurrence = None
                for record in streams[name].at(position):
                    original = record[1:3]
                    owner, family, event_position, end = record[-4:]
                    if (owner != cut.initialization or family != FAMILY or event_position != position
                            or not 0 <= original[0] < position
                            or previous_occurrence is not None and original <= previous_occurrence
                            or name == 'expiry' and end != position
                            or name == 'revisions' and end is not None and end <= position):
                        raise ValueError('Rationing audit event ownership/membership differs')
                    checks[name].add(list(record[1:-4]))
                    previous_occurrence = original
            for name, count_key in (('facts', 'inserted'), ('revisions', 'revised'), ('expiry', 'expired')):
                actual = checks[name]
                if actual.count != body[count_key] or actual.finish() != body[name+'_digest']:
                    raise ValueError('Rationing audit '+name+' values/type/order differ')
                totals[name] += actual.count
            if body['count'] != (previous.body['count'] if previous else 0) + body['inserted'] - body['expired']:
                raise ValueError('Rationing audit membership transition differs')
            if anchor_hash is not None:
                anchor = body['anchor']
                if (not isinstance(anchor, dict) or anchor.get('count') != anchor_hash.count
                        or anchor.get('digest') != anchor_hash.finish()
                        or body['revised'] != 0 or body['expired'] != 0):
                    raise ValueError('Rationing audit anchor source values/type/order differ')
            elif body['anchor'] is not None:
                raise ValueError('Rationing audit successor has unexpected anchor')
            previous = current
            totals['cuts'] += 1
        if previous != cut or any(s.next is not None for s in streams.values()):
            raise ValueError('Rationing audit did not reach the exact selected cut')
    _lifetimes(cut)
    return dict(totals, root_digest=cut.root_digest, count=cut.body['count'])


def audit_image(run, item):
    return audit_cut(require_image(run, item))
