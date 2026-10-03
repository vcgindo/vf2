"""Pinned existing UI metadata and pure payload helpers; no old ORM."""
from __future__ import annotations
import json
from pathlib import Path

PLANNING_CUSTOM_HEADERS = (
    ('SKUCode','sc',1), ('WHCode','wc',2), ('SKUDescription','sd',3), ('WHDescription','wd',4),
    ('DelayDays','dd',5), ('SKUStatus','ss',6), ('Status','s',7), ('ParentWhCode','pwc',8),
    ('ParentName','pn',9), ('Norm','n',10), ('MinNorm','mn',11), ('RLT','rlt',12),
    ('RCP','rcp',13), ('GCP','gcp',14), ('OCP','ocp',15), ('MinOrderCount','moc',16),
    ('PackSize','ps',17), ('FGRMFlag','frf',18), ('DBMActive','da',19), ('OrderNo','odn',20),
    ('TruckStatus','ts',21), ('TransporterName','tn',22), ('TransporterCode','tc',23),
    ('FromLocation','fl',24), ('ToLocationQty','itq',25), ('TransporterContact','tct',26),
    ('CreationDate','cd',27), ('SLT','slt',28), ('Ageing','ag',29), ('ETA','eta',30),
    ('CurrentLocation','cl',31), ('Remark','rmk',32), ('LRCode','lc',33), ('Stock','sk',34),
    ('Tech Pen','pt',35), ('Tech Pen Percentage','tpp',36), ('GIT','git',37),
    ('Eco Pen Percentage','epp',38), ('Eco Pen','ep',39), ('RationedQty','rq',40),
    ('Business','sl1',41), ('Category','sl2',42), ('Family','sl3',43),
    ('Zone','ll1',46), ('Location Group','ll2',47), ('WH Type','ll3',48),
)

REASON_CODES = {
    1: "Stockout has occurred today. Upward revision suggested.",
    2: "Virtual Stockout has occurred. Upward revision suggested.",
    3: "Stockout has occurred in Red Check Period. Upward revision suggested.",
    4: "Buffer penetration has consistently been red. Upward revision suggested.",
    5: "Buffer penetration has consistently been green. Downward revision suggested.",
    6: "High spike count",
    7: "Norm 0 Order based Increase",
    8: "Norm 0 Order based Increase suggestion generated and forcefully accepted",
    9: "Norm 0 Order based Increase suggestion is not generated but forcefully accepted",
    10: "Norm 1 Consumption based Increase",
    11: "Norm 2 Consumption based Decrease ",
    12: "Delisting of norm. Norm 0 suggested.",
}

def _ui_config_row(
    code: str,
    position: int,
    header: str,
    visible: bool,
    value: str,
    *,
    report_name: str = "NormSuggestion",
    alignment: str = "left      ",
) -> dict:
    return {
        "ReportName": report_name,
        "Col_Code": code,
        "Col_Position": position,
        "Header": header,
        "Visible": visible,
        "CellAlignment": alignment,
        "Value": value,
        "TagID": None,
    }

DBM_UI_CONFIG = [
    _ui_config_row("OldNormValue", 9, "Old Norm", True, "*Error"),
    *[
        _ui_config_row(
            f"SKUAttribute{index}",
            99,
            f"S{index}" if index < 3 else f"s{index}",
            index < 3,
            "*Error*" if index < 4 else "*Error",
        )
        for index in range(1, 16)
    ],
    *[
        _ui_config_row(
            f"LocAttribute{index}",
            99,
            f"L{index}" if index < 3 else f"l{index}",
            index < 3,
            "*Error*" if index < 4 else "*Error",
        )
        for index in range(1, 16)
    ],
    *[
        _ui_config_row(
            f"SKULocAttribute{index}",
            99,
            f"SL{index}" if index < 3 else f"sl{index}",
            index < 3,
            "*Error*" if index < 4 else "*Error",
        )
        for index in range(1, 16)
    ],
    _ui_config_row("SKUCode", 2, "SKU Code", True, "*Error*"),
    _ui_config_row("SKUName", 3, "SKU Name", True, "*Error*"),
    _ui_config_row("LocCode", 4, "Location Code", True, "*Error*"),
    _ui_config_row("LocName", 5, "Location Name", True, "*Error*"),
    _ui_config_row("ParentWhCode", 8, "Parent WH Code", False, "*Error*"),
    _ui_config_row("dailydatagraph", 12, "", True, "*Error"),
    _ui_config_row("NewNormValue", 10, "New Norm", True, "*Error"),
    _ui_config_row("Comment", 11, "Reason", True, "*Error"),
    _ui_config_row("Sleep", 14, "Sleep", True, "*Error"),
    _ui_config_row("Suggestions", 13, "", True, "*Error*"),
]

