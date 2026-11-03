"""Advance a BTR snapshot only from its own compact predecessor and dated import."""
from contextlib import closing
from itertools import groupby
import re
from xml.sax.saxutils import quoteattr

from django.db import connection

from mta.application.stage_observation import summary
from mta.domain import btr_finalization as btr
from mta.presentation import btr_snapshot_storage as storage
from mta.runtime import relational_state as typed


FAMILIES = ('BPPTrendTech', 'BPPTrendEcon', 'BPPTrendDispatch', 'BPPTrendPhysicalInv',
            'BufferTrendReport', 'BufferTrendReportEcon', 'BufferTrendDispatch', 'BufferTrendPhysicalInv')
ATTRIBUTE = re.compile(r""" D([1-9][0-9]?)=("[^"]*"|'[^']*')""")


def shifted(text, distance):
    """Keep the original quoted wire literals, including their escaping and numeric spelling."""
    end = text.find('/>') + 2
    if not text.startswith('<X') or end < 2 or len(text) % end:
        return None
    fragment = text[:end]
    if any(not text.startswith(fragment, at) for at in range(end, len(text), end)):
        return None
    result = ['<X']
    previous = 0
    position = 2
    while position < end - 2:
        token = ATTRIBUTE.match(fragment, position, end - 2)
        if token is None:
            return None
        slot = int(token[1])
        if not previous < slot <= 90:
            return None
        if slot > distance:
            result.extend((' D', str(slot-distance), '=', token[2]))
        previous = slot
        position = token.end()
    return ''.join(result)


def previous_groups(run, item, distance):
    """Read the ordinal roster once. Only owners carry XML over the wire."""
    storage.require(item)
    columns = ','.join(map(typed.quote, storage.XML))
    query = ('SELECT vf_ordinal,"SKUCode","WhCode",vf_xml_ordinal,'+columns+' FROM '+
             typed.table_sql(storage.TABLE)+' WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal')
    cache = {}
    retained_bytes = 0
    with connection.chunked_cursor() as cursor:
        cursor.execute(query, [run.pk, storage.PATH])
        while batch := cursor.fetchmany(256):
            for ordinal, sku, location, owner, *values in batch:
                if ordinal == owner:
                    prefixes = tuple(shifted(value, distance) for value in values)
                    if ordinal < item['reuse_before']:
                        retained_bytes += sum(len(value.encode()) for value in prefixes if value is not None)
                        if len(cache) >= storage.MAX_ENTRIES or retained_bytes > storage.MAX_BYTES:
                            raise ValueError('BTR predecessor XML exceeds its accepted lookup budget')
                        cache[ordinal] = prefixes
                else:
                    prefixes = cache[owner]
                if sku is not None and location is not None:
                    yield (sku, location), owner, prefixes


def _pair(row):
    return row['SKUCode'], row['WhCode']


def _advance_snapshot(state, prior, distance):
    result = btr._snapshot(state, _owned=True, _include_xml=False)
    streams = [groupby(state[name], _pair) for name in FAMILIES]
    old = next(prior, None)
    hits = fallbacks = cache_bytes = 0
    transitions = {}
    for row in result['BTRSnapshotForUI']:
        key = _pair(row)
        groups = [next(stream, None) for stream in streams]
        if None in key or any(group is None or group[0] != key for group in groups):
            # Preserve even an unusual bag or join spelling using the original owner.
            return btr._snapshot(state, _owned=True)
        bags = [list(group[1]) for group in groups]
        while old is not None and old[0] < key:
            old = next(prior, None)
        if distance >= 90:
            owner, prefixes = -1, ('<X',)*8
        elif old is not None and old[0] == key and all(value is not None for value in old[2]):
            _, owner, prefixes = old
        else:
            row.update((field, btr._xml_rows(bag)) for field, bag in zip(storage.XML, bags, strict=True))
            fallbacks += 1
            continue
        # The original pivot replicates an identical row for each latest BPP
        # occurrence. The new roster supplies its current multiplicity.
        cells = tuple((len(bag), None if bag[0]['D90'] is None else str(bag[0]['D90'])) for bag in bags)
        transition = owner, cells
        values = transitions.get(transition)
        if values is None:
            values = tuple((prefix + ('' if value is None else ' D90='+quoteattr(value)) + '/>') * count
                           for prefix, (count, value) in zip(prefixes, cells, strict=True))
            if len(transitions) < storage.MAX_ENTRIES and cache_bytes < storage.MAX_BYTES:
                size = sum(len(v.encode()) for v in values)
                if size <= storage.MAX_BYTES-cache_bytes:
                    transitions[transition] = values
                    cache_bytes += size
        else:
            hits += 1
        row.update(zip(storage.XML, values, strict=True))
    summary('btr_snapshot_xml_advance', rows=len(result['BTRSnapshotForUI']), reused_transitions=hits,
            full_row_fallbacks=fallbacks, cached_transitions=len(transitions), cached_bytes=cache_bytes)
    return result


def reporting(run, predecessor, prior_image, state, facts, settings, importer, *, advance_trends=False):
    distance = (run.business_date - predecessor.business_date).days
    if predecessor.pk != run.predecessor_id or distance <= 0:
        raise ValueError('BTR snapshot advancement requires its own earlier day')
    selected = btr._selected_settings(settings, importer)
    day = run.business_date
    if advance_trends:
        from mta.presentation import btr_successor_trends
        current = btr_successor_trends.generate(run, predecessor, prior_image, state, facts)
    else:
        current = btr._generate_trends(day, state, facts, _owned=True)
    current = btr._update_br_age(current, facts, 'BufferTrendDispatch', selected['br_tolerance'], _owned=True)
    current = btr._update_br_age(current, facts, 'BufferTrendPhysicalInv', selected['br_tolerance'], _owned=True)
    current = btr._availability(current, _owned=True)
    current = btr._colour_age(day, current, selected['generate_age'], selected['age_tolerance'], _owned=True)
    with closing(previous_groups(predecessor, prior_image, distance)) as prior:
        current = _advance_snapshot(current, prior if distance < 90 else iter(()), distance)
    current = btr._count_graph(current, _owned=True)
    current = btr._chronic(current, facts, _owned=True)
    current = btr._norm_suggestions(day, current, facts, selected, _owned=True)
    return {name: current[name] for name in btr.DERIVED_TABLES}
