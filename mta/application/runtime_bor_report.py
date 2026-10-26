"""Pure projection of three exact retained RuntimeReports SQL definitions.

This is a data-resultset contract, not SQLCMD metadata/file qualification or a
production default. Inputs are explicit typed source projections (extra source
columns are permitted). No calculated state is read or changed here.
"""
from collections.abc import Mapping
from decimal import Decimal
import hashlib
from itertools import product
import math

from mta.application.row_bag_lookup import AsciiBagLookup
from mta.domain.complete_daily_scalars import ascii_equal
from mta.row_sequences import is_record_rows

SOURCE_FIXTURE = 'tests/fixtures/runtime_reports_retained_20261019.json'
SOURCE_FIXTURE_SHA256 = '1f036745abadf0224d9778a8fabf3cc93ad632d106a61127973f08b2baa9af55'
# Captured row Id is provenance only: a deployment may assign another Id.
QUERY_PINS = {
    'ce590b309a1e70a61794ba2265acfcaabd4db939b198493fe11bef9d3ed9772a': (4, None),
    '5af4d6679f70d30f3cee753b7322c23c393ec278f70418add4eb3335e0071fe4': (5, 'P041'),
    '395aba037b9713b0b0c10101b6a507fc227073af34187dbe4601683b4763b780': (6, 'P001'),
}
QUANTITIES = ('Norm', 'Stock', 'VirtualNorm', 'GIT', 'ParentLeftoverStock',
              'Requirement', 'Req_TOB', 'Req_TOR', 'Req_TOY', 'Req_TOG',
              'Req_TOBlue', 'DispatchQty', 'Dispatch_TOB', 'Dispatch_TOR',
              'Dispatch_TOY', 'Dispatch_TOG', 'Dispatch_ToBlue')
DESCENDING = ('OrderBlackUnsatisfiedPercentage', 'OrderRedUnsatisfiedPercentage',
              'OrderYellowUnsatisfiedPercentage', 'OrderGreenUnsatisfiedPercentage', 'DispatchPen')
# Positional expression labels, not invented native resultset column names.
COLUMNS = ('A.SKUCode', 'quoted(S1.SKUDescription)', 'A.WhCode',
           'quoted(S2.WHDescription)', 'A.SupplierCode', 'quoted(S3.WHDescription)',
           *QUANTITIES, 'A.DispatchColor', "ISNULL(D.c9,'-')", "ISNULL(D.c10,'-')",
           "ISNULL(D.c12,'-')", "ISNULL(D.c13,'-')", 'E.c3', 'D.c11', 'D.c7')
TIE_POLICY = ('Native ORDER BY has no tie-break. Unresolved ties retain supplied '
              'BOR, ColorSequence, S1, S2, S3, D, E occurrence order; exact native '
              'tie order remains unqualified.')


def query_pin(report_definition):
    """Identify exact captured SQL without interpreting SQL or deployment Id."""
    query = report_definition.get('Query') if isinstance(report_definition, Mapping) else None
    if type(query) is not str:
        raise ValueError('Explicit retained RuntimeReports Query required')
    sha = hashlib.sha256(query.encode('utf-8')).hexdigest()
    if sha not in QUERY_PINS:
        raise ValueError('Unsupported retained BOR RuntimeReports Query')
    source_id, site = QUERY_PINS[sha]
    return dict(query_sha256=sha, source_id=source_id, site_filter=site,
                source_fixture=SOURCE_FIXTURE, source_fixture_sha256=SOURCE_FIXTURE_SHA256)


def _rows(name, rows, texts, integers=(), numbers=(), keys=()):
    if not is_record_rows(rows):
        raise ValueError('Explicit typed source population required: ' + name)
    fields = set(texts) | set(integers) | set(numbers)
    for row in rows:
        if not isinstance(row, Mapping) or not fields <= row.keys():
            raise ValueError('Required source columns missing: ' + name)
        for field in texts:
            value = row[field]
            if value is not None and type(value) is not str:
                raise ValueError('Typed SQL text required: ' + name + '.' + field)
            if field in keys and value is not None and not value.isascii():
                raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: ASCII SQL text equality')
        for field in integers:
            value = row[field]
            if value is not None and (type(value) is not int or not -2**31 <= value < 2**31):
                raise ValueError('Typed SQL int required: ' + name + '.' + field)
        for field in numbers:
            value = row[field]
            if value is not None and (type(value) not in (int, float, Decimal)
                    or (isinstance(value, Decimal) and not value.is_finite())
                    or (type(value) is float and not math.isfinite(value))):
                raise ValueError('Typed finite SQL number required: ' + name + '.' + field)


