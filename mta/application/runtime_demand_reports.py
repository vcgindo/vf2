"""Exact retained Spike and Total Requirement runtime-report projections.

Only data cells are produced. Query hashes bind the projection; deployment Id
controls placement order elsewhere. Neither SELECT has an ORDER BY: retain
supplied occurrence order without claiming canonical file-order parity.
"""
from collections.abc import Mapping
import hashlib
from itertools import product

from mta.application.row_bag_lookup import AsciiBagLookup
from mta.domain.complete_daily_scalars import ascii_equal
from mta.row_sequences import is_record_rows

SPIKE_QUERY = '2bd3bfa4af68d5abc34c63fda94104450466ab2002ef2a405422ea873246393e'
TOTAL_QUERY = 'a1708de0d079e15dcf5ff7db1eed70efd97943d89ff94ce864394b43b7c16fb3'
SPIKE_FIELDS = ('OrderKey', 'CustomerOrderId', 'PartId', 'IsSpike', 'IsElephant',
                'OriginalQty', 'Qty', 'SKUCode', 'WhCode', 'FirstServicingWhCode',
                'DueDate', 'IntroDate')
TOTAL_CORE = tuple('SKUCode SKUName WhCode WhName Norm VirtualNorm VirtualNodeNorm '
    'SpikeThreshold PSOThreshold Stock GIT StockForRationing StockForReqCalc TechPen '
    'TechColor EcoPen EcoColor DispatchPen DispatchColor DispatchColorSequence '
    'ReqTopOfRed ReqTopOfYellow ReqTopOfGreen ParentWhCode ParentWhName ParentNorm '
    'TechPenParent TechColorParent EcoPenParent EcoColorParent Req '
    'AllocatedForVirtualNormReq AllocatedForNormReq AllocatedForSnPReq '
    'AllocatedForDirectOrders RationedReq PackSize RationedCasePacks LeftoverParentStock '
    'LeftoverStock ParentPackSize IsNormed DirectSpikeOverdue SpikeOverdueAtParent '
    'PSO RelPSOAndCNR ResidualChildrenSnP SnPToNetOff SnPNettedOff ResidualSnP '
    'EcoStockForNormReq NormReq BlueReq AvgSiblingsNorm AvgChildrenNorm '
    'ParentStockForNormRationing ParentStockForSnPRationing ParentStockForRationing '
    'StockPercentageForRationing NormPercentReservation ParentStockPercentageForRationing '
    'ParentNormPercentReservation'.split())
ATTRIBUTES = tuple('c' + str(n) for n in range(1, 16))
SUPPLIER_BANDS = ('ReqTopOfRed', 'ReqTopOfYellow', 'ReqTopOfGreen')
RATIONED_FIELDS = tuple(field for field in TOTAL_CORE if field not in (*SUPPLIER_BANDS, 'ParentWhName'))
# Positional expression labels, not SQLCMD metadata or invented CSV headers.
TOTAL_COLUMNS = TOTAL_CORE + tuple(owner + '.' + field
                                  for owner in ('C', 'D', 'E') for field in ATTRIBUTES)


def _query(definition, expected):
    query = definition.get('Query') if isinstance(definition, Mapping) else None
    if type(query) is not str or hashlib.sha256(query.encode('utf-8')).hexdigest() != expected:
        raise ValueError('Exact retained runtime demand Query required')


def _population(rows, name):
    if not is_record_rows(rows):
        raise ValueError('Explicit typed runtime report source required: ' + name)
    return rows


def _each(rows, fields, name):
    for row in rows:
        if not isinstance(row, Mapping) or not set(fields) <= row.keys():
            raise ValueError('Runtime report source columns missing: ' + name)
        yield row


def _lookup(rows, keys, fields, name):
    _population(rows, name)
    for row in _each(rows, (*keys, *fields), name):
        for field in keys:
            value = row[field]
            if value is not None and (type(value) is not str or not value.isascii()):
                raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: ASCII SQL text equality')
    return AsciiBagLookup(rows, keys, ascii_equal)


def _matches(lookup, source, left, right, *, outer=False):
    matches = [row for row in lookup.candidates(source, left)
               if all(ascii_equal(source[a], row[b]) for a, b in zip(left, right, strict=True))]
    return matches or ([None] if outer else [])


