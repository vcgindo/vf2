export interface MTOStore {
    AnalyticsData: any
}

export interface OrderAttribute {
    attribute1: string;
    attribute2: string;
}

export interface LineAttribute {
    lineAttribute1: string;
    lineAttribute2: string;
}

export interface CustomerAttribute {
    customerAttribute1: string;
    customerAttribute2: string;
}

export interface Order {
    oid: string; // Order ID
    lid: string; // Line ID
    ic: string; // Item Code
    id: string; // Item Description
    ig: string; // Item Group
    dd: string; // Due Date (ISO 8601 format string)
    rd: string; // Release Date (ISO 8601 format string)
    oq: number; // Order Quantity
    bs: number; // Batch Size
    fk: number; // Full Kit Available Percentage
    cc: string; // Customer Code
    cn: string; // Customer Name
    bpp: number; // Buffer Penetration Percentage
    clr: string; // Color
    pid: string; // Plant ID
    pnm: string; // Plant Name
    ov: number; // Order Value
    pdb: number; // Production Buffer Size
    pcb: number; // Procurement Buffer Size
    td: string; // Trailing Department
    ccrid: string; // CCR ID
    ccrnm: string; // CCR Name
    ccrgrid: string; // CCR Group ID
    ccrgrnm: string; // CCR Group Name
    soh: number; // Stock On Hand
    sit: number; // Stock In Transit (including Stock in QC)
    po: number; // Open Purchase Orders
    or: number; // Raw Material/PM Shortage
    oa: OrderAttribute[]; // Order Attributes
    la: LineAttribute[]; // Line Attributes
    ca: CustomerAttribute[]; // Customer Attributes
}

export interface DeptWiseOrder {
    BPP: string;
    D_Ag: string;
    Ord_Typ: string;
    Ord_ID: string;
    L_Itm: string;
    Itm_Code: string;
    Itm_Desc: string;
    Ord_Qty: number;
    WIP_O_Hd: number;
    M_Bal: number;
    CCR_Nme: string;
    Cust_Nme: string;
    CRDDate: string;
    DDt: string;
    R_DDt: string;
    Trail_Dpt: string;
    Elap_days: number;
    Attr: string;
    Pl_Nam: string;
    PO_No: string;
    Price: number;
    Itm_Grp: string;
    Att_1: string;
    Att_2: string;
    Att_3: string;
    Att_4: string;
    Cust_Cd: string;
    Rgn: string;
    Cntry: string;
    Rem_Cd: string;
    Lst_Rmrk: string;
    Rmrk_Hstry: string;
}

export interface Filter{
    type:string
    name:string
    attributeName:string
    operator:string
    value: any
    options: string[] | number[]
}

export interface FilterGroup{
    id:string
    label:string
    filters: Filter[]
}

export interface FilterState{
    customers?: FilterGroup
    resources?: FilterGroup
    orders?: FilterGroup
    major?: FilterGroup
    filters?: any
}