def _report_columns(report_name: str, columns: list[tuple]) -> list[dict]:
    """Create only recovered columns backed by the migrated projection."""
    return [
        _ui_config_row(
            code,
            position,
            header,
            visible,
            value,
            report_name=report_name,
            alignment=alignment,
        )
        for code, position, header, visible, alignment, value in columns
    ]

# Exact retained DB-creation rows, including hidden export metadata.
# Source hashes and complete comparison: f3-stage2-bpr-batch-001/config-audit.json.
_BPR_METADATA = json.loads((Path(__file__).parents[1]/'config'/'bpr_selected_ui.json').read_text())
BPR_UI_CONFIG = _BPR_METADATA['columns']


def bpr_ui_columns():
    # UIConfigProcessor: visible only, LEFT JOIN types, FOR JSON omits NULLs.
    return [dict({key:value for key,value in row.items() if key != 'TagID' and value is not None},
                 **({'DataType':match['DataType']} if match.get('DataType') is not None else {}))
            for row in BPR_UI_CONFIG if row['Visible']
            for match in ([t for t in _BPR_METADATA['types']
                           if t['ColCode'].casefold() == row['Col_Code'].casefold()] or [{}])]


RESEARCH_INSIGHT_UI_CONFIG = _report_columns("ResearchInsight", [
    ("Tags", 0, "Tags", True, "left      ", "*Error*"),
    ("SKUCode", 1, "SKUCode", True, "left      ", "*Error*"),
    ("SKUName", 2, "Description", True, "left      ", "*Error*"),
    ("WHCode", 3, "Location Code", True, "left      ", "*Error*"),
    ("WHName", 4, "Location", True, "left      ", "*Error*"),
    ("Norm", 5, "Norm", True, "right     ", "*Error*"),
    ("Stock", 6, "Stock", True, "right     ", "*Error*"),
    ("TechPen", 7, "On hand Inv. Pen", True, "right     ", "*Error*"),
    ("TechColor", 8, "On hand Inv. Color", True, "left      ", "*Error*"),
    ("GIT", 9, "GIT/ Pending", True, "right     ", "*Error*"),
    ("EcoPen", 10, "Pipeline Inv. Pen", True, "right     ", "*Error*"),
    ("EcoColor", 11, "Pipeline Inv. Color", True, "left      ", "*Error*"),
    ("vn", 12, "Virtual Norm", True, "left      ", "*Error*"),
    ("dailydatagraph", 13, "-", True, "left      ", "*Error*"),
])

def _mdm_field(key: str, position: int, label: str, *, data_type: str = "String",
               editable: bool = True) -> dict:
    return {
        "displayName": label,
        "key": key,
        "col_Position": str(position),
        "visible": True,
        "isAdd": editable,
        "isEdit": editable,
        "isDownload": True,
        "isApplicable": editable,
        "dataType": data_type,
    }

