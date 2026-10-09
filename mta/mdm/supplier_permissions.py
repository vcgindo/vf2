"""Deployed GenericFunction expansion and trimmed hierarchy join for master4/5."""
from collections import Counter

from mta.presentation.context import permission_catalogue
from mta.presentation.permissions import expand_permission_ids


def hierarchy_key(value):
    return value.strip(' ').lower() if value is not None else None


def triples(kind, ids):
    records = permission_catalogue()[kind]['records']
    expanded = expand_permission_ids(records, ids or [])
    result = Counter()
    for row in records:
        values = tuple(hierarchy_key(row['level_' + str(i)]) for i in (1, 2, 3))
        if row['id'] in expanded and None not in values:
            result[values] += 1
    return result


def sql_permissions(kind, ids):
    values = [triple for triple, count in triples(kind, ids).items() for _ in range(count)]
    if not values:
        return 'SELECT NULL::text,NULL::text,NULL::text WHERE FALSE', []
    return ('VALUES ' + ','.join('(%s::text,%s::text,%s::text)' for _ in values),
            [value for triple in values for value in triple])


def scope(source, model, code_name, prefix, kind, ids):
    allowed = triples(kind, ids)
    return {getattr(row, code_name) for row in model.objects.filter(source=source, owner='Importer')
            if tuple(hierarchy_key(getattr(row, prefix + str(i))) for i in (1, 2, 3)) in allowed}
