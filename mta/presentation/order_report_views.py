"""Existing frontend order-report endpoints; all reads, no closing-state writes."""
from inspect import unwrap

from django.db import DatabaseError

from mta.presentation import views, order_reports
from mta.presentation.context import PublicationUnavailable


def columns(name):
    if name == 'OrderAllocationReport':
        # Visible rows of pinned native UI_ReportConfiguration_2.0.sql plus
        # UI_ReportColumnTypes_2.0.sql. This is seed-derived, not a live capture.
        specs = [('SKUCode', 'SKUCode'), ('SKUDescription', 'SKU Description'),
            ('DestWhCode', 'Location Code'), ('WHDescription', 'Location Description'),
            ('SrcWhCode', 'Parent WhCode'), ('ParentWhDesc', 'ParentWh Desc'),
            ('OrderKey', 'OrderKey'), ('DueDate', 'DueDate'), ('OrderColor', 'OrderColor'),
            ('BPP', 'BPP'), ('Qty', 'Pending Qty'),
            ('OrderWiseAllocatedQty', 'OrderWiseAllocatedQty'),
            ('PackSizeWiseAllocatedQty', 'PackSizeWiseAllocatedQty'), ('dailydatagraph', '')]
        result = []
        for index, (code, header) in enumerate(specs, 1):
            row = dict(ReportName=name, Col_Code=code, Col_Position=index, Header=header,
                Visible=True, CellAlignment='right     ' if 8 <= index <= 12 else 'left      ',
                DataType='Number' if code == 'BPP' else 'String')
            if index != 14:
                row['Value'] = '*Error' if index == 13 else '*Error*'
            result.append(row)
        return result
    if name == 'ElephantOrderReport':
        # No native EO configuration seed/capture was retained. These visible
        # columns are new metadata for the existing processor fields and UI
        # tooltip contract; they do not assert deployed configuration parity.
        specs = [('CustomerOrderID', 'Customer Order ID'), ('SKUCode', 'SKU Code'),
            ('SKUDescription', 'SKU Description'), ('WhCode', 'Location Code'),
            ('Qty', 'Qty'), ('TopmostWhCode', 'Topmost Location Code'),
            ('WHDescription', 'Location Description'), ('TopmostWhNorm', 'Topmost Location Norm'),
            ('RLTUptoSuppOrPlant', 'RLT Upto Supplier/Plant'), ('IntroDate', 'Intro Date'),
            ('CustomerExpectedDate', 'Customer Expected Date'),
            ('EPD', 'Earliest Possible Due Date'), ('DueDate', 'Due Date')]
        numbers = {'Qty', 'TopmostWhNorm', 'RLTUptoSuppOrPlant'}
        return [dict(ReportName=name, Col_Code=code, Col_Position=index, Header=header,
            Visible=True, CellAlignment='right     ' if code in numbers else 'left      ',
            DataType='Number' if code in numbers else 'String')
            for index, (code, header) in enumerate(specs, 1)]
    return None


@views.endpoint('GET')
def ui_config(request, payload):
    name = request.GET.get('reportName')
    if request.path.endswith('/EOUIConfig'):
        name = 'ElephantOrderReport'
    value = columns(name)
    return views.envelope(data=value) if value is not None else unwrap(views.ui_config)(request, payload)


@views.endpoint('POST')
def order_data(request, payload, *, elephant=False, count=False):
    try:
        value = order_reports.read(payload, elephant=elephant, count=count)
        if count:
            # Existing EO filter handler expects data[0].count, while initial
            # load reads recordCount. Preserve the canonical fields and supply
            # the explicit client aliases; calculation/count grain is fixed.
            return views.envelope(data=[{'count': value}] if elephant else
                [{'Count': value, 'count': value}], record_count=str(value) if elephant else None)
        return views.envelope(data=value, record_count=str(len(value)) if elephant else None)
    except PublicationUnavailable:
        raise
    except (ValueError, KeyError, TypeError, DatabaseError):
        return views.envelope(status=500)