MDM_MODIFY_CONFIG = [{
    "id": 3,
    "name": "SKULocation",
    "fields": [
        _mdm_field("sc", 1, "SKU Code", editable=False),
        _mdm_field("sd", 2, "SKU Description", editable=False),
        _mdm_field("wc", 3, "Location Code", editable=False),
        _mdm_field("wd", 4, "Location Description", editable=False),
        _mdm_field("pd", 4, "Parent Location Name", editable=False),
        _mdm_field("pwc", 5, "Parent Location Code", editable=False),
        _mdm_field("n", 6, "Norm", data_type="Number", editable=False),
        _mdm_field("rlt", 8, "RLT", data_type="Number"),
        _mdm_field("ps", 13, "Pack Size", data_type="Number"),
        _mdm_field("da", 18, "DBM Active", data_type="Boolean"),
        _mdm_field("c1", 20, "SKULocAtt01"),
        _mdm_field("c2", 21, "SKULocAtt02"),
        _mdm_field("c3", 22, "SKULocAtt03"),
        _mdm_field("c4", 23, "Original Parent"),
        _mdm_field("c6", 25, "SKULocAtt06", editable=False),
    ],
}]

RRR_UI_CONFIG = json.loads((Path(__file__).parents[1] / 'config' / 'rrr_selected_ui.json').read_text())

BOR_UI_CONFIG = _report_columns("BuyerOrderReport", [
    ("SKUCode", 1, "SKU Code", True, "left      ", "*Error*"),
    ("SKUDesc", 2, "SKU Description", True, "left      ", "*Error*"),
    ("WHCode", 3, "Location Code", True, "left      ", "*Error*"),
    ("WHDescription", 4, "Location Description", True, "left      ", "*Error*"),
    ("DispatchReq", 5, "Dispatch Quantity", True, "left      ", "*Error*"),
    ("EcoCol", 6, "Pipeline Inv. Color", False, "left      ", "*Error*"),
    ("Requirement", 7, "Requirement", False, "left      ", "*Error*"),
    ("TechCol", 8, "On hand Inv. Color", False, "left      ", "*Error*"),
    ("SupplierCode", 6, "Supplier Code", True, "left      ", "*Error*"),
    ("ReqTopOfRed", 8, "TOR", True, "left      ", "*Error*"),
    ("ReqTopOfYellow", 9, "TOY", True, "left      ", "*Error*"),
    ("ReqTopOfGreen", 10, "TOG", True, "left      ", "*Error*"),
    ("ReqTopOfBlue", 11, "TOB", True, "left      ", "*Error*"),
    ("GIT", 17, "GIT", False, "left      ", "*Error*"),
    ("Stock", 18, "Stock", False, "left      ", "*Error*"),
    ("DispatchPen", 12, "Dispatch Pen", True, "left      ", "*Error*"),
    ("DispatchColor", 23, "Dispatch Color", True, "left      ", "*Error*"),
    ("Norm", 99, "Norm", True, "left      ", "*Error*"),
    ("VirtualNorm", 18, "Virtual Norm", True, "left      ", "*Error*"),
    ("Remark", 19, "Lastest Remark", True, "left      ", "*Error*"),
    ("remarks", 20, "Enter New Remark", True, "left      ", "*Error*"),
    ("rh", 21, "Remark History", True, "center    ", "*Error*"),
])

