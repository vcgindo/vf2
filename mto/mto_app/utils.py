from enum import Enum, IntEnum, StrEnum


class OTIFTags(IntEnum):
    OTIFNone = 0,
    OT_False_IF_False = 1,
    OT_True_IF_True = 2,
    OT_True_IF_False = 3,
    OT_False_IF_True = 4,

class DBR_Settings(StrEnum):
    delivery_tolerance = 'DeliveryTolerance',
    mfg_tolerance = 'MfgTolerance',
    unit_of_measurement = 'UnitOfMeasurement',
    unresolved_reason_threshold = 'UnresolvedReasonThreshold',
    emergent_reason_threshold = 'EmergentReasonThreshold',
    close_orders_from_ui  = 'CloseOrdersFromUI'
    is_data_permission_enabled = 'IsDataPermissionEnabled'
    bom_component_allocation_type = 'BOM_Component_Allocation_Type'
    order_load_operator = 'OLOperator'

class Report_Configurations(StrEnum):
    OT_failed_difference_range = 'OTFailedDifferenceRange',
    IF_failed_difference_range_in_percent = 'IFfailedDifferenceRangeInPercent'

class eVFOrderType(Enum):
    MTO = 'MTO'
    MTA = 'MTA'

class eColors(Enum):
    WHITE = 'White'
    BLUE = 'Blue'
    RED = 'Red'
    BLACK = 'Black'
    YELLOW = 'YELLOW'
    GREEN = 'GREEN'

    # Lowercase
    black = 'black'
    blue = 'blue'
    red = 'red'
    white = 'white'
    gray = 'gray'

class eReportName(Enum):
    proc_planning = 'ProcurementPlanningShortage'
    proc_planning_child = 'ProcPlanningReportChildren'
    material_so = 'MaterialCoverageforOpenSalesOrder'
    material_so_child = 'MaterialCoverageforOpenSalesOrder_Child'
    bm_report = 'BMReport'
    bom_explosion = 'BomExplosion'
    DDQ = 'DueDateQuotation'
    DeptWiseReport = 'DeptWiseReport'

    OTIFAnalysis = 'OTIFAnalysis'
    reasonForDelayedOrder = 'ReasonForDelayedOrders'
    materialRequirement = 'MaterialRequirement'
    dayWiseCoverage = 'DayWiseCoverage'
    RMPMOrderWiseCoverage = 'RMPMOrderWiseCoverage'
    OrderRescheduling = 'OrderRescheduling'
    OrdersAtRisk = 'OrdersAtRisk'
    DynamicReleaseManagement = 'DynamicReleaseManagement'
    OrderBalance = 'OrderBalance'
    FullKitAssignment = 'FullKitAssignment'
    STPLAndFullKits = 'STPLAndFullKits'
    ElapseTime = 'Elapse Time'
    LeadTime = 'LeadTime'
    
class eChildName(Enum):
    children = 'children'
    bomexplosion = 'bomexplosion'
class ePageName(Enum):
    PROD_DDQ = "Prod_DDQ"
    PROC_MATERIAL_REQUIREMENT = "Proc_Material_Requirement"
    PROC_PROCUREMENT_PLANNING = "Proc_Procurement_Planning"
    PROC_MATERIAL_COVERAGE_FOR_OPENSO = "Proc_Material_Coverage_For_OpenSO"
    PROC_RM_PM_ORDERWISE = "Proc_RM_PM_OrderWise"
    PROD_DYNAMIC_RELEASE_MANAGEMENT = "Prod_Dynamic_Release_Management"
    MATERIAL_COVERAGE_FOR_OPEN_SO = "Material_Coverage_for_Open_Sales_Order"
    PROC_DAY_WISE_COVERAGE = "Proc_Day_Wise_Coverage"
    PROD_FULLKIT_ASSIGNMENT = "Prod_FullKit_Assignment"
    PROC_EXPEDITING_RM_AND_SUPPLIERS = "Proc_Expediting_RM_And_Suppliers"
    PROD_OVERALL_BMREPORT = "Prod_OverAll_BMReport"
    PROD_STPL_AND_FULLKITS = "Prod_STPL_And_FullKits"
    PROD_ORDER_AT_RISK = "Prod_Order_At_Risk"
    PROD_ORDER_BALANCE = "Prod_Order_Balance"
    POOGI_REASON_FOR_DELAYED_ORDERS = "Poogi_Reason_For_Delayed_Orders"
    POOGI_LEAD_TIME = "Poogi_Lead_Time"
    POOGI_OTIF_ANALYSIS = "Poogi_OTIF_Analysis"
    POOGI_OTandIF_ANALYSIS = "Poogi_OTandIF_Analysis"
    PROD_DEPT_WISE_BM_REPORT = "Prod_Dept_Wise_BM_Report"
    POOGI_TREND_OF_FAILURE_REASONS = "Poogi_Trend_Of_Failure_Reasons"
    POOGI_TOP_FAILURE_REASONS = "Poogi_Top_Failure_Reasons"
    FUTURE_ORDER_LOAD_CHART = "Future_Order_Load_Chart"

class AttributeTypes(Enum):
    Customer = 'customer'
    Order = 'order'
    Line = 'line'

class PermissionLevel(Enum):
    Level1 = 'level1'
    Level2 = 'level2'
    Level3 = 'level3'

class Attribute_types_column_mapping(Enum):
    order = 'order_attributes'
    line = 'line_order_attributes'
    item = 'item_attributes'
    computed = 'computed_line_attributes'

class HorizonEnum(Enum):
    default_horizon = 90

class FutureOrderLoadChartEnum(Enum):
    daily = 'daily'
    weekly = 'weekly'
    monthly = 'monthly'
    NotScheduleBeyondFOLHorizon = 'BFH'
    AllNotSchedule = 'ANS'
    PastScheduling = 'Past Scheduling'
    WithinScheduling = 'Within Scheduling'
    BeyondScheduling = 'Beyond Scheduling'
    Red  = "red"
    Grey = "gray"
    White = "white"
    PendingCCRQty = 1
    LoadWise = 2
    FutureOrderLoadWeekEndDay = 'FutureOrderLoadWeekEndDay'

class DefaultPageConfig(Enum):
    default_page_number = 1
    default_page_size = 15