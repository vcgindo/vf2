
export const columnConfigLevel1 = [
    {
        "cc": "plnt",
        "cp": 2,
        "hd": "Plant",
        "v": true,
        "cla": "left",
        "scc": "plnt"
    },
    {
        "cc": "dept",
        "cp": 2,
        "hd": "Department",
        "v": true,
        "cla": "left",
        "scc": "dept"
    },
    {
        "cc": "ccrGrp",
        "cp": 3,
        "hd": "CCR Group",
        "v": true,
        "cla": "left",
        "scc": "ccrGrp"
    },
    {
        "cc": "ccr",
        "cp": 4,
        "hd": "CCR Name",
        "v": true,
        "cla": "left",
        "scc": "ccr"
    },
    {
        "cc": "r_wip",
        "cp": 5,
        "hd": "Released WIP In Days",
        "v": true,
        "cla": "left",
        "scc": "r_wip"
    },
    {
        "cc": "un_fk",
        "cp": 6,
        "hd": "Unreleased Full Kit In Days",
        "v": true,
        "cla": "left",
        "scc": "un_fk"
    },
]

export const columnConfigData = {
    stplTableColumn : [
        { 
            "cc": "ccr_n",
            "cp": 1,
            "hd": "CCR",
            "v": true,
            "cla": "left",
            "scc": "ccr_n"
        },
        { 
            "cc": "exceedDays",
            "cp": 2,
            "hd": "Released WIP (In Days) Exceeding Limit",
            "v": true,
            "cla": "left",
            "scc": "exceedDays"
        },
        { 
            "cc": "days",
            "cp": 3,
            "hd": "Released WIP (In Days)",
            "v": true,
            "cla": "left",
            "scc": "days"
        },
        { 
            "cc": "limit",
            "cp": 4,
            "hd": "Limit",
            "v": true,
            "cla": "left",
            "scc": "limit"
        },
    ],
    fullkitTableColumn : [
        { 
            "cc": "ccr_n",
            "cp": 1,
            "hd": "CCR",
            "v": true,
            "cla": "left",
            "scc": "ccr_n"
        },
        { 
            "cc": "days",
            "cp": 2,
            "hd": "Full Kits In Days",
            "v": true,
            "cla": "left",
            "scc": "days"
        }
    ],
}

export const orderDetailsConfigCol = [
    {
        "cc": "order_details",
        "cp": 0,
        "hd": "Order Details",
        "v": true,
        "cla": "left",
        "scc": "order_details"
    },
    {
        "cc": "or_id",
        "cp": 1,
        "hd": "Order ID",
        "v": true,
        "cla": "left",
        "scc": "or_id"
    },
    {
        "cc": "or_type",
        "cp": 2,
        "hd": "Order Type",
        "v": true,
        "cla": "left",
        "scc": "or_type"
    },
    {
        "cc": "line_item_id",
        "cp": 3,
        "hd": "Line Item Id",
        "v": true,
        "cla": "left",
        "scc": "line_item_id"
    },
    {
        "cc": "fg_code",
        "cp": 4,
        "hd": "FG Code",
        "v": true,
        "cla": "left",
        "scc": "fg_code"
    },
    {
        "cc": "fg_desc",
        "cp": 5,
        "hd": "FG Desc",
        "v": true,
        "cla": "left",
        "scc": "fg_desc"
    },
    {
        "cc": "order_quality",
        "cp": 6,
        "hd": "Order Quality",
        "v": true,
        "cla": "left",
        "scc": "order_quality"
    },
    {
        "cc": "quantity_manufacture",
        "cp": 7,
        "hd": "Quantity Bal. to Mfg.",
        "v": true,
        "cla": "left",
        "scc": "quantity_manufacture"
    },
    {
        "cc": "r_wip",
        "cp": 8,
        "hd": "Release WIP In Days",
        "v": true,
        "cla": "left",
        "scc": "r_wip"
    },
    {
        "cc": "fk",
        "cp": 9,
        "hd": "Full Kit",
        "v": true,
        "cla": "left",
        "scc": "fk"
    },
    {
        "cc": "un_fk",
        "cp": 10,
        "hd": "Unreleased Full Kit In Days",
        "v": true,
        "cla": "left",
        "scc": "un_fk"
    },
    
]

export const rmMaterialConfigCol = [
    {
        "cc": "rm_material",
        "cp": 1,
        "hd": "RM Material",
        "v": true,
        "cla": "left",
        "scc": "rm_material"
    },
    {
        "cc": "rm_code",
        "cp": 2,
        "hd": "RM Code",
        "v": true,
        "cla": "left",
        "scc": "rm_code"
    },
    {
        "cc": "rm_desc",
        "cp": 3,
        "hd": "RM Desc",
        "v": true,
        "cla": "left",
        "scc": "rm_desc"
    },
    {
        "cc": "rm_req",
        "cp": 4,
        "hd": "Required RM",
        "v": true,
        "cla": "left",
        "scc": "rm_req"
    },
    {
        "cc": "rm_avbl",
        "cp": 5,
        "hd": "Available RM",
        "v": true,
        "cla": "left",
        "scc": "rm_avbl"
    },
    {
        "cc": "gap",
        "cp": 6,
        "hd": "Gap",
        "v": true,
        "cla": "left",
        "scc": "gap"
    },
]