BOR_OA_UI_CONFIG = _report_columns("BOR_OA", [
    ("SKUCode", 1, "SKUCode", True, "left      ", "*Error*"),
    ("SKUDescription", 2, "SKU Description", True, "left      ", "*Error*"),
    ("WhCode", 3, "Location Code", True, "left      ", "*Error*"),
    ("WHDescription", 4, "Location Description", True, "left      ", "*Error*"),
    ("SupplierCode", 5, "SupplierCode", True, "left      ", "*Error*"),
    ("SupplierDesc", 6, "SupplierDesc", True, "left      ", "*Error*"),
    ("Norm", 7, "Norm ", True, "right     ", "*Error*"),
    ("Stock", 8, "Stock", True, "right     ", "*Error*"),
    ("VirtualNorm", 9, "Virtual Norm", True, "right     ", "*Error*"),
    ("GIT", 10, "GIT/ Pending", True, "right     ", "*Error*"),
    ("Requirement", 12, "Requirement", True, "left      ", "*Error"),
    ("Req_TOB", 13, "Req TOB", True, "left      ", "*Error"),
    ("Req_TOR", 14, "Req TOR", True, "left      ", "*Error"),
    ("Req_TOY", 15, "Req TOY", True, "left      ", "*Error*"),
    ("Req_TOG", 16, "Req TOG", True, "left      ", "*Error*"),
    ("Req_TOBlue", 17, "Req TOBlue", True, "left      ", "*Error"),
    ("DispatchQty", 18, "Dispatch Qty", True, "right     ", "*Error"),
    ("Dispatch_TOB", 19, "Dispatch TOB", True, "right     ", "*Error"),
    ("Dispatch_TOR", 20, "Dispatch TOR", True, "right     ", "*Error"),
    ("Dispatch_TOY", 21, "Dispatch TOY", True, "right     ", "*Error"),
    ("Dispatch_TOG", 22, "Dispatch TOG", True, "right     ", "*Error"),
    ("Dispatch_ToBlue", 23, "Dispatch ToBlue", True, "right     ", "*Error"),
    ("DispatchColor", 24, "Dispatch Color", True, "right     ", "*Error"),
    ("Remark", 28, "Latest Remark", True, "left      ", "*Error*"),
    ("remarks", 29, "Enter New Remark", True, "left      ", "*Error*"),
    ("rh", 30, "Remark History", True, "left      ", "*Error*"),
])

RRR_OA_UI_CONFIG = _report_columns("RRR_OA", [
    ("SKUCode", 1, "SKUCode", True, "left      ", "*Error*"),
    ("SKUDescription", 2, "SKU Description", True, "left      ", "*Error*"),
    ("WhCode", 3, "Location Code", True, "left      ", "*Error*"),
    ("WHDescription", 4, "Location Description", True, "left      ", "*Error*"),
    ("ParentWhCode", 5, "ParentWhCode", True, "left      ", "*Error*"),
    ("AllocationFor", 7, "Allocation for", True, "left      ", "*Error*"),
    ("Norm", 8, "Norm", True, "right     ", "*Error*"),
    ("Stock", 9, "Stock", True, "right     ", "*Error*"),
    ("VirtualNorm", 10, "Virtual Norm", True, "right     ", "*Error*"),
    ("GIT", 11, "GIT/ Pending", True, "right     ", "*Error*"),
    ("Requirement", 13, "Requirement", True, "right     ", "*Error*"),
    ("TOBlack_ReqQty", 51, "Req TOB", True, "right     ", "*Error*"),
    ("TOR_ReqQty", 52, "Req TOR", True, "right     ", "*Error*"),
    ("TOY_ReqQty", 53, "Req TOY", True, "right     ", "*Error*"),
    ("TOGreen_ReqQty", 54, "Req TOG", True, "right     ", "*Error*"),
    ("TOBlue_ReqQty", 55, "Req TOBlue", True, "right     ", "*Error*"),
    ("RationedQty", 57, "Rationed Qty", True, "right     ", "*Error*"),
    ("TOBlack_AllocQty", 59, "Dispatch TOB", True, "right     ", "*Error*"),
    ("TOR_AllocQty", 60, "Dispatch TOR", True, "right     ", "*Error*"),
    ("TOY_AllocQty", 61, "Dispatch TOY", True, "right     ", "*Error*"),
    ("TOGreen_AllocQty", 62, "Dispatch TOG", True, "right     ", "*Error*"),
    ("TOBlue_AllocQty", 63, "Dispatch TOBlue", True, "right     ", "*Error*"),
])

SUPPLIER_ALLOCATION_UI_CONFIG = [
    {**row, "ReportName": "SupplierWiseAllocation"}
    for row in BOR_OA_UI_CONFIG
    if row["Col_Code"] not in {"Remark", "remarks", "rh"}
]

SUPPLIER_DISPATCH_UI_CONFIG = _report_columns("SupplierDispatchReport", [
    ("SKUCode", 1, "SKUCode", True, "left      ", "*Error*"),
    ("SKUDesc", 2, "Description", True, "left      ", "*Error*"),
    ("WHCode", 3, "Location Code", True, "left      ", "*Error*"),
    ("WHDescription", 4, "Location Description", True, "left      ", "*Error*"),
    ("DispatchReq", 5, "Dispatch Quantity", True, "left      ", "*Error*"),
    ("DispatchColor", 23, "Dispatch Color", True, "left      ", "*Error*"),
])

