
import { ColDef, ColGroupDef } from "ag-grid-enterprise";
import { ColorsMTO } from "../../Common/Colors";


export const DeptWiseBMReport = (onOpenRemarkHistory: () => void): (ColDef | ColGroupDef)[] => {
    return [

        {
            headerName: "",
            headerCheckboxSelection: false,
            checkboxSelection: true,
            maxWidth: 50,
            floatingFilter: false,
        }
        ,
        {
            headerName: "Default Attributes",
            suppressStickyLabel: true,
            colId: 'Default Attributes',
            openByDefault: true,
            children: [
                { field: 'ec', headerName: '', colId: '', cellRenderer: "customCellRenderer", initialWidth: 80, floatingFilter: false },
                { field: 'ic', headerName: '', colId: '', cellRenderer: "AgeingCellRenderer", initialWidth: 80, floatingFilter: false },
                { field: "BPP", headerName: "BPP", colId: "BPP", cellRenderer: "colorCellRenderer" },
                { field: "D_Ag", headerName: 'Dept Ageing', colId: "Dept Ageing", columnGroupShow: "open" },
                { field: "Ord_Typ", headerName: "Order Type", colId: "Order Type", columnGroupShow: "open" },
                { field: "Ord_ID", headerName: "Order Type", colId: "Order ID", columnGroupShow: "closed" },
                { field: "L_Itm", headerName: "Line Item", colId: "Line Item", columnGroupShow: "closed" },
                { field: "Itm_Code", headerName: "Item Code", colId: "Item Code", columnGroupShow: "closed" },
                { field: "Itm_Desc", headerName: "Item Description", colId: "Item Description", columnGroupShow: "closed" },
                { field: "Ord_Qty", headerName: "Order Quantity", colId: "Order Quantity", columnGroupShow: "closed" },
                { field: "WIP_O_Hd", headerName: "WIP On Hand", colId: "WIP On Hand", columnGroupShow: "closed" },
                { field: "M_Bal", headerName: "Mfg. Balance", colId: "Mfg. Balance", columnGroupShow: "closed" },
                { field: "CCR_Nme", headerName: "CCR Name", colId: "CCR Name", columnGroupShow: "closed" },
                { field: "Cust_Nme", headerName: "Customer Name", colId: "Customer Name", columnGroupShow: "closed" },
                { field: "CRDDate", headerName: "CRDDate", colId: "CRDDate", columnGroupShow: "closed" },
                { field: "DDt", headerName: "Due Date", colId: "Due Date", columnGroupShow: "closed" },
                { field: "R_DDt", headerName: "Release Date", colId: "Release Date", columnGroupShow: "closed" },
                { field: "Trail_Dpt", headerName: "Trailing Department", colId: "Trailing Department", columnGroupShow: "closed" },
            ]
        },
        {
            headerName: "Calculate Attribute",
            suppressStickyLabel: true,
            colId: 'Calculate Attributes',
            openByDefault: true,
            children: [
                { field: "Elap_days", headerName: "Elapsed Days", colId: "Elapsed Days" },
                { field: "Attr", headerName: "Attribute", colId: "Attribute", columnGroupShow: 'closed' },
            ]
        },
        {
            headerName: "Order Attribute",
            suppressStickyLabel: true,
            colId: 'Order Attributes',
            openByDefault: true,
            children: [
                { field: "Pl_Nam", headerName: "Plant Name", colId: "Plant Name" },
                { field: "PO_No", headerName: "PO No.", colId: "Po No.", columnGroupShow: 'closed' },
            ]
        },
        {
            headerName: "Product Attribute",
            suppressStickyLabel: true,
            colId: 'Product Attributes',
            openByDefault: true,
            children: [
                { field: "Price", headerName: "Price", colId: "Price" },
                { field: "Itm_Grp", headerName: "Item Group", colId: "Item Group" },
                { field: "Att_1", headerName: "Attribute 1", colId: "Attribute 1", columnGroupShow: 'closed' },
                { field: "Att_2", headerName: "Attribute 2", colId: "Attribute 2", columnGroupShow: 'closed' },
                { field: "Att_3", headerName: "Attribute 3", colId: "Attribute 3", columnGroupShow: 'closed' },
                { field: "Att_4", headerName: "Attribute 4", colId: "Attribute 4", columnGroupShow: 'closed' },
            ]
        },
        {
            headerName: "Customer Attribute",
            suppressStickyLabel: true,
            colId: 'Customer Attributes',
            openByDefault: true,
            children: [
                { field: "Cust_Cd", headerName: "Customer Code", colId: "Customer Code" },
                { field: "Rgn", headerName: "Region", colId: "Region", columnGroupShow: 'closed' },
                { field: "Cntry", headerName: "Country", colId: "Country", columnGroupShow: 'closed' },
            ]
        }, 
        {
            headerName: "",
            suppressStickyLabel: true,
            openByDefault: false,
            colId: '',
            children: [
                { 
                    field: "Rem_Cd", headerName: "Remark Code", pinned: 'right', colId: "Remark Code", cellRenderer: "TextBoxCellRenderer", cellRendererParams: {
                        visible: {
                            flag: true
                        },

                    }
                },
                {
                    field: "Lst_Rmrk", headerName: "Latest Remark", pinned: 'right', colId: "Latest Remark", cellRenderer: "TextBoxCellRenderer", cellRendererParams: {
                        visible: {
                            flag: false
                        }
                    }
                },
                {
                    field: "Rmrk_Hstry", headerName: "Remark History", pinned: 'right', colId: "Remark History", cellRenderer: "RemarkHistoryRenderer", cellRendererParams: {
                        onClick: onOpenRemarkHistory
                    }
                },
            ]
        }
    ]
};

