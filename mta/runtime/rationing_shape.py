"""Exact ordered wire descriptors for the canonical rationing population."""
from mta.domain.btr_rationing_history import COLUMNS

BY_NAME = {column['name']: column for column in COLUMNS}


def require_fields(fields, count, *, source_order=False):
    if type(count) is not int or count < 0 or type(fields) is not list:
        raise ValueError('Rationing count/fields shape differs')
    if fields == [] and count == 0:
        return
    if len(fields) != len(COLUMNS):
        raise ValueError('Rationing fields require the complete ordered roster')
    columns = COLUMNS
    if source_order:
        names = [f[0] for f in fields if type(f) is list and len(f) == 3 and type(f[0]) is str]
        if set(names) != BY_NAME.keys():
            raise ValueError('Rationing source descriptor roster differs')
        columns = [BY_NAME[name] for name in names]
    for field, column in zip(fields, columns):
        allowed = {'str'}  # Old descriptors use str for an entirely NULL column.
        if column['type'] == 'int':
            allowed.add('int')
        elif column['type'] == 'bit':
            allowed.update(('bool', 'int'))
        elif column['type'] == 'decimal':
            allowed.update(('int', 'float'))
        if (type(field) is not list or len(field) != 3
                or field[:2] != [column['name'], column['name']]
                or type(field[2]) is not str or field[2] not in allowed):
            raise ValueError('Rationing field mapping or wire type differs')