PLANNING_GIT_UI_CONFIG = _report_columns("GIT_From_Parent", [
    ("SKUCode", 1, "SKU Code", True, "left      ", "*Error*"),
    ("SKUName", 2, "SKU Description", True, "left      ", "*Error*"),
    ("WHCode", 3, "Destination Location", True, "left      ", "*Error*"),
    ("WHName", 4, "Destination Description", True, "left      ", "*Error*"),
    ("FromLocation", 5, "Source Location", True, "left      ", "*Error*"),
    ("OrderNo", 6, "Order No", True, "left      ", "*Error*"),
    ("ShipmentId", 7, "Shipment ID", True, "left      ", "*Error*"),
    ("Quantity", 8, "In-Transit Quantity", True, "right     ", "*Error*"),
    ("ETA", 9, "ETA", True, "left      ", "*Error*"),
    ("Transporter", 10, "Transporter", True, "left      ", "*Error*"),
    ("Status", 11, "Status", True, "left      ", "*Error*"),
    ("GIT", 12, "Current GIT", True, "right     ", "*Error*"),
])

PLANNING_EXPEDITE_UI_CONFIG = _report_columns("Expedit_From_Parent_ED", [
    ("SKUCode", 1, "SKU Code", True, "left      ", "*Error*"),
    ("SKUName", 2, "SKU Description", True, "left      ", "*Error*"),
    ("WHCode", 3, "Location", True, "left      ", "*Error*"),
    ("WHName", 4, "Location Description", True, "left      ", "*Error*"),
    ("ParentWhCode", 5, "Parent Location", True, "left      ", "*Error*"),
    ("Requirement", 6, "Requirement", True, "right     ", "*Error*"),
    ("ExpediteQty", 7, "Expedite Quantity", True, "right     ", "*Error*"),
    ("PipelinePen", 8, "Pipeline Penetration", True, "right     ", "*Error*"),
    ("DispatchColor", 9, "Dispatch Colour", True, "left      ", "*Error*"),
])

PLANNING_EXCESS_UI_CONFIG = _report_columns("Excess_Inventory_Review", [
    ("SKUCode", 1, "SKU Code", True, "left      ", "*Error*"),
    ("SKUName", 2, "SKU Description", True, "left      ", "*Error*"),
    ("WHCode", 3, "Location", True, "left      ", "*Error*"),
    ("WHName", 4, "Location Description", True, "left      ", "*Error*"),
    ("VirtualNorm", 5, "Virtual Norm", True, "right     ", "*Error*"),
    ("Stock", 6, "Stock", True, "right     ", "*Error*"),
    ("ExcessQty", 7, "Excess Quantity", True, "right     ", "*Error*"),
    ("UnitPrice", 8, "Unit Price", True, "right     ", "*Error*"),
    ("Amount", 9, "Excess Value", True, "right     ", "*Error*"),
])

PLANNING_FULFILMENT_CUSTOM_CONFIG = _report_columns("Order_Fulfillment_Review_CS", [
    (code,position,header,True,'left      ',None)
    for header,code,position in PLANNING_CUSTOM_HEADERS
])

PLANNING_FULFILMENT_UI_CONFIG = _report_columns("Order_Fulfillment_Review", [
    (code, position, header, True, alignment, None)
    for code, position, header, alignment in [
        ('c',1,'Coverage','Left      '), ('t',2,'Tags','Left      '),
        ('sc',3,'SKU Code','Left      '), ('sd',4,'SKU Description','Left      '),
        ('wc',5,'WHCODE','Left      '), ('wcd',6,'Location','Left      '),
        ('vn',7,'Virtual Norm','Right     '), ('n',8,'Norm','Right     '),
        ('s',9,'Stock','Right     '), ('git',10,'GIT','Right     '),
        ('rq',11,'Rationed Qty','Right     '), ('nr',12,'Norm Requirement','Right     '),
        ('tq',15,'Total Requirement','Right     '), ('g',16,'Gap','Right     '),
        ('pip',17,'On-hand Inventory Pen','Right     '),
        ('plp',18,'Pipeline Inventory Pen','Right     '), ('p',19,'Price','Right     '),
        ('sl1',20,'Business','Left      '), ('sl2',21,'Category','Left      '),
        ('sl3',22,'Family','Left      '), ('tsnp',23,'Total SnP','Right     '),
        ('ll1',25,'Zone','Left      '), ('ll2',26,'Location Group','Left      '),
        ('ll3',27,'WH Type','Left      '), ('dailydatagraph',30,'','Left      '),
    ]
])