export const orderDataDropDown: (ColDef)[] = [
    { field: "FG_Cod", headerName: 'FG Code', rowGroup: true, hide: true },
    { field: "Lvl", rowGroup: true, hide: true },
    { field: "Rqrment", headerName: 'Requirement' },
    { field: "Stck", headerName: 'Stock' },
    { field: "WIP", headerName: 'WIP' },
    { field: 'Gp', headerName: 'Gap' }
]
export const orderStatus: (ColDef | ColGroupDef)[] = [
    {
        headerName: "Order ID",
        field: 'ord_id',
        colId: 'ord_id',
    },
    {
        headerName: "Line Item",
        field: 'l_itm',
        colId: 'l_itm',

    },
    {
        headerName: "Quantity",
        field: 'qty',
        colId: 'qty',
    },
    {
        headerName: 'Department 1',
        children: [
            {
                headerName: 'WIP on hand',
                field: 'wipoh',
                colId: 'wipoh'
            },
            {
                headerName: 'Balance to manufacture',
                field: 'btm',
                colId: 'btm',
            },
        ]
    },
    {
        headerName: 'Department 2',
        children: [
            {
                headerName: 'WIP on hand',
                field: 'wipoh',
                colId: 'wipoh'
            },
            {
                headerName: 'Balance to manufacture',
                field: 'btm',
                colId: 'btm',
            },
        ]
    },
    {
        headerName: 'Department 3',
        children: [
            {
                headerName: 'WIP on hand',
                field: 'wipoh',
                colId: 'wipoh'
            },
            {
                headerName: 'Balance to manufacture',
                field: 'btm',
                colId: 'btm',
            },
        ]
    }
]

export const orderStatusData = [
    {
        "ord_id": 1,
        "l_itm": "Item A",
        "qty": 5,
        "wipoh": 12,
        "btm": 15
    },
    {
        "ord_id": 2,
        "l_itm": "Item B",
        "qty": 8,
        "wipoh": 12,
        "btm": 18
    },
    {
        "ord_id": 3,
        "l_itm": "Item C",
        "qty": 3,
        "wipoh": 8,
        "btm": 10
    },
    {
        "ord_id": 4,
        "l_itm": "Item D",
        "qty": 6,
        "wipoh": 15,
        "btm": 20
    },
    {
        "ord_id": 5,
        "l_itm": "Item E",
        "qty": 4,
        "wipoh": 9,
        "btm": 12
    },
    {
        "ord_id": 6,
        "l_itm": "Item F",
        "qty": 7,
        "wipoh": 11,
        "btm": 16
    },
    {
        "ord_id": 7,
        "l_itm": "Item G",
        "qty": 2,
        "wipoh": 7,
        "btm": 9
    },
    {
        "ord_id": 8,
        "l_itm": "Item H",
        "qty": 9,
        "wipoh": 18,
        "btm": 25
    },
    {
        "ord_id": 9,
        "l_itm": "Item I",
        "qty": 5,
        "wipoh": 13,
        "btm": 17
    },
    {
        "ord_id": 10,
        "l_itm": "Item J",
        "qty": 4,
        "wipoh": 10,
        "btm": 14
    }
]


