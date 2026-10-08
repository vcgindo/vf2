"""Lossless projection of live producer values for later BOR materialization.

This module never invokes a calculation or reads a trace archive. Empty inputs
must be explicit complete capabilities in the live calculation result.
"""
from mta.application.operational_bor import _int


BAND_MAP = (
    ('SKUCode', 'sku_code'), ('WhCode', 'location_code'),
    ('ParentWhCode', 'parent_location_code'),
    ('OrderReqBlack', 'order_req_black'), ('OrderReqRed', 'order_req_red'),
    ('OrderReqYellow', 'order_req_yellow'), ('OrderReqGreen', 'order_req_green'),
    ('OrderReqBlue', 'order_req_blue'), ('NormReqBlack', 'norm_req_black'),
    ('NormReqRed', 'norm_req_red'), ('NormReqYellow', 'norm_req_yellow'),
    ('NormReqGreen', 'norm_req_green'), ('OrderBlackBand', 'order_black_band'),
    ('OrderRedBand', 'order_red_band'), ('OrderYellowBand', 'order_yellow_band'),
    ('OrderGreenBand', 'order_green_band'),
)
STOCK_FIELDS = ('sku_code', 'source_location_code', 'allocated_quantity')
CAPTURE_POLICY = 'cohort2-operational-sources-v1'


def _population(calculated, name):
    if not isinstance(calculated, list):
        raise ValueError('Live complete calculation capabilities required')
    matches = [item for item in calculated if isinstance(item, dict) and item.get('capability') == name]
    if len(matches) != 1 or set(matches[0]) != {'capability', 'rows'} or not isinstance(matches[0]['rows'], list):
        raise ValueError('Missing/duplicate explicit producer capability: ' + name)
    return matches[0]['rows']


def _code(value, *, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or len(value.encode('utf-16-le')) // 2 > 50:
        raise ValueError('Native producer code exceeds nvarchar(50) contract')
    return value


def capture_rows(calculated):
    bands = []
    for source in _population(calculated, 'r1_requirement_band'):
        if not isinstance(source, dict) or any(field not in source for _, field in BAND_MAP):
            raise ValueError('Requirement-band producer fields missing')
        row = {}
        for ordinal, (native, field) in enumerate(BAND_MAP):
            value = source[field]
            row[native] = (_code(value, nullable=native == 'ParentWhCode') if ordinal < 3
                           else None if value is None else _int(value))
        bands.append(row)
    stock = []
    for source in _population(calculated, 'r1_advance_stock_allocation'):
        if (not isinstance(source, dict) or any(field not in source for field in STOCK_FIELDS)
                or source.get('allocation_type') != 'advance-stock'):
            raise ValueError('Explicit stock-only allocation producer required')
        stock.append(dict(sku_code=_code(source['sku_code']),
            source_location_code=_code(source['source_location_code']),
            allocated_quantity=_int(source['allocated_quantity'])))
    return dict(requirement_bands=bands, advance_stock_allocations=stock)