CHRONIC_UI_CONFIG = _report_columns("ChronicUnavailability", [
    ("skucode", 1, "SKU Code", True, "left      ", "*Error*"),
    ("skudesc", 2, "SKU Description", True, "left      ", "*Error*"),
    ("location", 3, "Location", True, "left      ", "*Error*"),
    ("parentloc", 4, "Parent Location", True, "left      ", "*Error*"),
    ("RLT", 5, "RLT", True, "right     ", "*Error*"),
    ("BlackRedAgeing", 6, "Black/Red Ageing", True, "right     ", "*Error*"),
    ("Techcolor", 7, "On-Hand Colour", True, "left      ", "*Error*"),
    ("Executive", 8, "On-Hand Penetration", True, "right     ", "*Error*"),
    ("ecocolor", 9, "Pipeline Colour", True, "left      ", "*Error*"),
    ("ExecutiveEco", 10, "Pipeline Penetration", True, "right     ", "*Error*"),
    ("RationedStockatparent", 11, "Rationed Quantity", True, "right     ", "*Error*"),
])

def _planning_config(report_name: str, template: list[dict]) -> list[dict]:
    """Reuse a fact-backed Planning shape while preserving every UI name."""
    return [{**row, "ReportName": report_name} for row in template]

UI_CONFIGS = {
    "NormSuggestion": DBM_UI_CONFIG,
    "AdminBPR": BPR_UI_CONFIG,
    "ResearchInsight": RESEARCH_INSIGHT_UI_CONFIG,
    "RationRequirementReport": RRR_UI_CONFIG,
    "BuyerOrderReport": BOR_UI_CONFIG,
    "BOR_OA": BOR_OA_UI_CONFIG,
    "RRR_OA": RRR_OA_UI_CONFIG,
    "SupplierWiseAllocation": SUPPLIER_ALLOCATION_UI_CONFIG,
    "SupplierDispatchReport": SUPPLIER_DISPATCH_UI_CONFIG,
    "GIT_From_Parent": PLANNING_GIT_UI_CONFIG,
    "GIT_To_Child_LW": _planning_config("GIT_To_Child_LW", PLANNING_GIT_UI_CONFIG),
    "GIT_To_Child_TW": _planning_config("GIT_To_Child_TW", PLANNING_GIT_UI_CONFIG),
    "GIT_To_Child_CS": _planning_config("GIT_To_Child_CS", PLANNING_GIT_UI_CONFIG),
    "Expedit_From_Parent_ED": PLANNING_EXPEDITE_UI_CONFIG,
    "Expedite_To_Parent_CAAP": _planning_config("Expedite_To_Parent_CAAP", PLANNING_EXPEDITE_UI_CONFIG),
    "Expedit_To_Child_ED": _planning_config("Expedit_To_Child_ED", PLANNING_EXPEDITE_UI_CONFIG),
    "Expedite_To_Child_CS": _planning_config("Expedite_To_Child_CS", PLANNING_EXPEDITE_UI_CONFIG),
    "Excess_Inventory_Review": PLANNING_EXCESS_UI_CONFIG,
    "Excess_Inventory_Review_CS": _planning_config("Excess_Inventory_Review_CS", PLANNING_EXCESS_UI_CONFIG),
    "Order_Fulfillment_Review": PLANNING_FULFILMENT_UI_CONFIG,
    "Order_Fulfillment_Review_CS": PLANNING_FULFILMENT_CUSTOM_CONFIG,
    "ChronicUnavailability": CHRONIC_UI_CONFIG,
}

