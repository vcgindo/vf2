"""BPR unpaged CSV column and configured header contract."""
from mta.presentation.legacy_ui import BPR_UI_CONFIG
from mta.presentation.rrr_export import selected_headers as common_headers

FIELDS = tuple('tags SKUCode SKUName WHCode WHName ParentWhCode ParentName Stock Norm GIT ts TechPen es PhysicalInventoryColorSequence EcoPen TechColor EcoColor Req RationedQTY LeftoverParentStock PhaseIn-Out ResidualSnP NormReq BlueReq vn'.split()) + (
    *(p+str(i) for p in ('sl','ll') for i in range(1,6)),
    *(p+str(i) for p in ('SKULocAttr','SKUAttr','LocAttr') for i in range(1,16)),
    'Remark','intransit','Availability_01_30','Availability_31_60','Availability_61_90')


def selected_headers(state):
    return common_headers(state, FIELDS, configuration=BPR_UI_CONFIG)
