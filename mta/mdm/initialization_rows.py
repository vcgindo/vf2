"""Explicit initialization population schemas; no subset/table guessing."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import math

from mta.runtime.relational_state import CATALOG, STORAGE_TABLES, COMPLETE_BINDINGS
from mta.application.r1_daily_input import PRIOR_TABLES
from mta.runtime.dbm_phase_storage import OPENING as PHASE_OPENING, TABLE as PHASE_TABLE
from mta.runtime.btr_history_storage import OPENING as BTR_OPENING, TABLE as BTR_TABLE

TABLES = {'input/opening/state/'+key.removeprefix('closing/')+'/values': '/'.join(table)
          for key, table in CATALOG['bindings'].items() if key.startswith('closing/')}
TABLES.update({'input/opening/state/'+key.removeprefix('closing/')+'/values': table
              for key, table in COMPLETE_BINDINGS.items()})
TABLES[PHASE_OPENING] = PHASE_TABLE
TABLES[BTR_OPENING] = BTR_TABLE
TABLES['input/opening/state/importer_settings/values'] = 'Importer/ImporterSettingsTbl'
TABLES.update({
    'input/pair_exclusions/values': 'Intermediate/ExclusionRecords',
    'input/profile/daily/settings/values': 'Importer/ImporterSettingsTbl',
    'input/profile/daily/vf_settings/values': 'Importer/ImporterSettingsTbl',
    'input/profile/delivery/btr_settings/values': 'Importer/ImporterSettingsTbl',
    'input/profile/delivery/conditional_dbm/importer_vf_settings/values': 'Importer/VFSettings',
    'input/profile/delivery/btr_history/importer_vf_settings/values': 'Importer/VFSettings',
    **{'input/profile/daily/module_sources/'+name+'/values':'Intermediate/SKULoc_DailyData'
       for name in ('distributor_norms','vendor_master')},
    **{'input/profile/calculation/'+name+'/values': table for name, table in (
        ('skus', 'input/sku'), ('locations', 'input/location'),
        ('stock_openings', 'input/stock'), ('policies', 'input/policy'))},
    **{'input/profile/calculation/logistics/'+name+'/values': table for name, table in (
        ('items', 'input/logistics'), ('vehicles', 'input/vehicle'),
        ('location_vehicles', 'input/location_vehicle'))},
})
SCALARS = {'input/profile/daily/'+name: 'input/string_values' for name in
           ('distributor_codes', 'vendor_codes', 'vector_dms_codes')}
SCALARS['input/profile/calculation/replenishment_exclusions'] = 'input/string_values'
EMPTY_STRUCTURES = frozenset(('input/opening/state/dbm/IntermediateTables',))


def schema(path, rows):
    table = TABLES.get(path) or SCALARS.get(path) or SCALARS.get(path.removesuffix('/values'))
    if not table or table not in STORAGE_TABLES:
        raise ValueError('Undeclared initialization population: '+path)
    if path in ('input/profile/calculation/logistics/vehicles/values',
                'input/profile/calculation/logistics/location_vehicles/values'):
        ids = [row['vehicle_id'] for row in rows if 'vehicle_id' in row]
        if ids and all(type(value) is str for value in ids):
            table += '_text'
    fields = dict(STORAGE_TABLES[table])
    bpr = path.removeprefix('input/opening/state/bpr/').removesuffix('/values')
    if path.startswith('input/opening/state/bpr/') and bpr in PRIOR_TABLES:
        fields = {name: fields[name] for name in PRIOR_TABLES[bpr]}
    return table, fields


def scalar(value, kind, path):
    if value is None:
        return
    if kind in ('nvarchar', 'nchar', 'varchar', 'xml'):
        valid = type(value) is str and '\x00' not in value
    elif kind in ('int', 'bigint'):
        limit = 2**31 if kind == 'int' else 2**63
        valid = type(value) is int and -limit <= value < limit
    elif kind == 'bit':
        valid = type(value) is bool or type(value) is int and value in (0, 1)
    elif kind in ('float', 'real'):
        valid = type(value) in (int, float) and math.isfinite(value)
    elif kind in ('decimal', 'numeric'):
        try:
            valid = type(value) in (str, int, float) and Decimal(str(value)).is_finite()
        except InvalidOperation:
            valid = False
    elif kind in ('date', 'datetime'):
        try:
            parsed = (date if kind == 'date' else datetime).fromisoformat(value)
            valid = type(value) is str and parsed.isoformat() == value
            if kind == 'datetime':
                valid = valid and parsed.tzinfo is None
        except (ValueError, TypeError):
            valid = False
    else:
        valid = False
    if not valid:
        raise ValueError('Initialization field type differs: '+path)


def select(fields, path, rows):
    if path in ('input/profile/delivery/conditional_dbm/importer_vf_settings/values',
                'input/profile/delivery/btr_history/importer_vf_settings/values'):
        from mta.domain.dbm_conditional import validate_settings_rows
        # The raw contract validates lists; the internal typed writer projects
        # them through a reiterable Rows sequence. Validate its exact records.
        validate_settings_rows(list(rows))
    if path.removesuffix('/values') in EMPTY_STRUCTURES:
        if rows != []:
            raise ValueError('Explicit empty initialization scratch list required: '+path)
        return None  # Shape metadata represents []; there are no typed state rows.
    table, expected = schema(path, rows)
    if set(fields) != set(expected) and rows:
        raise ValueError('Initialization field roster differs: '+path)
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(expected):
            raise ValueError('Initialization field roster differs: '+path)
        for field, kind in expected.items():
            if path.startswith('input/profile/'):
                nullable = {'policy/pso_override', 'policy/spike_override'}
                if path=='input/profile/calculation/stock_openings/values':
                    nullable.add('stock')  # Unknown PRIOR stock; current daily producer owns its replacement.
                if '/logistics/items/' in path:
                    # Producer-owned attributes retain canonical NULL exclusion.
                    nullable |= {'logistics_location', 'pack_size', 'weight', 'volume'}
                if row[field] is None and field not in nullable:
                    raise ValueError('NULL in required initialization configuration field: '+path+'/'+field)
                if field in ('sku_code', 'location_code', 'from_location', 'to_location', 'vehicle_id') and type(row[field]) is str and not row[field].strip():
                    raise ValueError('Blank initialization configuration identity: '+path+'/'+field)
            scalar(row[field], kind, path+'/'+field)
    return table


def validate_tree(value, path='input'):
    if path in EMPTY_STRUCTURES:
        if value != [] or type(value) is not list:
            raise ValueError('Explicit empty initialization scratch list required: '+path)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            validate_tree(child, path+'/'+key)
    elif isinstance(value, list):
        if path in SCALARS:
            select(('value',), path, [{'value': item} for item in value])
        else:
            # Flatten the declared policy object, without admitting arbitrary
            # nested bags or manufacturing absent fields.
            rows = []
            for row in value:
                if not isinstance(row, dict):
                    raise ValueError('Explicit initialization record required: '+path)
                flat = {}
                for key, item in row.items():
                    if isinstance(item, dict) and key == 'policy' and path.endswith('/policies'):
                        flat.update({'policy/'+name: child for name, child in item.items()})
                    elif isinstance(item, (dict, list)):
                        raise ValueError('Undeclared nested initialization field: '+path+'/'+key)
                    else:
                        flat[key] = item
                rows.append(flat)
            select(rows[0] if rows else (), path+'/values', rows)
