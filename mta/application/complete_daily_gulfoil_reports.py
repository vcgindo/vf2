"""Pure retained GulfOil BTR file transformation, before owned file writing.

Input is the exact ordered joined SELECT population, not a prepared UI grid.
The host date is explicit and MUST NOT be replaced with the business date.
No row deduplication or tie-break is added: native idxmax/first retain the first
occurrence in an already ReportDate-ordered source. SQL joins and diagnostic
queries/file side effects require their own qualified caller.
"""
import csv
from datetime import date, datetime
from io import StringIO

SOURCE = ('Scripts/SiteSpecific/GulfOil/BTR/GulfOil_BTRReports.py',
          '9492cb85d618ae373cf84442e12fcc8c6c90dad7b8544b03aa45b4c4996e6096')
PIVOTS = dict(BTR_Tech='TechColor', BTR_Eco='EcoColor',
              BTR_OnHand='PhysicalInventoryColor', BTR_Pipeline='DispatchColor')
IDENTIFIERS = ('SKUCode', 'WHCode')
STATIC = ('SKUCode', 'WHCode', 'WhName', 'ParentWhCode', 'ParentWhName',
          'Norm', 'SL1', 'SL2', 'SL3', 'LL1', 'LL2', 'LL3', 'RLT', 'ABCxFMS')
DAYS = tuple('D' + str(i) for i in range(1, 91))
COLORS = ('White', 'Blue', 'Green', 'Yellow', 'Red', 'Black', 'Grey')
TARGET = ('21104027051000', 'P023_1002')


def joined_rows(*, bpr_history, site_descriptions, sku_attributes,
                location_attributes, importer_master, sku_loc_attributes,
                report_type, equal):
    """The canonical six INNER JOINs, preserving every join occurrence.

    Each population must be supplied by its actual BTR/Importer owner. The
    native SELECT orders by ReportDate only; input occurrence order is retained
    inside equal-date groups and is never presented as a SQL tie-break proof.
    """
    if report_type not in PIVOTS:
        raise ValueError('Unsupported GulfOil BTR report')

    def matches(rows, fields, values):
        return [row for row in rows if all(row[field] is not None and value is not None
                and equal(row[field], value) for field, value in zip(fields, values))]

    output = []
    for history in bpr_history:
        sku, wh, parent = history['SKUCode'], history['WHCode'], history['ParentWhCode']
        for receiving in matches(site_descriptions, ('WHCode',), (wh,)):
            for supplying in matches(site_descriptions, ('WHCode',), (parent,)):
                for skumeta in matches(sku_attributes, ('SKUCode',), (sku,)):
                    for location in matches(location_attributes, ('WHCode',), (wh,)):
                        for master in matches(importer_master, ('SKUCode', 'WhCode'), (sku, wh)):
                            for attr in matches(sku_loc_attributes, ('SKUCode', 'LocCode'), (sku, wh)):
                                row = {key: history[key] for key in
                                       ('SKUCode', 'WHCode', 'ParentWhCode', 'Norm',
                                        *PIVOTS.values(), 'ReportDate')}
                                row.update(WhName=receiving['WHDescription'],
                                           ParentWhName=supplying['WHDescription'],
                                           RLT=master['RLT'], ABCxFMS=attr['c11'])
                                row.update({key: skumeta[key] for key in ('SL1', 'SL2', 'SL3')})
                                row.update({key: location[key] for key in ('LL1', 'LL2', 'LL3')})
                                if report_type in ('BTR_OnHand', 'BTR_Pipeline'):
                                    row['VirtualNorm'] = history['VirtualNorm']
                                output.append(row)
    return sorted(output, key=lambda row: _date(row['ReportDate']))


def _date(value):
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            raise ValueError('Native report dates are timezone-naive')
        return value.date()
    if type(value) is date:
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    raise ValueError('Native non-NULL ReportDate required')


