"""Advance the eight raw BTR windows from the run's own compact predecessor."""
from contextlib import closing
from datetime import timedelta
from itertools import groupby, zip_longest
from sys import getsizeof
from xml.etree import ElementTree

from mta.application.stage_observation import summary
from mta.domain import btr_finalization as btr
from mta.domain.sql_identity_keys import group_key
from mta.presentation import btr_incremental_xml as snapshot
from mta.presentation import btr_snapshot_storage as storage
from mta.runtime.btr_import_relation import HISTORY


OPERANDS = ('TechPen', 'EcoPen', 'DispatchPen', 'PhysicalInventoryPen',
            'TechColor', 'EcoColor', 'DispatchColor', 'PhysicalInventoryColor')
WIRE = {'str': str, 'int': int, 'float': float}


class _UseFullWindow(Exception):
    """The predecessor cannot supply this exact typed window."""


def _latest_rows(history, day):
    newest, retained = {}, set()
    cutoff = day - timedelta(days=90)
    for row in history:
        when = btr._day(row['ReportDate'])
        spelling = row['SKUCode'], row['WHCode']
        if None in spelling or not cutoff < when <= day:
            raise _UseFullWindow
        key = group_key(*spelling)
        if when < day:
            retained.add(spelling)
        entry = newest.get(key)
        if entry is not None:
            previous, bag = entry
            if (bag[0]['SKUCode'], bag[0]['WHCode']) != spelling:
                # Let the canonical producer report its source ambiguity.
                raise _UseFullWindow
            if when == previous:
                bag.append(row)
                continue
            if when < previous:
                continue
        newest[key] = when, [row]
    return [row for _, bag in newest.values() for row in bag], retained


def _decode(prefixes, kinds):
    matrices = []
    size = 0
    for prefix, convert in zip(prefixes, kinds, strict=True):
        if prefix is None:
            raise _UseFullWindow
        try:
            cells = ElementTree.fromstring(prefix + '/>').attrib
            for slot, literal in cells.items():
                value = convert(literal)
                if str(value) != literal:
                    raise _UseFullWindow
                cells[slot] = value
                size += getsizeof(slot) + getsizeof(value)
        except (ElementTree.ParseError, ValueError, OverflowError) as exc:
            raise _UseFullWindow from exc
        matrices.append(cells)
        size += getsizeof(cells)
    return matrices, size + getsizeof(matrices)


def _advance(day, state, facts, previous, kinds):
    history = state['BPR']
    latest, retained = _latest_rows(history, day)
    # The original producer still owns scalar fields, ordering, D90 and the
    # multiplicity of the newest occurrences, including keys absent today.
    result = btr._generate_trends(day, {**state, 'BPR': latest}, facts, _owned=True)
    result['BPR'] = history

    def pair(row):
        return row['SKUCode'], row['WhCode']

    streams = [groupby(result[name], pair) for name in snapshot.FAMILIES]
    prior = next(previous, None)
    decoded, cache_bytes = {}, 0
    for groups in zip_longest(*streams):
        if any(group is None for group in groups):
            raise _UseFullWindow
        key = groups[0][0]
        if any(group[0] != key for group in groups):
            raise _UseFullWindow
        if key not in retained:
            continue
        while prior is not None and prior[0] < key:
            prior = next(previous, None)
        if prior is None or prior[0] != key:
            raise _UseFullWindow
        _, owner, prefixes = prior
        matrices = decoded.get(owner)
        if matrices is None:
            matrices, size = _decode(prefixes, kinds)
            if len(decoded) < storage.MAX_ENTRIES and cache_bytes + size <= storage.MAX_BYTES:
                decoded[owner] = matrices
                cache_bytes += size
        for (_, rows), cells in zip(groups, matrices, strict=True):
            for row in rows:
                row.update(cells)
    summary('btr_trend_window_advance', import_rows=len(history), latest_rows=len(latest),
            cached_owners=len(decoded), cached_bytes=cache_bytes)
    return result


def generate(run, predecessor, prior_image, state, facts):
    day = run.business_date
    distance = (day - predecessor.business_date).days
    if predecessor.pk != run.predecessor_id or distance <= 0:
        raise ValueError('BTR trends require the run\'s own earlier predecessor')
    image = run.production_manifest['images'][HISTORY]
    from mta.runtime import btr_import_image
    if not btr_import_image.owns(image):
        raise ValueError('BTR trends require the accepted dated import')
    current_count = len(facts['vf_RationedReqReport'])
    # A second cursor over the predecessor does not pay for a shallow import.
    # At a full-window gap the current facts already determine every cell.
    if distance < 90 and len(state['BPR']) > 4 * max(prior_image['count'], current_count):
        wire = {name: kind for _, name, kind in image['fields']}
        if all(wire.get(name) in WIRE for name in OPERANDS):
            kinds = [WIRE[wire[name]] for name in OPERANDS]
            with closing(snapshot.previous_groups(predecessor, prior_image, distance)) as prior:
                try:
                    return _advance(day, state, facts, prior, kinds)
                except _UseFullWindow:
                    summary('btr_trend_window_full_fallback', import_rows=len(state['BPR']))
    return btr._generate_trends(day, state, facts, _owned=True)
