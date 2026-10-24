"""BPR unpaged CSV column and configured header contract."""
from mta.presentation.legacy_ui import BPR_UI_CONFIG
from mta.presentation.rrr_export import selected_headers as common_headers

FIELDS = tuple('tags SKUCode SKUName WHCode WHName ParentWhCode ParentName Stock Norm GIT ts TechPen es PhysicalInventoryColorSequence EcoPen TechColor EcoColor Req RationedQTY LeftoverParentStock PhaseIn-Out ResidualSnP NormReq BlueReq vn'.split()) + (
    *(p+str(i) for p in ('sl','ll') for i in range(1,6)),
    *(p+str(i) for p in ('SKULocAttr','SKUAttr','LocAttr') for i in range(1,16)),
    'Remark','intransit','Availability_01_30','Availability_31_60','Availability_61_90')


def selected_headers(state):
    return common_headers(state, FIELDS, configuration=BPR_UI_CONFIG)


def transport_chunks(rows, headers, *, chunk_size=65536):
    """Keep CSV bytes exact while bounding gateway/socket handoffs and memory."""
    from mta.presentation.rrr_export import csv_chunks
    if type(chunk_size) is not int or chunk_size < 1:
        raise ValueError('positive_BPR_transport_chunk_size_required')
    pending = bytearray()
    try:
        for row in csv_chunks(rows, headers):
            offset = 0
            while offset < len(row):
                take = min(chunk_size - len(pending), len(row) - offset)
                pending.extend(row[offset:offset + take])
                offset += take
                if len(pending) == chunk_size:
                    yield bytes(pending)
                    pending.clear()
        if pending:
            yield bytes(pending)
    finally:
        close = getattr(rows, 'close', None)
        if close:
            close()