export const ElapsedTime: (ColDef | ColGroupDef)[] = [
    {
        headerName: "",
        field: 'time',
        colId: 'time',
    },
    {
        headerName: 'Department 1',
        field: '1',
        colId: '1'

    },
    {
        headerName: 'Department 2',
        field: '2',
        colId: '2'

    },
    {
        headerName: 'Department 3',
        field: '3',
        colId: '3'
    }
]

export const ElapsedTimeData = [
    {
        "time": "In Time",
        "dpt1": '1 Feb 2024, 10.00am',
        "dpt2": '2 Feb 2024, 10.00am',
        "dpt3": '16 Feb 2024, 10.00am',
    },
    {
        "time": "Out Time",
        "dpt1": '2 Feb 2024, 11.00am',
        "dpt2": '5 Feb 2024, 10.00am',
        "dpt3": '21 Feb 2024, 10.00am',
    },
    {
        "time": "Elapsed Time",
        "dpt1": '3 Feb 2024, 12.00pm',
        "dpt2": '11 Feb 2024, 10.00am',
        "dpt3": '29 Feb 2024, 10.00am',
    },
]


export const AgieingTime: (ColDef | ColGroupDef)[] = [
    {
        headerName: "Order ID",
        field: 'o_id',
        colId: 'o_id',
    },
    {
        headerName: 'Line Item',
        field: 'L_itm',
        colId: 'L_itm'

    },
    {
        headerName: 'Batch No.',
        field: 'btch_no',
        colId: 'btch_no'

    },
    {
        headerName: 'Department',
        field: 'dpt',
        colId: 'dpt'
    },
    {
        headerName: 'Ageing',
        field: 'agng',
        colId: 'agng',
        cellStyle: {
            'color': ColorsMTO.Pink.code
        }
    }
]

export const ageingData = [
    {
        "o_id": 1,
        "L_itm": "Item 1",
        "btch_no": "B001",
        "dpt": "Sales",
        "agng": 10
    },
    {
        "o_id": 2,
        "L_itm": "Item 2",
        "btch_no": "B002",
        "dpt": "Marketing",
        "agng": 5
    },
    {
        "o_id": 3,
        "L_itm": "Item 3",
        "btch_no": "B003",
        "dpt": "Operations",
        "agng": 15
    },
    {
        "o_id": 4,
        "L_itm": "Item 4",
        "btch_no": "B004",
        "dpt": "Finance",
        "agng": 8
    }
]



