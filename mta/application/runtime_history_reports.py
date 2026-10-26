"""Exact retained efficiency/allocation-history query projections, no execution.

Unordered results retain supplied join occurrence order; SQL specifies no output
order. No SQLCMD column metadata, file parity or production applicability claim.
"""
from datetime import date, datetime, timedelta
import hashlib
from itertools import product

from mta.application.row_bag_lookup import AsciiBagLookup
from mta.application.runtime_bor_report import (
    SOURCE_FIXTURE, SOURCE_FIXTURE_SHA256, QUANTITIES, _rows, _matches, _cell)
from mta.domain.complete_daily_scalars import ascii_equal

QUERY_PINS = {
    'aec9887abcad134870a26a9ece9ccef8f20f8ed2c1095424844006d8e1b0246d': 2,
    '76f20aba949486a13a08684c810b76df84b69a529a119e6168f5d5c371144351': 3,
    '589872d44d3f0f09a5d87421130e46797bbab6598046ebf544642e4bed3a76a8': 8,
}
SCHEMA_PINS = {
    'Scripts/DBCreation/BTR_DBCreation.sql': '2d8a4b4091943ca67489789d60f964da0adbc80ec5b285c05fef9c0ed03ae16d',
    'Scripts/DBCreation/BPR_DBCreation.sql': 'a906c4b7ea50cb4a121101159553c2d531a29fe5c782247318fc0f933efe6ec0',
}
# BTR DDL RationingHistory.ParentNorm is int NULL: int precedence converts ''
# to 0 in NULLIF. The four unqualified bands resolve to C=vf_PickListReport:
# only its BPR DDL declares them; RationingHistory does not contain those names.
EFFICIENCY_COLUMNS = ('ParentWhCode', 'ParentWhName', 'SKUCode', 'SKUName', 'WhCode',
    'WhName', 'IsNormed', 'Req', 'c9', 'c10', 'c12', 'c13', 'DispatchAdviceQuantity',
    'DispatchPen', 'DispatchColor', 'Dispatch', 'ReportDate', 'BOR/RRR',
    'E.Stock', 'E.GIT', 'C.TOR_B', 'C.TOR_R', 'C.TOY', 'C.TOG')
ALLOCATION_COLUMNS = ('SKUCode', 'SKUDescription', 'WhCode', 'LocDesciption',
    'SupplierCode', 'SupplierDescription', *QUANTITIES, 'DispatchColor', 'B.AdvAllocDone',
    'D.c9', 'D.c10', 'F.Remark', 'D.c7', 'D.c11', 'D.c12', 'D.c13', 'E.c3', 'A.ReportDate')
ORDER_POLICY = 'No native output ORDER BY; retain supplied source/join occurrence order, unqualified natively.'


class AmbiguousLatestRemark(ValueError):
    """ROW_NUMBER's tied candidates can produce different projected cells."""


def query_pin(definition):
    query = definition.get('Query') if isinstance(definition, dict) else None
    if type(query) is not str:
        raise ValueError('Explicit retained history Query required')
    sha = hashlib.sha256(query.encode()).hexdigest()
    if sha not in QUERY_PINS:
        raise ValueError('Unsupported retained history Query')
    return dict(query_sha256=sha, source_id=QUERY_PINS[sha], source_fixture=SOURCE_FIXTURE,
                source_fixture_sha256=SOURCE_FIXTURE_SHA256, schema_pins=dict(SCHEMA_PINS))


def _dates(rows, field, kind=date, *, nullable=True):
    for row in rows:
        if field not in row or (row[field] is None and not nullable):
            raise ValueError('Required typed source date: ' + field)
        value = row[field]
        if value is not None and (type(value) is not kind or
                (kind is datetime and value.tzinfo is not None)):
            raise ValueError('Typed native date/datetime required: ' + field)


def _today(value):
    if value is not None and type(value) is not date:
        raise ValueError('Typed LastBatchRunTbl date required')


def _replace(value, replacement=''):
    return None if value is None else value.replace(',', replacement)


