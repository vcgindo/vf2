"""Additional typed operational populations for the opt-in complete-day owner.

The accepted closing catalogue is unchanged. These mappings can only be chosen
for an explicitly named complete closing section/input path. No business payload
is stored in a JSON receipt, and existing input table selection is unchanged.
"""
import hashlib
import json
from pathlib import Path

SCHEMA_SHA256 = 'c36dee5784b6922d7a1fbe422052941918be9c2af20b4deb691b1561ff77d8bf'
_raw = (Path(__file__).resolve().parents[2]/'baseline/complete-daily-state-schema-v2.json').read_bytes()
if hashlib.sha256(_raw).hexdigest() != SCHEMA_SHA256:
    raise ValueError('Complete-day typed schema supplement differs')
CATALOG = json.loads(_raw)
TABLES = CATALOG['tables']
BINDINGS = CATALOG['bindings']


def input_table(path):
    prefix = 'input/opening/state/complete/'
    if not path.startswith(prefix):
        return None
    suffix = path[len(prefix):]
    population, separator, tail = suffix.partition('/')
    key = BINDINGS.get('closing/complete/' + population)
    if not key or separator != '/' or tail != 'values':
        raise ValueError('Undeclared complete-day input population: ' + path)
    return key


def validate_write(key, image, binding):
    if not key.startswith('complete/'):
        return
    if binding in BINDINGS and image == binding and BINDINGS[binding] == key:
        return
    if binding is None and input_table(image) == key:
        return
    raise ValueError('Complete-day typed image does not match its declared population')


def schema_statements():
    from mta.runtime.relational_state import table_sql, quote, PG_TYPES
    result = []
    for key, columns in sorted(TABLES.items()):
        result.append('CREATE TABLE '+table_sql(key)+' (vf_run_id uuid NOT NULL '
            'REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT, '
            'vf_image text NOT NULL, vf_ordinal bigint NOT NULL, '
            + ','.join(quote(name)+' '+PG_TYPES[kind] for name, kind in columns)
            + ', PRIMARY KEY(vf_run_id,vf_image,vf_ordinal))')
    return result