def transform(joined_rows, report_type, *, host_today):
    """Return ordered report rows, or absence while preserving an existing ZIP.

    Static fields use the latest row per pair, first among exact date ties.
    Pivot first skips NULL colors. Grey is applied before pivot, Age counts gaps
    backwards from D90, and color counts include only D61–D90. This is the
    declared native int/text population; arbitrary pandas object inference is
    not silently approximated.
    """
    if report_type not in PIVOTS:
        raise ValueError('Unsupported GulfOil BTR report')
    today = _date(host_today)
    virtual = report_type in ('BTR_OnHand', 'BTR_Pipeline')
    fields = set(STATIC) | set(PIVOTS.values()) | {'ReportDate'}
    if virtual:
        fields.add('VirtualNorm')
    rows = list(joined_rows)
    previous = None
    for row in rows:
        if set(row) != fields:
            raise ValueError('Exact canonical GulfOil SELECT column roster required')
        if any(not isinstance(row[k], str) for k in IDENTIFIERS):
            raise ValueError('Native non-NULL SKU/location identifiers required')
        if type(row['Norm']) is not int or type(row['RLT']) is not int:
            raise ValueError('Native non-NULL int Norm/RLT required')
        if virtual and row['VirtualNorm'] is not None and type(row['VirtualNorm']) is not int:
            raise ValueError('Native nullable int VirtualNorm required')
        if any(row[k] is not None and not isinstance(row[k], str) for k in PIVOTS.values()):
            raise ValueError('Native nullable text colors required')
        when = _date(row['ReportDate'])
        if previous is not None and when < previous:
            raise ValueError('Source must retain native ORDER BY ReportDate')
        previous = when
    target_present = any(tuple(row[k] for k in IDENTIFIERS) == TARGET for row in rows)
    retained = [(row, (today - _date(row['ReportDate'])).days) for row in rows]
    retained = [(row, days) for row, days in retained if 0 <= days < 90]
    result = dict(report_type=report_type, host_date=today.isoformat(),
                  diagnostic_required=not target_present,
                  diagnostic_filename='debug_missing_entry_21104027051000_P023_1002.txt',
                  action='PRESERVE_EXISTING', reason='no data within host-date 90-day window',
                  columns=[], rows=[])
    if not retained:
        return result
    # pandas.read_sql promotes a nullable int column to float when the *whole*
    # fetched population contains both int and NULL, even if NULL is filtered out.
    virtual_float = virtual and any(row['VirtualNorm'] is None for row in rows) and any(
        row['VirtualNorm'] is not None for row in rows)
    static, pivots = {}, {}
    color_field = PIVOTS[report_type]
    for row, days in retained:
        pair = tuple(row[k] for k in IDENTIFIERS)
        when = _date(row['ReportDate'])
        if pair not in static or when > static[pair][0]:
            static[pair] = (when, row)
        color = row[color_field]
        if row['Norm'] == 0 and (not virtual or row['VirtualNorm'] == 0):
            color = 'Grey'
        day = 'D' + str(90 - days)
        if color is not None:
            pivots.setdefault(pair, {}).setdefault(day, color)
    columns = (*STATIC[:6], *(('VirtualNorm',) if virtual else ()), *DAYS,
               'Age', *(c + 'Count' for c in COLORS), *STATIC[6:])
    output = []
    # pandas.groupby defaults sort=True; this is not SQL collation sorting.
    for pair in sorted(static):
        row = static[pair][1]
        values = {k: row[k] for k in STATIC}
        if virtual:
            value = row['VirtualNorm']
            values['VirtualNorm'] = float(value) if virtual_float and value is not None else value
        values.update({day: pivots.get(pair, {}).get(day) for day in DAYS})
        current = values['D90']
        age = 0 if current is None else 1
        if current is not None:
            for i in range(89, 0, -1):
                if values['D' + str(i)] is None or values['D' + str(i)] == current:
                    age += 1
                else:
                    break
        values['Age'] = age
        for color in COLORS:
            values[color + 'Count'] = sum(values['D' + str(i)] == color for i in range(90, 60, -1))
        output.append({field: values[field] for field in columns})
    result.update(action='REPLACE_ZIP', reason=None, columns=list(columns), rows=output)
    return result


def csv_bytes(report, *, line_ending):
    """Canonical pandas-style minimal quoting; caller binds native OS newline."""
    if report['action'] != 'REPLACE_ZIP':
        raise ValueError('Absent report does not create or replace a CSV')
    if line_ending not in ('\n', '\r\n'):
        raise ValueError('Explicit native file line ending required')
    stream = StringIO(newline='')
    writer = csv.writer(stream, lineterminator=line_ending)
    writer.writerow(report['columns'])
    writer.writerows([row[field] for field in report['columns']] for row in report['rows'])
    return stream.getvalue().encode('utf-8')