def efficiency(definition, *, today, rationing_history, sku_loc_attributes, pick_report):
    """Queries 2/3. The lower bound is strict and there is NO upper bound."""
    source_id = query_pin(definition)['source_id']
    if source_id not in (2, 3):
        raise ValueError('Efficiency query required')
    _today(today)
    texts = ('ParentWhCode', 'ParentWhName', 'SKUCode', 'SKUName', 'WhCode', 'WhName', 'DispatchColor')
    _rows('RationingHistory', rationing_history, texts,
          ('ParentNorm', 'Req', 'RationedReq', 'SupplierDispatchReq', 'Dispatch', 'Stock', 'GIT'),
          ('DispatchPen',), keys=('ParentWhCode', 'SKUCode', 'WhCode'))
    _dates(rationing_history, 'ReportDate')
    for row in rationing_history:
        if 'IsNormed' not in row or type(row['IsNormed']) not in (bool, int) or row['IsNormed'] not in (0, 1):
            raise ValueError('Typed IsNormed bit required')
    _rows('SkuLocAttributeData', sku_loc_attributes,
          ('SKUCode', 'LocCode', 'c9', 'c10', 'c12', 'c13'), keys=('SKUCode', 'LocCode'))
    _rows('vf_PickListReport', pick_report, ('SKUCode', 'WhCode', 'ParentWhCode'),
          ('TOR_B', 'TOR_R', 'TOY', 'TOG'), keys=('SKUCode', 'WhCode', 'ParentWhCode'))
    attrs = AsciiBagLookup(sku_loc_attributes, ('SKUCode', 'LocCode'), ascii_equal)
    picks = AsciiBagLookup(pick_report, ('SKUCode', 'WhCode', 'ParentWhCode'), ascii_equal)
    stocks = AsciiBagLookup([row for row in rationing_history if today is not None and row['ReportDate'] == today],
                            ('SKUCode', 'WhCode'), ascii_equal)
    result = []
    for row in rationing_history:
        if today is None or row['ReportDate'] is None or row['ReportDate'] <= today - timedelta(days=45):
            continue
        rrr = row['ParentNorm'] is not None and row['ParentNorm'] != 0
        if rrr != (source_id == 3):
            continue
        for attr, pick, stock in product(
                _matches(attrs, row, ('SKUCode', 'WhCode'), ('SKUCode', 'LocCode')),
                _matches(picks, row, ('SKUCode', 'WhCode', 'ParentWhCode'), ('SKUCode', 'WhCode', 'ParentWhCode')),
                _matches(stocks, row, ('SKUCode', 'WhCode'), ('SKUCode', 'WhCode'))):
            result.append((row['ParentWhCode'], _replace(row['ParentWhName']), row['SKUCode'],
                _replace(row['SKUName']), row['WhCode'], _replace(row['WhName']), row['IsNormed'], row['Req'],
                *(_replace('-' if _cell(attr, field) is None else attr[field]) for field in ('c9', 'c10', 'c12', 'c13')),
                row['RationedReq'] if rrr else row['SupplierDispatchReq'], row['DispatchPen'], row['DispatchColor'],
                row['Dispatch'], row['ReportDate'], 'RRR' if rrr else 'BOR', _cell(stock, 'Stock'), _cell(stock, 'GIT'),
                *(_cell(pick, field) for field in ('TOR_B', 'TOR_R', 'TOY', 'TOG'))))
    return result


def _sql_key(row, fields):
    # All key scalars have already passed the shared ASCII-domain guard.
    return tuple(None if row[field] is None else row[field].rstrip(' ').upper() for field in fields)


def _latest_remark_bags(remarks):
    """One linear pass retains every occurrence tied for each pair's maximum.

    Canonical BORReport_OARemarkDetails.RemarkDate is datetime NOT NULL (BPR
    DDL line1934). No NULL-date sorting/default is needed or admitted. NULL pair
    keys cannot join a report row and can be excluded from this lookup.
    """
    bags = {}
    for row in remarks:
        key = _sql_key(row, ('SKUCode', 'WhCode'))
        if None in key:
            continue
        prior = bags.get(key)
        if prior is None or row['RemarkDate'] > prior[0]['RemarkDate']:
            bags[key] = [row]
        elif row['RemarkDate'] == prior[0]['RemarkDate']:
            prior.append(row)
    return AsciiBagLookup([row for bag in bags.values() for row in bag],
                          ('SKUCode', 'WhCode'), ascii_equal)


def _remark_for(row, lookup):
    candidates = _matches(lookup, row, ('SKUCode', 'WhCode'), ('SKUCode', 'WhCode'), outer=False)
    if not candidates:
        return None
    # ROW_NUMBER partitions only by pair. A newer OTHER supplier hides this
    # supplier's older remark; adding SupplierCode to the partition is wrong.
    values = {candidate['Remark'] if ascii_equal(row['SupplierCode'], candidate['SupplierCode']) else None
              for candidate in candidates}
    if len(values) != 1:
        raise AmbiguousLatestRemark('Equal latest RemarkDate has distinguishable supplier/remark projections')
    return next(iter(values))


