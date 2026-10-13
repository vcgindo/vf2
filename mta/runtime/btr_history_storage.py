"""Additive typed, owned BTR history; earlier catalogues remain immutable."""
from mta.domain.btr_rationing_history import COLUMNS, FIELDS, POPULATION, validate_target

TABLE = 'BTR/'+POPULATION
OPENING = 'input/opening/state/btr/'+POPULATION+'/values'
FROZEN = 'input/predecessor/btr/'+POPULATION+'/values'
TABLES = {TABLE:[(c['name'],c['type']) for c in COLUMNS]}
BINDINGS = {'closing/btr/'+POPULATION:TABLE}


def validate_write(image,binding,rows):
    if not (image==FROZEN and binding is None or BINDINGS.get(binding)==TABLE and image==binding):
        raise ValueError('BTR history typed owner differs')
    for row in rows:
        if tuple(row)!=FIELDS:
            raise ValueError('Complete ordered BTR history fields required')
        validate_target(row)
