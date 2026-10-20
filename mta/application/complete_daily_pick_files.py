"""Pure projections of the four canonical required Pick batch reports.

Inputs are explicit native table images from this engine's own Pick producer,
never presentation reports or copied native answers. No allocation is computed
here. SQL has no ORDER BY: encounter order is retained for diagnostics only;
native qualification must compare typed relational bags, not invent a sort.
"""
from decimal import Decimal, localcontext

from mta.domain.complete_daily_scalars import ascii_equal

SOURCES = {
    'logistic': ('Scripts/BPR/PickList_Reports/GenerateLogisticPickListReport.sql',
                 '0355da5c9b767d2a90bdc08a39845b0fb0d99577a573b9efb95afed4c743eb6c'),
    'remaining_summary': ('Scripts/BPR/PickList_Reports/GenerateRemainingQtySummaryReport.sql',
                          '0f5a45ba41a21f8f8a7aa00a7904d849a0b5cf1a2850a2d61116f0afbde8bd87'),
    'remaining_details': ('Scripts/BPR/PickList_Reports/GenerateRemainingQtyDetailsReport.sql',
                          'b6847f5d623f1306b00ee0a4ead0a6f213d7a040f9b27f693ef2734737744ed1'),
    'transport_summary': ('Scripts/BPR/PickList_Reports/GenerateTransportReqSummaryRpt.sql',
                          'fce7e6686d7271c8f0075dd367a8a3bf58691617213ed253049f39f626311a11'),
}

LOGISTIC_FIELDS = ('ParentWHCode', 'WHCode', 'LogisticLocation', 'TruckCount',
                   'VehicleName', 'TransportLoadType', 'DispatchColor', 'SKUCode')
LOGISTIC_GROUP = ('ParentWHCode', 'WHCode', 'LogisticLocation', 'SKUCode', 'TruckCount')
DETAIL_FIELDS = ('ParentWHCode', 'WHCode', 'LogisticLocation', 'DispatchColor', 'SKUCode')
DETAIL_GROUP = ('ParentWHCode', 'WHCode', 'LogisticLocation', 'SKUCode')
SUMMARY_GROUP = ('ParentWHCode', 'LogisticLocation')
TRANSPORT_GROUP = ('ParentWHCode', 'LogisticLocation', 'VehicleName', 'TransportLoadType')
LOGISTIC_OUTPUT = ('ParentWHCode', 'WHCode', 'LogisticLocation', 'Vehicle Counter',
    'VehicleName', 'TransportLoadType', 'DispatchColor', 'SKUCode', 'SumOfPikedQty', 'TotalWeight', 'TotalVolume')
DETAIL_OUTPUT = DETAIL_FIELDS + ('Qty', 'RemainingTotalWeight', 'RemainingTotalVol')

# Complete native images are produced by complete_daily_pick.calculate_native_pick
# and bound to typed closing state by the explicit complete_pick daily policy.
# Compatibility receipt field retained; supported-domain limits are documented
# separately and are not missing materializers or fabricated input defaults.
MISSING_INPUT_MATERIALIZERS = {}


class UnqualifiedPickFileInput(ValueError):
    """Explicit native domain needing proof; never a silently changed value."""


def _key(row, fields):
    result = []
    for field in fields:
        value = row[field]
        if value is None:
            result.append(None)  # SQL GROUP/DISTINCT group NULLs together.
        elif field == 'TruckCount':
            _integer(value)
            result.append(value)
        else:
            ascii_equal(value, value)  # qualified CI ASCII/trailing-space domain
            result.append(value.rstrip(' ').upper())
    return tuple(result)


def _groups(rows, fields):
    groups, representatives = {}, {}
    for row in rows:
        key = _key(row, fields)
        spelling = tuple(row[field] for field in fields)
        if key in representatives and representatives[key] != spelling:
            # SQL does not specify which byte spelling a CI GROUP/DISTINCT
            # retains. Fail visibly rather than invent a representative.
            raise UnqualifiedPickFileInput('Ambiguous native CI group spelling; native representative proof required')
        representatives[key] = spelling
        groups.setdefault(key, []).append(row)
    return groups


def _integer(value):
    if type(value) is not int or not -2**31 <= value < 2**31:
        raise UnqualifiedPickFileInput('Exact native SQL int required')
    return value


