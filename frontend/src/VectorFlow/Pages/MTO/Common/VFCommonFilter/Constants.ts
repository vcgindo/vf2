export const staticHeaderConfig: any = {
    //Order Filter attributes
    id: { name: "Order ID", type: 'search'},
    lid: { name:"Line Item", type: 'search'},
    ic: { name:"Item Code", type: 'search'},
    ide: { name:"Item Description", type: 'textCompare'},
    ot: { name:"Order Type", type: 'multiSelect'},
    ms: { name:"Manufacturing Strategy", type: 'checkbox'},
    // ov: { name: "Amount", type: 'numberCompare'},
    // pbsz: { name: "Prod Buffer", type: 'numberCompare'},
    // pcbsz: {name: "Proc Buffer", type: 'numberCompare'},
    
    // Customer Filter Attributes
    cc: { name:"Customer Code", type: 'search'},
    cn: { name:"Customer Name", type: 'search'},
    
    // Major Filter Attributes
    majid: { name: "Major Reason", type: 'multiSelect'},
    minid: { name: 'Minor Reason', type: 'multiSelect'},
    
    // Resource Filter Attributes
    pn: { name: "Plant", type: 'search'},
    deptid: { name: "Department", type: 'search'},
    ccrid: { name: "CCR", type: 'search'},
    grpid: { name: "CCR Group", type: 'search'},
}

export const filterAttributes: any = {
    customer: ["cc", "cn"],
    resource: ["pn", "deptid", "grpid", "ccrid"],
    order: ["id", "lid", "ic", "ot",'ms', "ide", "ov", "pbsz", "pcbsz"],
    major: ["majid","minid"]
};

export const APIFilterConfig = {
    filSecVisConfig :  {
 
        "Proc_Material_Coverage_For_OpenSO" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
 
        "Proc_Procurement_Planning" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
 
 
        "Proc_Material_Requirement" : {
            mjr : false,
            or: true,
            res: false,
            cus: false
        },
 
        "Proc_Day_Wise_Coverage" : {
            mjr : false,
            or: false,
            res: true,
            cus: true
        },
 
        "Proc_RM_PM_OrderWise" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
 
 
        "Proc_RM_PM_BufferTrend" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
 
 
        "Proc_Expediting_RM_And_Suppliers" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
 
        "Prod_Enquiry_Response" : {
            mjr : false,
            or: false,
            res: true,
            cus: false
        },
        "Prod_DDQ" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
        "Prod_FullKit_Assignment" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
        "Prod_Dynamic_Release_Management" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
        "Prod_Dept_Wise_BM_Report" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
        "Prod_OverAll_BMReport" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
        "Prod_BM_Trend" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
        "Prod_FOL_Summary" : {
            mjr : false,
            or: false,
            res: true,
            cus: false
        },
        "Prod_STPL_And_FullKits" : {
            mjr : false,
            or: false,
            res: true,
            cus: false
        },
        "Prod_Elapsed_Time" : {
            mjr : false,
            or: false,
            res: true,
            cus: false
        },
        "Prod_Order_At_Risk" : {
            mjr : true,
            or: true,
            res: true,
            cus: false
        },
		
		"Prod_Order_Balance" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
 
        "Poogi_Reason_For_Delayed_Orders" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
 
        "Poogi_OTIF_Analysis" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
 
        "Poogi_OTIF_And_Analysis" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
 
        "Poogi_Lead_Time" : {
            mjr : false,
            or: false,
            res: true,
            cus: true
        },
 
        "Poogi_Top_Failure_Reasons" : {
            mjr : true,
            or: true,
            res: true,
            cus: true
        },
 
        "Poogi_Trend_Of_Failure_Reasons" : {
            mjr : true,
            or: true,
            res: true,
            cus: true
        },
        'Future_Order_Load_Chart': {
            mjr : false,
            or: true,
            res: false,
            cus: true
        }
    }
};