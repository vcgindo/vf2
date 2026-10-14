"""Additive typed sources for native day producers and their own histories."""
from mta.application.operational_bor import NATIVE_SCHEMAS
from mta.application.production_output_policy import ATTRIBUTES
from mta.application.production_bor_contract import OUTPUT_FIELDS as BOR_FIELDS, QUANTITY_FIELDS

TABLES = {}
SCHEMAS = {}
for _name, _columns in NATIVE_SCHEMAS.items():
    _key = 'production/' + _name
    SCHEMAS[_key] = _columns
    TABLES[_key] = [(column['name'], column['sql_type'].split('(')[0]) for column in _columns]

# Existing manifests keep their original26/27-field reconstruction. Additive
# columns support only the explicitly versioned new native source writer.
TABLES['production/BORWithOrderAllocation'] += [(name, 'nvarchar') for name in ATTRIBUTES]
_history = TABLES['production/BOR_OrderAllocationHistory']
TABLES['production/BOR_OrderAllocationHistory'] = _history[:-1] + [(name, 'nvarchar') for name in ATTRIBUTES] + _history[-1:]
TABLES['production/SupplierDispatchReq'] = [(name, 'int' if name in (*QUANTITY_FIELDS, 'ReqTopOfBlack', 'CumulativeTOBlack') else 'nvarchar')
                                         for name in BOR_FIELDS]

TABLES['production/AllocatedOrders'] = [
    ('SKUCode','nvarchar'),('DestWhCode','nvarchar'),('SrcWhCode','nvarchar'),
    ('OrderKey','int'),('DueDate','date'),('CustomerOrderId','nvarchar'),('IsSpike','int'),
    ('Qty','int'),('OrderWiseAllocatedQty','int'),('BPP','decimal'),('OrderColor','nvarchar'),
    ('DueDateAtDest','date'),('PackSizeWiseAllocatedQty','int')]
TABLES['production/BOROARequirement'] = [('SKUCode','nvarchar'),('WhCode','nvarchar'),('AdvAllocDone','int'),('ParentWhCode','nvarchar')]
PATHS = {name: 'sources/production/'+name for name in
         ('BORWithOrderAllocation','BOR_OrderAllocationHistory','RRR_OrderAllocation',
          'RRR_OrderAllocationHistory','AllocatedOrders','BOROARequirement','SupplierDispatchReq')}


def save(run, name, rows, *, expanded=False):
    from mta.runtime.relational_state import save_image, load_image
    from mta.serialization import storage
    table = 'production/'+name
    expected = [field for field, _ in TABLES[table]]
    if not expanded and name in ('BORWithOrderAllocation', 'BOR_OrderAllocationHistory'):
        expected = [column['name'] for column in NATIVE_SCHEMAS[name]]
    if not expanded and name == 'BOROARequirement':
        expected = expected[:-1]
    if any(list(row) != expected for row in rows):
        raise ValueError('Native report source field order differs: '+name)
    value = storage(rows)
    metadata = save_image(run, PATHS[name], None, value, table=table)
    if load_image(run, metadata) != value:
        raise ValueError('Native report source typed readback differs: '+name)
    return metadata


def read(run, name):
    from mta.presentation.daily_sources import image_rows
    from mta.runtime.receipt_integrity import verify_root
    verify_root(run)
    return image_rows(run, PATHS[name])
