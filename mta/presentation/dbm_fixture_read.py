"""Bound the immutable fixture's DBM inputs before transferring them to Python.

The native display/filter selector remains authoritative. Admission binds the
full-value loader receipts and write-denial triggers; there is no row cache.
"""
from django.db import connection

from mta.presentation import fixture
from mta.presentation.context import scope
from mta.presentation.dbm import key
from mta.presentation.selective import image_rows
from mta.runtime.relational_state import table_sql, quote, wire_value


def pair_condition(pairs, location):
    """Exact Python pair membership, including None, without join multiplication."""
    ordinary = [pair for pair in pairs if None not in pair]
    nullable = [pair for pair in pairs if None in pair]
    clauses, params = [], []
    columns = ('"SKUCode"', quote(location))
    if ordinary:
        clauses.append('(' + ','.join(columns) + ') IN (VALUES ' +
                       ','.join(['(%s,%s)'] * len(ordinary)) + ')')
        params.extend(value for pair in ordinary for value in pair)
    for pair in nullable:
        parts = []
        for column, value in zip(columns, pair):
            parts.append(column + (' IS NULL' if value is None else '=%s'))
            if value is not None:
                params.append(value)
        clauses.append('(' + ' AND '.join(parts) + ')')
    return ' OR '.join(clauses) or 'FALSE', params


def grid_state(run, payload):
    fixture.binding()  # Also fail closed when called outside the HTTP endpoint.
    names = ('Suggestions', 'SKUDescriptionTbl', 'SiteDescriptionTbl',
             'ReasonCodes', 'SkuAttributeData', 'LocationAttributeData')
    state = {name: image_rows(run, 'closing/dbm/' + name) for name in names}
    selected = state['Suggestions']
    if payload is not None:
        products, locations = scope(payload, attributes=state)
        selected = [row for row in selected if key(row)[0] in products and key(row)[1] in locations]
    state['Suggestions'] = selected
    pairs = set(map(key, selected))
    for name in ('DBMMaster', 'NormAcceptanceTbl', 'SkuLocAttributeData'):
        path = 'closing/dbm/' + name
        item = fixture.image_metadata(run, path)
        fields = item['fields']
        location = 'LocCode' if name == 'SkuLocAttributeData' else 'WhCode'
        condition, params = pair_condition(pairs, location)
        with connection.cursor() as cursor:
            cursor.execute('SELECT vf_ordinal,' + ','.join(quote(column) for _, column, _ in fields) +
                ' FROM ' + table_sql(item['table']) + ' WHERE vf_run_id=%s AND vf_image=%s AND (' +
                condition + ') ORDER BY vf_ordinal', [run.pk, path, *params])
            records = cursor.fetchall()
        ordinals = [record[0] for record in records]
        if any(not 0 <= ordinal < item['count'] for ordinal in ordinals) or ordinals != sorted(set(ordinals)):
            fixture.unavailable('dbm_selected_ordinal_changed')
        state[name] = [{field: wire_value(value, kind) for (field, _, kind), value in zip(fields, row[1:])}
                       for row in records]
    return state
