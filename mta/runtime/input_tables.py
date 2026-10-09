"""Additional typed input families absent from the canonical closing catalogue.

These are storage adapters, not calculation rules. Native field spellings and
wire types are retained in bounded image receipts; no input population is JSONB.
"""

import json
from pathlib import Path

TABLES = {
    'input/sob': [('SKUCode','nvarchar'), ('WHCode','nvarchar'), ('SupplierCode','nvarchar'), ('SOB','numeric')],
    'input/command_receipt': [('id','bigint'), ('digest','nvarchar'), ('before','nvarchar'), ('after','nvarchar')],
    'input/sku': [('sku_code','nvarchar'), ('description','nvarchar')],
    'input/location': [('location_code','nvarchar'), ('description','nvarchar'), ('location_type','nvarchar')],
    'input/stock': [('sku_code','nvarchar'), ('location_code','nvarchar'),
        *[(n,'numeric') for n in ('stock','utilized_stock','stock_percent_reservation','norm_percent_reservation')]],
    'input/logistics': [(n,'nvarchar') for n in ('sku_code','location_code','logistics_location','from_location','to_location')]
        + [(n,'numeric') for n in ('pack_size','weight','volume')],
    'input/vehicle': [('vehicle_id','bigint'), ('name','nvarchar'), ('weight_capacity','numeric'), ('volume_capacity','numeric')],
    'input/location_vehicle': [('location_code','nvarchar'), ('vehicle_id','bigint')],
    'input/policy': [('sku_code','nvarchar'), ('location_code','nvarchar'), ('rationing_priority','bigint')]
        + [('policy/'+n,'numeric') for n in ('pso_high','pso_low','pso_override','spike_high','spike_low','spike_override')],
    'input/norm_control': [('control_type','nvarchar'), ('effective_from','nvarchar'),
                          ('value','numeric'), ('source_event_id','nvarchar')],
    'input/string_values': [('value','nvarchar')],
    'input/integer_values': [('value','bigint')],
    'input/row_shape': [('shape_id','bigint')],
    'input/child_link': [('parent_ordinal','bigint'), ('child_ordinal','bigint')],
    'input/row_version': [('pk','bigint'), ('digest','nvarchar')],
    'input/scratch_name': [('table','nvarchar')],
    'input/mdm_task': [('task_pk','bigint'), ('task_id','nvarchar'), ('action_type','int'),
        ('subtask_pk','bigint'), ('subtask_status','nvarchar'), ('family','nvarchar'),
        ('task_digest','nvarchar'), ('history_digest','nvarchar')],
    'input/mdm_occurrence': [('family','nvarchar'), ('queue_kind','nvarchar'), ('source_pk','bigint'),
        ('ordinal','bigint'), ('sku_code','nvarchar'), ('location_code','nvarchar'),
        ('action_type','int'), ('approved','bit'), ('reverted','bit'), ('row_digest','nvarchar')],
    'input/mdm_history': [('family','nvarchar'), ('history_pk','bigint'), ('task_id','nvarchar'), ('row_digest','nvarchar')],
    'input/mdm_completion': [('task_id','nvarchar'), ('master_id','nvarchar'), ('task/pk','bigint'), ('task/digest','nvarchar'), ('digest','nvarchar')],
    'input/mdm_prune': [('task_id','nvarchar'), ('master_id','nvarchar'), ('digest','nvarchar')],
}
TABLES.update(json.loads((Path(__file__).resolve().parents[2]/
                         'baseline/daily-input-extra-schema-v2.json').read_text()))

# Explicit profile input representations; numeric families remain unchanged.
TEXT_VEHICLE_TABLES = {
    'input/vehicle_text': [('vehicle_id','nvarchar'), ('name','nvarchar'),
                         ('weight_capacity','numeric'), ('volume_capacity','numeric')],
    'input/location_vehicle_text': [('location_code','nvarchar'), ('vehicle_id','nvarchar')],
}
TABLES.update(TEXT_VEHICLE_TABLES)
# Supplier capture rows retain native float53/int32 and the queue occurrence ID.
for _name, _scalar, _destination in (
        ('sob', ('SOB', 'float'), True),
        ('moq_with_destination', ('MOQ', 'int'), True),
        ('moq_without_destination', ('MOQ', 'int'), False)):
    TABLES['input/supplier_' + _name] = [('id', 'bigint'), ('revision', 'bigint'), ('SKUCode', 'nvarchar'),
        *([('WhCode', 'nvarchar')] if _destination else []), ('SupplierCode', 'nvarchar'),
        _scalar, ('ActionType', 'int'), ('Approved', 'bit'), ('Reverted', 'bit')]