export const deptwiseBMReportData = [
    {
        "BPP": "Red",
        "D_Ag": "Dept Ageing 1",
        "Ord_Typ": "Order Type 1",
        "Ord_ID": "Order ID 1",
        "L_Itm": "Line Item 1",
        "Itm_Code": "Item Code 1",
        "Itm_Desc": "Item Description 1",
        "Ord_Qty": 10,
        "WIP_O_Hd": 5,
        "M_Bal": 8,
        "CCR_Nme": "CCR Name 1",
        "Cust_Nme": "Customer Name 1",
        "CRDDate": "2024-07-14",
        "DDt": "2024-07-20",
        "R_DDt": "2024-07-15",
        "Trail_Dpt": "Trailing Department 1",
        "Elap_days": 5,
        "Attr": "Attribute 1",
        "Pl_Nam": "Plant Name 1",
        "PO_No": "PO No. 1",
        "Price": 20,
        "Itm_Grp": "Item Group 1",
        "Att_1": "Attribute 1-1",
        "Att_2": "Attribute 1-2",
        "Att_3": "Attribute 1-3",
        "Att_4": "Attribute 1-4",
        "Cust_Cd": "Customer Code 1",
        "Rgn": "Region 1",
        "Cntry": "Country 1",
        "Rem_Cd": "Remark Code 1",
        "Lst_Rmrk": "Latest Remark 1",
        "Rmrk_Hstry": "Remark History 1",
        "children": [
            {

                "FG_Cod": "A123",
                "Lvl": "L0",
                "Rqrment": "Requirement 1",
                "Stck": 100,
                "WIP": 50,
                "Gp": 50,
                "children": [
                    {
                        "FG_Cod": "A124",
                        "Lvl": "L1",
                        "Rqrment": "Requirement 1",
                        "Stck": 100,
                        "WIP": 50,
                        "Gp": 50,
                        "children": [
                            {
                                "FG_Cod": "A124",
                                "Lvl": "L2",
                                "Rqrment": "Requirement 1",
                                "Stck": 100,
                                "WIP": 50,
                                "Gp": 50,
                                "children": [
                                    {
                                        "FG_Cod": "A124",
                                        "Lvl": "L3",
                                        "Rqrment": "Requirement 1",
                                        "Stck": 100,
                                        "WIP": 50,
                                        "Gp": 50,
                                        "children": [
                                            {
                                                "FG_Cod": "A124",
                                                "Lvl": "L4",
                                                "Rqrment": "Requirement 1",
                                                "Stck": 100,
                                                "WIP": 50,
                                                "Gp": 50,
                                                "children": [
                                                    {
                                                        "FG_Cod": "A124",
                                                        "Lvl": "L5",
                                                        "Rqrment": "Requirement 1",
                                                        "Stck": 100,
                                                        "WIP": 50,
                                                        "Gp": 50,
                                                        "children": [
                                                            {
                                                                "FG_Cod": "A124",
                                                                "Lvl": "L6",
                                                                "Rqrment": "Requirement 1",
                                                                "Stck": 100,
                                                                "WIP": 50,
                                                                "Gp": 50,
                                                                "children": [
                                                                    {
                                                                        "FG_Cod": "A124",
                                                                        "Lvl": "L7",
                                                                        "Rqrment": "Requirement 1",
                                                                        "Stck": 100,
                                                                        "WIP": 50,
                                                                        "Gp": 50,
                                                                        "children": [
                                                                            {
                                                                                "FG_Cod": "A124",
                                                                                "Lvl": "L8",
                                                                                "Rqrment": "Requirement 1",
                                                                                "Stck": 100,
                                                                                "WIP": 50,
                                                                                "Gp": 50,
                                                                            }
                                                                        ]
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ],
            },
            {
                "FG_Cod": "B125",
                "Lvl": "L0",
                "Rqrment": "Requirement 1",
                "Stck": 100,
                "WIP": 50,
                "Gp": 50,

            },
            {
                "FG_Cod": "B126",
                "Lvl": "L0",
                "Rqrment": "Requirement 1",
                "Stck": 100,
                "WIP": 50,
                "Gp": 50,

            },
            {
                "FG_Cod": "B127",
                "Lvl": "L0",
                "Rqrment": "Requirement 1",
                "Stck": 100,
                "WIP": 50,
                "Gp": 50,

            }
        ]
    },
    {
        "BPP": "Value 2",
        "D_Ag": "Dept Ageing 2",
        "Ord_Typ": "Order Type 2",
        "Ord_ID": "Order ID 2",
        "L_Itm": "Line Item 2",
        "Itm_Code": "Item Code 2",
        "Itm_Desc": "Item Description 2",
        "Ord_Qty": 15,
        "WIP_O_Hd": 3,
        "M_Bal": 12,
        "CCR_Nme": "CCR Name 2",
        "Cust_Nme": "Customer Name 2",
        "CRDDate": "2024-07-15",
        "DDt": "2024-07-21",
        "R_DDt": "2024-07-16",
        "Trail_Dpt": "Trailing Department 2",
        "Elap_days": 7,
        "Attr": "Attribute 2",
        "Pl_Nam": "Plant Name 2",
        "PO_No": "PO No. 2",
        "Price": 25,
        "Itm_Grp": "Item Group 2",
        "Att_1": "Attribute 2-1",
        "Att_2": "Attribute 2-2",
        "Att_3": "Attribute 2-3",
        "Att_4": "Attribute 2-4",
        "Cust_Cd": "Customer Code 2",
        "Rgn": "Region 2",
        "Cntry": "Country 2",
        "Rem_Cd": "Remark Code 2",
        "Lst_Rmrk": "Latest Remark 2",
        "Rmrk_Hstry": "Remark History 2",
        "children": [
            {
                "FG_Cod": "B123",
                "Lvl": "L0",
                "Rqrment": "Requirement 1",
                "Stck": 100,
                "WIP": 50,
                "Gp": 50,
                "children": [
                    {
                        "FG_Cod": "B123",
                        "Lvl": "L1",
                        "Rqrment": "Requirement 2",
                        "Stck": 150,
                        "WIP": 70,
                        "Gp": 80
                    },
                ]
            },

        ]
    },
    {
        "BPP": "Value 3",
        "D_Ag": "Dept Ageing 3",
        "Ord_Typ": "Order Type 3",
        "Ord_ID": "Order ID 3",
        "L_Itm": "Line Item 3",
        "Itm_Code": "Item Code 3",
        "Itm_Desc": "Item Description 3",
        "Ord_Qty": 20,
        "WIP_O_Hd": 8,
        "M_Bal": 5,
        "CCR_Nme": "CCR Name 3",
        "Cust_Nme": "Customer Name 3",
        "CRDDate": "2024-07-16",
        "DDt": "2024-07-22",
        "R_DDt": "2024-07-17",
        "Trail_Dpt": "Trailing Department 3",
        "Elap_days": 10,
        "Attr": "Attribute 3",
        "Pl_Nam": "Plant Name 3",
        "PO_No": "PO No. 3",
        "Price": 30,
        "Itm_Grp": "Item Group 3",
        "Att_1": "Attribute 3-1",
        "Att_2": "Attribute 3-2",
        "Att_3": "Attribute 3-3",
        "Att_4": "Attribute 3-4",
        "Cust_Cd": "Customer Code 3",
        "Rgn": "Region 3",
        "Cntry": "Country 3",
        "Rem_Cd": "Remark Code 3",
        "Lst_Rmrk": "Latest Remark 3",
        "Rmrk_Hstry": "Remark History 3",
        "children": [
            {
                "FG_Cod": "B456",
                "Lvl": "L0",
                "Rqrment": "Requirement 3",
                "Stck": 120,
                "WIP": 60,
                "Gp": 60,
                "children": [
                    {
                        "FG_Cod": "B456",
                        "Lvl": "L1",
                        "Rqrment": "Requirement 4",
                        "Stck": 90,
                        "WIP": 30,
                        "Gp": 60
                    },
                ]
            },

        ]
    },
    {
        "BPP": "Value 4",
        "D_Ag": "Dept Ageing 4",
        "Ord_Typ": "Order Type 4",
        "Ord_ID": "Order ID 4",
        "L_Itm": "Line Item 4",
        "Itm_Code": "Item Code 4",
        "Itm_Desc": "Item Description 4",
        "Ord_Qty": 25,
        "WIP_O_Hd": 10,
        "M_Bal": 7,
        "CCR_Nme": "CCR Name 4",
        "Cust_Nme": "Customer Name 4",
        "CRDDate": "2024-07-17",
        "DDt": "2024-07-23",
        "R_DDt": "2024-07-18",
        "Trail_Dpt": "Trailing Department 4",
        "Elap_days": 12,
        "Attr": "Attribute 4",
        "Pl_Nam": "Plant Name 4",
        "PO_No": "PO No. 4",
        "Price": 35,
        "Itm_Grp": "Item Group 4",
        "Att_1": "Attribute 4-1",
        "Att_2": "Attribute 4-2",
        "Att_3": "Attribute 4-3",
        "Att_4": "Attribute 4-4",
        "Cust_Cd": "Customer Code 4",
        "Rgn": "Region 4",
        "Cntry": "Country 4",
        "Rem_Cd": "Remark Code 4",
        "Lst_Rmrk": "Latest Remark 4",
        "Rmrk_Hstry": "Remark History 4",
        "children": [
            {
                "FG_Cod": "C123",
                "Lvl": "L0",
                "Rqrment": "Requirement 1",
                "Stck": 100,
                "WIP": 50,
                "Gp": 50,
                "children": [
                    {
                        "FG_Cod": "C123",
                        "Lvl": "L1",
                        "Rqrment": "Requirement 2",
                        "Stck": 150,
                        "WIP": 70,
                        "Gp": 80
                    },
                ]
            },

        ]
    },
    {
        "BPP": "Value 5",
        "D_Ag": "Dept Ageing 5",
        "Ord_Typ": "Order Type 5",
        "Ord_ID": "Order ID 5",
        "L_Itm": "Line Item 5",
        "Itm_Code": "Item Code 5",
        "Itm_Desc": "Item Description 5",
        "Ord_Qty": 30,
        "WIP_O_Hd": 15,
        "M_Bal": 9,
        "CCR_Nme": "CCR Name 5",
        "Cust_Nme": "Customer Name 5",
        "CRDDate": "2024-07-18",
        "DDt": "2024-07-24",
        "R_DDt": "2024-07-19",
        "Trail_Dpt": "Trailing Department 5",
        "Elap_days": 15,
        "Attr": "Attribute 5",
        "Pl_Nam": "Plant Name 5",
        "PO_No": "PO No. 5",
        "Price": 40,
        "Itm_Grp": "Item Group 5",
        "Att_1": "Attribute 5-1",
        "Att_2": "Attribute 5-2",
        "Att_3": "Attribute 5-3",
        "Att_4": "Attribute 5-4",
        "Cust_Cd": "Customer Code 5",
        "Rgn": "Region 5",
        "Cntry": "Country 5",
        "Rem_Cd": "Remark Code 5",
        "Lst_Rmrk": "Latest Remark 5",
        "Rmrk_Hstry": "Remark History 5",
        "children": [
            {
                "FG_Cod": "D123",
                "Lvl": "L0",
                "Rqrment": "Requirement 1",
                "Stck": 100,
                "WIP": 50,
                "Gp": 50,
                "children": [
                    {
                        "FG_Cod": "D123",
                        "Lvl": "L1",
                        "Rqrment": "Requirement 2",
                        "Stck": 150,
                        "WIP": 70,
                        "Gp": 80
                    },
                ]
            },

        ]
    }

]


export const RemarkHistoryData = [
    {
        'added_by': 'fristan',
        'remark': 'enter the last remark data',
        'added_on': '2023-12-23'
    },
    {
        'added_by': 'fristan',
        'remark': 'enter the  remark 1 data',
        'added_on': '2023-12-24'
    },
    {
        'added_by': 'fristan',
        'remark': 'enter the remark 2 data',
        'added_on': '2023-12-24'
    },
    {
        'added_by': 'Tarun',
        'remark': 'enter the remark 3 data',
        'added_on': '2023-12-23'
    },
    {
        'added_by': 'Tarun',
        'remark': 'enter the remark 4 data',
        'added_on': '2023-12-24'
    },
    {
        'added_by': 'Tarun',
        'remark': 'enter the remark 5 data',
        'added_on': '2023-12-24'
    }
]


// const gridOptionForMapping : GridOptions = {
//     rowData: "rowData",
//     columnDef: [
//         { field: "FG_Code", cellRenderer: "agGroupCellRenderer" },
//         { field: "Lvl" },
//         { field: "Rqrmtn" },
//         { field: "stck" },
//         { field: "wip" },
//         { field: "gp" }
//     ],
//     defaultColDef: {
//       flex: 1,
//     },
//     groupDefaultExpanded: 1,
//     masterDetail: true,
//     detailCellRendererParams: {
//       // level 2 grid options
//       detailGridOptions: {
//         columnDef: [
//             { field: "FG_Code", cellRenderer: "agGroupCellRenderer" },
//             { field: "Lvl" },
//             { field: "Rqrmtn" },
//             { field: "stck" },
//             { field: "wip" },
//             { field: "gp" }
//         ],
//         defaultColDef: {
//           flex: 1,
//         },
//         groupDefaultExpanded: 1,
//         masterDetail: true,
//         detailRowHeight: 240,
//         detailCellRendererParams: {
//           // level 3 grid options
//           detailGridOptions: {
//             columnDef: [
//                 { field: "FG_Code", cellRenderer: "agGroupCellRenderer" },
//                 { field: "Lvl" },
//                 { field: "Rqrmtn" },
//                 { field: "stck" },
//                 { field: "wip" },
//                 { field: "gp" }
//             ],
//             defaultColDef: {
//               flex: 1,
//             },
//           },
//           getDetailRowData: (params) => {
//             params.successCallback(params.data.children);
//           },
//         } as IDetailCellRendererParams,
//       },
//       getDetailRowData: (params) => {
//         params.successCallback(params.data.children);
//       },
//     } as IDetailCellRendererParams,
//   }; 