def _sum_int(rows, field, *, isnull):
    values = [_integer(row[field]) for row in rows if row[field] is not None]
    if not values and not isnull:
        return None
    total = sum(values)
    if not -2**31 <= total < 2**31:
        raise UnqualifiedPickFileInput('Native ANSI_WARNINGS OFF integer overflow requires separate proof')
    return total


def _sum_decimal(rows, field, *, precision):
    with localcontext() as context:
        context.prec = 50
        total = Decimal('0.000')
        for row in rows:
            value = row[field]
            if value is None:
                continue  # SUM(ISNULL(native decimal(13,3),0))
            if (not isinstance(value, Decimal) or not value.is_finite()
                    or value.as_tuple().exponent != -3 or abs(value) >= Decimal(10)**10):
                raise UnqualifiedPickFileInput('Exact finite native decimal(13,3) input required')
            total += value
        if abs(total) >= Decimal(10)**(precision - 3):
            raise UnqualifiedPickFileInput('Native decimal assignment overflow requires separate proof')
        return total.quantize(Decimal('0.001'))


def _result(kind, header, fields, types, rows, transient=None):
    path, pin = SOURCES[kind]
    marked = kind in ('logistic', 'remaining_details')
    return dict(canonical_source=path, source_sha256=pin,
        script_marker=path.rsplit('/', 1)[1] if marked else None,
        scratch_truncate_before=marked, scratch_truncate_after=marked,
        order_policy='SQL has no ORDER BY; encounter sequence diagnostic only; typed bag qualification',
        resultsets=[dict(fields=('',) * len(header), rows=[tuple(header)],
                        types=tuple('varchar(' + str(len(value)) + ')' for value in header)),
                    dict(fields=tuple(fields), rows=rows, types=tuple(types))],
        transient_rows=transient or [])


def logistic_pick_list_report(logistic_pick_list):
    """DISTINCT8 rows receive GROUP5 totals; NULL UPDATE keys stay NULL."""
    grouped = _groups(logistic_pick_list, LOGISTIC_GROUP)
    distinct = _groups(logistic_pick_list, LOGISTIC_FIELDS)
    rows, transient = [], []
    for sources in distinct.values():
        source = sources[0]
        key = _key(source, LOGISTIC_GROUP)
        qty = weight = volume = None
        if all(value is not None for value in key):
            group = grouped[key]
            qty = _sum_int(group, 'ColorWiseAlloction', isnull=True)
            weight = _sum_decimal(group, 'TotalWeight', precision=13)
            volume = _sum_decimal(group, 'TotalVolume', precision=13)
        values = tuple(source[field] for field in LOGISTIC_FIELDS) + (qty, weight, volume)
        rows.append(values)
        transient.append(dict(zip(LOGISTIC_OUTPUT, values)))
    return _result('logistic',
        ('From Location', 'To Location', 'Logistic Location', 'Vehicle Counter', 'Vehicle Name',
         'Transport Load Type', 'Dispatch Color', 'SKUCode', 'Sum of Picked Qty', 'Total Weight', 'Total Volume'),
        LOGISTIC_OUTPUT, ('nvarchar(50)',) * 3 + ('int', 'nvarchar(50)', 'nvarchar(20)',
            'nvarchar(20)', 'nvarchar(50)', 'int', 'decimal(13,3)', 'decimal(13,3)'), rows, transient)


def remaining_quantity_summary_report(pick_list_data_for_truck_formation):
    rows = []
    for group in _groups(pick_list_data_for_truck_formation, SUMMARY_GROUP).values():
        source = group[0]
        rows.append(tuple(source[field] for field in SUMMARY_GROUP) +
            (_sum_decimal(group, 'TotalWeight', precision=38),
             _sum_decimal(group, 'TotalVolume', precision=38)))
    return _result('remaining_summary',
        ('From Location', 'Logistic Location', 'Total Remaining Weight', 'Total Remaining Volume'),
        SUMMARY_GROUP + ('TotalRemWeight', 'TotalRemVolume'),
        ('nvarchar(50)', 'nvarchar(50)', 'decimal(38,3)', 'decimal(38,3)'), rows)