def _without_commas(value):
    # REPLACE(ISNULL(expression,''),',','') from this SELECT, not a CSV policy.
    if value is None:
        return ''
    if type(value) is not str:
        raise ValueError('Native runtime report description text required')
    return value.replace(',', '')


def _coalesce(row, field, fallback):
    return fallback if row is None or row[field] is None else row[field]


def spike_orders(definition, *, spike_order_data):
    """Yield the literal 12 selected cells, including duplicates and typed NULLs."""
    _query(definition, SPIKE_QUERY)
    _population(spike_order_data, 'SpikeOrderData')
    return (tuple(row[field] for field in SPIKE_FIELDS)
            for row in _each(spike_order_data, SPIKE_FIELDS, 'SpikeOrderData'))


def total_requirements(definition, *, rationed_report, supplier_dispatch,
                       site_descriptions, sku_loc_attributes, sku_attributes,
                       location_attributes):
    """Yield the 107-column native join without reducing any occurrence bag.

    Supplier and parent descriptions are LEFT JOINs. All three attribute bags
    are INNER JOINs. A NULL supplier falls back to A.ParentWhCode; empty text
    does not. The three attribute bags are indexed once, not scanned per row.
    Actual typed source ownership belongs to the caller's accepted phase.
    """
    _query(definition, TOTAL_QUERY)
    _population(rationed_report, 'vf_RationedReqReport')
    suppliers = _lookup(supplier_dispatch, ('SKUCode', 'WHCode'),
                        ('SupplierCode', 'OriginalReq', 'DispatchReq', *SUPPLIER_BANDS), 'SupplierDispatchReq')
    sites = _lookup(site_descriptions, ('WHCode',), ('WHDescription',), 'SiteDescriptionTbl')
    pairs = _lookup(sku_loc_attributes, ('SKUCode', 'LocCode'), ATTRIBUTES, 'SkuLocAttributeData')
    skus = _lookup(sku_attributes, ('SKUCode',), ATTRIBUTES, 'SkuAttributeData')
    locations = _lookup(location_attributes, ('WHCode',), ATTRIBUTES, 'LocationAttributeData')

    def records():
        for row in _each(rationed_report, RATIONED_FIELDS, 'vf_RationedReqReport'):
            for field in ('SKUCode', 'WhCode', 'ParentWhCode'):
                value = row[field]
                if value is not None and (type(value) is not str or not value.isascii()):
                    raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: ASCII SQL text equality')
            # These bags are independent of the supplier occurrence.
            attrs = (
                _matches(pairs, row, ('SKUCode', 'WhCode'), ('SKUCode', 'LocCode')),
                _matches(skus, row, ('SKUCode',), ('SKUCode',)),
                _matches(locations, row, ('WhCode',), ('WHCode',)),
            )
            for supplier in _matches(suppliers, row, ('SKUCode', 'WhCode'),
                                     ('SKUCode', 'WHCode'), outer=True):
                parent = _coalesce(supplier, 'SupplierCode', row['ParentWhCode'])
                if parent is not None and (type(parent) is not str or not parent.isascii()):
                    raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: ASCII SQL text equality')
                for site in _matches(sites, {'WHCode': parent}, ('WHCode',), ('WHCode',), outer=True):
                    values = dict(row, SKUName=_without_commas(row['SKUName']),
                        WhName=_without_commas(row['WhName']), ParentWhCode=parent,
                        ParentWhName=_without_commas(None if site is None else site['WHDescription']),
                        Req=_coalesce(supplier, 'OriginalReq', row['Req']),
                        RationedReq=_coalesce(supplier, 'DispatchReq', row['RationedReq']))
                    # Unqualified SELECT names resolve to B: these fields do
                    # not exist on A.vf_RationedReqReport. Missing LEFT JOIN B
                    # means NULL bands, not rationed data or numeric defaults.
                    values.update({field: None if supplier is None else supplier[field]
                                   for field in SUPPLIER_BANDS})
                    core = tuple(values[field] for field in TOTAL_CORE)
                    for pair, sku, location in product(*attrs):
                        yield core + tuple(record[field] for record in (pair, sku, location)
                                           for field in ATTRIBUTES)
    return records()