TABLES['input/supplier_task_revision'] = [('master_id', 'int'), ('task_id', 'nvarchar'), ('revision', 'bigint')]
TABLES['input/force_queue'] = [('id', 'bigint'), ('revision', 'bigint'),
    ('SKUCode', 'nvarchar'), ('WhCode', 'nvarchar'), ('NewNorm', 'int'),
    ('Approved', 'bit'), ('RequestedBy', 'nvarchar')]
TABLES['input/force_task_revision'] = [('task_id', 'nvarchar'), ('revision', 'bigint')]
TABLES['input/force_upload_log'] = [('id', 'bigint'), ('SKUCode', 'nvarchar'),
    ('WHCode', 'nvarchar'), ('OldNorm', 'int'), ('NewNorm', 'int'), ('Approved', 'bit'),
    ('RequestedBy', 'nvarchar'), ('ActionTimeStamp', 'datetime'), ('ActionId', 'int')]


_SEASON_REQUEST = [('SKUCode', 'nvarchar'), ('WhCode', 'nvarchar'), ('StartDate', 'date'),
    ('EndDate', 'date'), ('TargetNorm', 'int'), ('DeltaNormPercentage', 'int'),
    ('UpperLowerCap', 'int'), ('BuildupDuration', 'int'), ('ActivateDBM', 'bit')]
TABLES['input/season_queue'] = [('id', 'bigint'), ('revision', 'bigint'),
    *_SEASON_REQUEST, ('Approved', 'bit')]
TABLES['input/season_current'] = [('id', 'bigint'), ('revision', 'bigint'),
    ('ordinal', 'bigint'), *_SEASON_REQUEST, ('OrigNorm', 'int'), ('NewNorm', 'int'),
    ('Type', 'int'), ('Status', 'int'), ('Comment', 'nvarchar'), ('LastProcessedOn', 'date')]
TABLES['input/season_task_revision'] = [('master_id', 'int'), ('task_id', 'nvarchar'), ('revision', 'bigint')]


def schema_statements():
    from mta.runtime.relational_state import quote, table_sql, PG_TYPES
    result=[]
    for key, fields in sorted(TABLES.items()):
        result.append('CREATE TABLE '+table_sql(key)+' (vf_run_id uuid NOT NULL REFERENCES '
            'mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT, vf_image text NOT NULL, '
            'vf_ordinal bigint NOT NULL, '+','.join(quote(n)+' '+PG_TYPES[t] for n,t in fields)
            +', PRIMARY KEY(vf_run_id,vf_image,vf_ordinal))')
    return result

TABLES['input/stop_pipo_queue'] = [('id', 'bigint'), ('revision', 'bigint'),
    ('SKUCode', 'nvarchar'), ('WhCode', 'nvarchar')]
TABLES['input/stop_pipo_task_revision'] = [('task_id', 'nvarchar'), ('revision', 'bigint')]

TABLES['input/phase_out_queue'] = [('id', 'bigint'), ('revision', 'bigint'),
    ('SKUCode', 'nvarchar'), ('WhCode', 'nvarchar'), ('PhaseInSKUCode', 'nvarchar'), ('Approved', 'bit')]
TABLES['input/phase_in_norm_queue'] = [('id', 'bigint'), ('revision', 'bigint'),
    ('SKUCode', 'nvarchar'), ('WhCode', 'nvarchar'), ('TargetNorm', 'int'), ('Approved', 'bit')]
TABLES['input/phase_controls_task_revision'] = [('master_id', 'int'), ('task_id', 'nvarchar'), ('revision', 'bigint')]