def allocation_history(definition, *, today, bor_history, color_sequence, sku_descriptions,
                       site_descriptions, requirements, sku_loc_attributes, sku_attributes, remarks):
    """Query 8. Inclusive 44-day window; tied latest remarks must be equivalent."""
    if query_pin(definition)['source_id'] != 8:
        raise ValueError('Allocation history query required')
    _today(today)
    _rows('BOR_OrderAllocationHistory', bor_history, ('SKUCode', 'WhCode', 'SupplierCode', 'DispatchColor'),
          QUANTITIES, keys=('SKUCode', 'WhCode', 'SupplierCode', 'DispatchColor'))
    _dates(bor_history, 'ReportDate')
    _rows('ColorSequence', color_sequence, ('Color',), ('SequenceNo',), keys=('Color',))
    _rows('SKUDescriptionTbl', sku_descriptions, ('SKUCode', 'SKUDescription'), keys=('SKUCode',))
    _rows('SiteDescriptionTbl', site_descriptions, ('WHCode', 'WHDescription'), keys=('WHCode',))
    _rows('vf_ReqCalculation', requirements, ('SKUCode', 'WhCode'), ('AdvAllocDone',), keys=('SKUCode', 'WhCode'))
    _rows('SkuLocAttributeData', sku_loc_attributes,
          ('SKUCode', 'LocCode', 'c9', 'c10', 'c7', 'c11', 'c12', 'c13'), keys=('SKUCode', 'LocCode'))
    _rows('SkuAttributeData', sku_attributes, ('SKUCode', 'c3'), keys=('SKUCode',))
    _rows('BORReport_OARemarkDetails', remarks, ('SKUCode', 'WhCode', 'SupplierCode', 'Remark'),
          keys=('SKUCode', 'WhCode', 'SupplierCode'))
    _dates(remarks, 'RemarkDate', datetime, nullable=False)
    indexes = [AsciiBagLookup(rows, fields, ascii_equal) for rows, fields in (
        (color_sequence, ('Color',)), (sku_descriptions, ('SKUCode',)),
        (site_descriptions, ('WHCode',)), (requirements, ('SKUCode', 'WhCode')),
        (sku_loc_attributes, ('SKUCode', 'LocCode')), (sku_attributes, ('SKUCode',)))]
    colours, skus, sites, reqs, pairs, attrs = indexes
    remark_lookup = _latest_remark_bags(remarks)
    remark_cache = {}
    result = []
    for row in bor_history:
        if today is None or row['ReportDate'] is None or not today - timedelta(days=44) <= row['ReportDate'] <= today:
            continue
        bags = (_matches(colours, row, ('DispatchColor',), ('Color',), outer=False),
                _matches(skus, row, ('SKUCode',), ('SKUCode',)),
                _matches(sites, row, ('WhCode',), ('WHCode',)),
                _matches(sites, row, ('SupplierCode',), ('WHCode',)),
                _matches(reqs, row, ('SKUCode', 'WhCode'), ('SKUCode', 'WhCode')),
                _matches(pairs, row, ('SKUCode', 'WhCode'), ('SKUCode', 'LocCode')),
                _matches(attrs, row, ('SKUCode',), ('SKUCode',)))
        if not bags[0]:
            continue
        remark_key = _sql_key(row, ('SKUCode', 'WhCode', 'SupplierCode'))
        if remark_key not in remark_cache:
            remark_cache[remark_key] = _remark_for(row, remark_lookup)
        remark = remark_cache[remark_key]
        for _colour, sku, site, supplier, req, pair, attr in product(*bags):
            result.append((row['SKUCode'], _replace(_cell(sku, 'SKUDescription'), ' '),
                row['WhCode'], _replace(_cell(site, 'WHDescription'), ' '), row['SupplierCode'],
                _replace(_cell(supplier, 'WHDescription'), ' '), *(row[f] for f in QUANTITIES),
                row['DispatchColor'], _cell(req, 'AdvAllocDone'), _cell(pair, 'c9'), _cell(pair, 'c10'),
                remark, *(_cell(pair, f) for f in ('c7', 'c11', 'c12', 'c13')), _cell(attr, 'c3'), row['ReportDate']))
    return result