def _matches(lookup, source, left, right, *, outer=True):
    matches = [row for row in lookup.candidates(source, left)
               if all(ascii_equal(source[a], row[b]) for a, b in zip(left, right))]
    return matches or ([None] if outer else [])


def _cell(row, field):
    return None if row is None else row[field]


def _quoted(value):
    return None if value is None else '"' + value + '"'


def project(report_definition, *, bor_with_order_allocation, color_sequence,
            sku_descriptions, site_descriptions, sku_loc_attributes, sku_attributes):
    """Return ordered 31-cell tuples, preserving every joined occurrence.

    NULL is distinct from an absent column/population. Numeric values remain
    typed and unconverted. Text equality uses the existing bounded ASCII CI,
    space-padded adapter; Unicode join keys fail explicitly. Description/attribute
    values need no collation comparison and retain their Unicode and punctuation.
    """
    pin = query_pin(report_definition)
    _rows('BORWithOrderAllocation', bor_with_order_allocation,
          ('SKUCode', 'WhCode', 'SupplierCode', 'DispatchColor'), QUANTITIES, DESCENDING,
          keys=('SKUCode', 'WhCode', 'SupplierCode', 'DispatchColor'))
    _rows('ColorSequence', color_sequence, ('Color',), ('SequenceNo',), keys=('Color',))
    _rows('SKUDescriptionTbl', sku_descriptions, ('SKUCode', 'SKUDescription'), keys=('SKUCode',))
    _rows('SiteDescriptionTbl', site_descriptions, ('WHCode', 'WHDescription'), keys=('WHCode',))
    _rows('SkuLocAttributeData', sku_loc_attributes,
          ('SKUCode', 'LocCode', 'c9', 'c10', 'c12', 'c13', 'c11', 'c7'), keys=('SKUCode', 'LocCode'))
    _rows('SkuAttributeData', sku_attributes, ('SKUCode', 'c3'), keys=('SKUCode',))
    colours = AsciiBagLookup(color_sequence, ('Color',), ascii_equal)
    skus = AsciiBagLookup(sku_descriptions, ('SKUCode',), ascii_equal)
    sites = AsciiBagLookup(site_descriptions, ('WHCode',), ascii_equal)
    pairs = AsciiBagLookup(sku_loc_attributes, ('SKUCode', 'LocCode'), ascii_equal)
    attrs = AsciiBagLookup(sku_attributes, ('SKUCode',), ascii_equal)
    expanded = []
    for bor in bor_with_order_allocation:
        if pin['site_filter'] is not None and not ascii_equal(bor['WhCode'], pin['site_filter']):
            continue
        bags = (
            _matches(colours, bor, ('DispatchColor',), ('Color',), outer=False),
            _matches(skus, bor, ('SKUCode',), ('SKUCode',)),
            _matches(sites, bor, ('WhCode',), ('WHCode',)),
            _matches(sites, bor, ('SupplierCode',), ('WHCode',)),
            _matches(pairs, bor, ('SKUCode', 'WhCode'), ('SKUCode', 'LocCode')),
            _matches(attrs, bor, ('SKUCode',), ('SKUCode',)),
        )
        for colour, sku, site, supplier, pair, attr in product(*bags):
            sequence = colour['SequenceNo']
            # SQL Server: NULL first ASC, last DESC. Stable sort adds no key.
            key = ((sequence is not None, sequence if sequence is not None else 0),
                   *((bor[f] is None, -bor[f] if bor[f] is not None else 0) for f in DESCENDING))
            values = (bor['SKUCode'], _quoted(_cell(sku, 'SKUDescription')),
                      bor['WhCode'], _quoted(_cell(site, 'WHDescription')),
                      bor['SupplierCode'], _quoted(_cell(supplier, 'WHDescription')),
                      *(bor[f] for f in QUANTITIES), bor['DispatchColor'],
                      *('-' if _cell(pair, f) is None else pair[f] for f in ('c9', 'c10', 'c12', 'c13')),
                      _cell(attr, 'c3'), _cell(pair, 'c11'), _cell(pair, 'c7'))
            expanded.append((key, values))
    expanded.sort(key=lambda item: item[0])
    return [values for _, values in expanded]