def remaining_quantity_details_report(pick_list_data_for_truck_formation):
    grouped = _groups(pick_list_data_for_truck_formation, DETAIL_GROUP)
    distinct = _groups(pick_list_data_for_truck_formation, DETAIL_FIELDS)
    rows, transient = [], []
    for sources in distinct.values():
        source = sources[0]
        key = _key(source, DETAIL_GROUP)
        qty = weight = volume = None
        if all(value is not None for value in key):
            group = grouped[key]
            qty = _sum_int(group, 'ColorWiseAlloction', isnull=False)
            weight = _sum_decimal(group, 'TotalWeight', precision=13)
            volume = _sum_decimal(group, 'TotalVolume', precision=13)
        values = tuple(source[field] for field in DETAIL_FIELDS) + (qty, weight, volume)
        rows.append(values)
        transient.append(dict(zip(DETAIL_OUTPUT, values)))
    return _result('remaining_details',
        ('From Location', 'To Location', 'Logistic Location', 'Dispatch Color', 'SKU Code', 'Qty',
         'Total Remaining Weight', 'Total Remaining Volume'), DETAIL_OUTPUT,
        ('nvarchar(50)',) * 3 + ('nvarchar(20)', 'nvarchar(50)', 'int', 'decimal(13,3)', 'decimal(13,3)'), rows, transient)


def transport_requirement_summary_report(logistic_pick_list):
    rows = []
    for group in _groups(logistic_pick_list, TRANSPORT_GROUP).values():
        for source in group:
            if source['IsTruckFormed'] is not None and type(source['IsTruckFormed']) is not bool:
                raise UnqualifiedPickFileInput('Exact native IsTruckFormed bit required')
        count = _integer(sum(row['IsTruckFormed'] is not None for row in group))
        rows.append(tuple(group[0][field] for field in TRANSPORT_GROUP) + (count,))
    return _result('transport_summary',
        ('From Location', 'Logistic Location', 'Vehicle Name', 'Transport Load Type', 'Sum of Transport Required'),
        TRANSPORT_GROUP + ('',), ('nvarchar(50)', 'nvarchar(50)', 'nvarchar(50)', 'nvarchar(20)', 'int'), rows)


def project_reports(*, logistic_pick_list, pick_list_data_for_truck_formation):
    """Require both explicit own stage populations; absent is never empty."""
    if not isinstance(logistic_pick_list, (list, tuple)) or not isinstance(pick_list_data_for_truck_formation, (list, tuple)):
        raise ValueError('Explicit native Pick stage table populations required')
    reports = dict(logistic=logistic_pick_list_report(logistic_pick_list),
        remaining_summary=remaining_quantity_summary_report(pick_list_data_for_truck_formation),
        remaining_details=remaining_quantity_details_report(pick_list_data_for_truck_formation),
        transport_summary=transport_requirement_summary_report(logistic_pick_list))
    # Producer-owned, typed markers survive storage/readback. Do not infer a
    # historical weight-only decision merely from a missing product dimension.
    fields = ('ParentWHCode', 'LogisticLocation')
    unverified = {_key(row, fields) for row in logistic_pick_list
                  if row['TransportLoadType'] == 'WEIGHT_ONLY'}
    unverified.update(_key(row, fields) for row in pick_list_data_for_truck_formation
                      if row.get('RemainingVolume', 0) is None)
    if unverified:
        for report in reports.values():
            header, body = report['resultsets']
            indexes = [body['fields'].index(field) for field in fields]
            volume_index = next((i for i, field in enumerate(body['fields'])
                                 if field in ('TotalVolume', 'TotalRemVolume', 'RemainingTotalVol')), None)
            flagged = []
            for values in body['rows']:
                key = _key(dict(zip(fields, (values[i] for i in indexes))), fields)
                warning = 'WEIGHT_ONLY: VOLUME UNVERIFIED; CHECK LOAD SPACE' if key in unverified else ''
                values = list(values)
                if warning and volume_index is not None:
                    # A known partial SUM must not look like a verified total.
                    values[volume_index] = None
                flagged.append(tuple(values) + (warning,))
            header['fields'] += ('',)
            header['types'] += ('varchar(19)',)
            header['rows'] = [tuple(header['rows'][0]) + ('Capacity Validation',)]
            body['fields'] += ('CapacityValidation',)
            body['types'] += ('varchar(64)',)
            body['rows'] = flagged
            report['capacity_policy'] = 'missing-volume-weight-only-v1'
            for row, values in zip(report['transient_rows'], flagged):
                row.update(zip(body['fields'], values))
    return reports