UI_CONFIGS.update(json.loads((Path(__file__).parents[1]/'config'/'expedite_selected_ui.json').read_text()))

UI_CONFIGS.update(json.loads((Path(__file__).parents[1]/'config'/'git_selected_ui.json').read_text()))

UI_CONFIGS.update(json.loads((Path(__file__).parents[1]/'config'/'excess_selected_ui.json').read_text()))

UI_CONFIGS.update(json.loads((Path(__file__).parents[1]/'config'/'btr_selected_ui.json').read_text()))

def _no_active_filters(payload: dict) -> bool:
    filters = payload.get("filters")
    if filters in (None, {}, []):
        return True
    if not isinstance(filters, dict):
        return False

    # The preserved frontend always sends named filter groups containing id and
    # label metadata. Only non-empty group ``filters`` are active predicates.
    if all(
        isinstance(group, dict) and isinstance(group.get("filters"), list)
        for group in filters.values()
    ):
        return all(not group["filters"] for group in filters.values())
    return all(value in (None, "", {}, []) for value in filters.values())

def _filter_rows(rows: list[dict], payload: dict) -> list[dict]:
    """Apply the retained filter payload without changing the response shape.

    The frontend submits groups of ``attributeName/operator/value`` records.
    Only fields actually present in a projection are evaluated; unknown
    attributes therefore fail closed instead of being silently converted into
    a fabricated report predicate.
    """
    filters = payload.get("filters")
    if filters in (None, {}, []):
        return rows
    groups = filters.values() if isinstance(filters, dict) else []
    predicates = [item for group in groups if isinstance(group, dict)
                  for item in group.get("filters", []) if isinstance(item, dict) and item.get("value") not in (None, "", [])]
    aliases = {"SKUCode": "SKUCode", "SKUName": "SKUName", "WhCode": "WhCode", "WHCode": "WHCode",
               "WHName": "WHName", "LocationCode": "WHCode", "TechColor": "TechColor", "EcoColor": "EcoColor",
               "PhysicalColor": "PhysicalColor", "PipelineColor": "PipelineColor", "Coverage": "Coverage"}
    def matches(row: dict, predicate: dict) -> bool:
        field = aliases.get(str(predicate.get("attributeName") or predicate.get("name") or ""), predicate.get("attributeName"))
        if field not in row:
            return False
        wanted, actual, operator = predicate.get("value"), row.get(field), str(predicate.get("operator") or "equals").casefold()
        values = wanted if isinstance(wanted, list) else [wanted]
        for value in values:
            if isinstance(actual, (int, float)):
                try:
                    comparable = float(value)
                except (TypeError, ValueError):
                    continue
                if operator in {"equals", "=", "=="} and actual == comparable: return True
                if operator in {"greaterthan", ">"} and actual > comparable: return True
                if operator in {"lessthan", "<"} and actual < comparable: return True
            else:
                left, right = str(actual).casefold(), str(value).casefold()
                if operator in {"contains", "like"} and right in left: return True
                if operator in {"doesnotcontain", "not like"} and right not in left: return True
                if operator in {"equals", "=", "=="} and left == right: return True
                if operator in {"doesnotequal", "!="} and left != right: return True
        return False
    return [row for row in rows if all(matches(row, predicate) for predicate in predicates)]

def _pagination(payload: dict) -> tuple[int, int] | None:
    pagination = payload.get("paginationParameter") or {}
    try:
        page = max(int(pagination.get("pageNumber", 1)), 1)
        size = max(min(int(pagination.get("recordsPerPage", 50)), 5000), 1)
    except (TypeError, ValueError):
        return None
    return page, size

def _page(rows: list[dict], payload: dict) -> list[dict]:
    page_size = _pagination(payload)
    if page_size is None:
        raise ValueError("invalid pagination")
    page, size = page_size
    return rows[(page - 1) * size:page * size]
