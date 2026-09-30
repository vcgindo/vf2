export enum EnumKitStatus {
    Nokit = 1,
    PartialKit = 2,
    FullKit = 3,
}

export enum ProcurementSeriesDataYKey {
    total_soh = 0,
    total_sit = 1,
    total_po = 2,
    shortage = 3
}
export enum ProcurementSeriesDataYName {
    "Orders With Full Kit (On hand Stock)" = 0,
    "Orders With Full Kit (incl. In Transit Inventory + In QC)" = 1,
    "Orders With Full Kit (incl. In Open Orders)" = 2,
    "Orders With RM /PM Shortage" = 3
}

export enum ProcurementSeriesDataFill {
    "#F4BD8E" = 0,
    "#F09241" = 1,
    "#AD5000" = 2,
    "#6A3001" = 3
}

export enum OTIFTags {
    OTIFNone = 0,
    OT_False_IF_False = 1,
    OT_True_IF_True = 2,
    OT_True_IF_False = 3,
    OT_False_IF_True = 4,
}

export enum InputTypes {
    TextCompare = "textCompare",
    NumberCompare = "numberCompare",
    MultiSelect = "multiSelect",
    Checkbox = "checkbox",
    Search = "search",
    Select = "select"
}

export enum pagination {
    mtoPageSize = 500
}

export enum UIGridCode {

    // Procurement
        "ProcMaterialCovOpenSales" = 100,  
        "ProcMaterialCovOpenSalesAll" = 106,  
        "ProcPlanning" = 101, 
        "ProcMaterialRequirement" = 102,  
        "ProcDayWiseCov" = 103,  
        "ProcRMPMOrderCov" = 104,
        "ProcPlanningSimulation" = 105,  // Blocked

    // Production
        "ProdEnquiryResponse" = 200,
        "ProdDDQ" = 201,
        // "ProdDDQUnScheduleOrder" = 202,// not required
        // "ProdDDQThree" = 203,// not required
        "ProdOrderRescheduling" = 204,
        "ProdFullkitAssignment" = 205,
        "ProdDynamicReleaseManagement" = 206,// Blocked
        "ProdDeptWiseBMReport" = 207,// pending
        "ProdOverallBMReport" = 208,// pending
        "ProdFolSummary" = 209,
        "ProdStplAndFullKit" = 210,
        "ProdElapsedTime" = 211,
        "ProdOrderAtRisk" = 212,
    "ProdOrderBalance" = 213,
        
    "prodFutureLoadChart" = 214,

    // POOGI
        "PoogiReasonForDelayedOrders" = 300,
        "PoogiOTIFAnalysis" = 301,
        "PoogiOTAndIFAnalysis" = 302,
        "PoogiLeadTime" = 303,
        "PoogiTopFailureReason" = 304,  // code commented pending
}   

export enum FilterPageName {
    Proc_Material_Coverage_For_OpenSO= "Material_Coverage_For_OpenSO",
    Proc_Procurement_Planning= "Procurement_Planning",
    Proc_Material_Requirement="Proc_Material_Requirement",
    Proc_Day_Wise_Coverage= "Day_Wise_Coverage",
    Proc_RM_PM_OrderWise="RM_PM_OrderWise",
    Proc_RM_PM_BufferTrend= "RM_PM_BufferTrend",
    Proc_Expediting_RM_And_Suppliers= "Expediting_RM_And_Suppliers",
    Proc_MaterialCoverageforOpenSalesOrder_Child= "MaterialCoverageforOpenSalesOrder_Child",

    Prod_DDQ= "DDQ",
    Prod_FullKit_Assignment="FullKit_Assignment",
    Prod_Dynamic_Release_Management="Dynamic_Release_Management",
    Prod_OverAll_BMReport="OverAll_BMReport",
    Prod_Dept_Wise_BM_Report= "Dept_Wise_BM_Report",
    Prod_STPL_And_FullKits="STPL_And_FullKits",
    Prod_Order_Balance="Order_Balance",
    Prod_Order_At_Risk="Order_At_Risk",
    Prod_Order_Rescheduling = "Order_Rescheduling",
    
    Future_Order_Load_Chart='Future_Order_Load_Chart',

    Poogi_Reason_For_Delayed_Orders="Reason_For_Delayed_Orders",
    Poogi_OTIF_Analysis= "OTIF_Analysis",
    Poogi_OTIF_And_Analysis="OTandIF_Analysis",
    Poogi_Lead_Time="Lead_Time",
    Poogi_Top_Failure_Reasons="Top_Failure_Reasons",
    Poogi_Trend_Of_Failure_Reasons="Trend_Of_Failure_Reasons",
    Poogi_Elapsed_Time="Elapsed_Time",

   

}

export enum ExcelExportName{
    Login_Audit_Report = "Login_Audit_Report",
    UserData ="UserData",
    ErrorData = "ErrorData",
    Enquiry_Response="Enquiry_Response",
    FOL_Summary="FOL_Summary",
    Order_At_Risk="Order_At_Risk",
    Order_Balance="Order_Balance",
    OverallBMReport="OverallBMReport"
    
}

export enum ApplicationName {
    "Retail"  = 1, 
    "Replenishment" = 2,
    "Production and Procurement" = 3
}
