import { MDMMasterState } from "../VectorFlow/types/MDM";
import { generateRandomId } from "../helpers/utils";

export const mockMasterData: any = {
  recordCount: 345,
  data: [
    {
      SKUSrNo: 1,
      SKUCode: "Q1231231DE12",
      SKUName: "Text Description",
      SKUAttr1: "ABC",
      SKUAttr2: "Group A",
      SKUAttr3: "PTH",
      SKUAttr4: 50,
      SKUAttr5: "Arrow New",
      SKUAttr6: "Red",
      SKUAttr7: 25,
      SKUAttr8: "mm",
      SKUAttr9: 35,
      SKUAttr10: "ABC",
      SKUAttr11: "SubCategory",
      SKUAttr12: "2022-11-08",
      SKUAttr13: "Dymmy Value",
      SKUAttr14: "ABC Group",
      SKUAttr15: "Dummy Value",
      SKUAttr16: "mm",
    },
    {
      SKUSrNo: 2,
      SKUCode: "Q1231231FG34",
      SKUName: "Text Description",
      SKUAttr1: "ABC",
      SKUAttr2: "Group A",
      SKUAttr3: "PTH",
      SKUAttr4: 50,
      SKUAttr5: "Arrow New",
      SKUAttr6: "Red",
      SKUAttr7: 25,
      SKUAttr8: "mm",
      SKUAttr9: 35,
      SKUAttr10: "ABC",
      SKUAttr11: "SubCategory",
      SKUAttr12: "2022-11-08",
      SKUAttr13: "Dymmy Value",
      SKUAttr14: "ABC Group",
      SKUAttr15: "Dummy Value",
      SKUAttr16: "mm",
    },
    {
      SKUSrNo: 3,
      SKUCode: "Q1231231FG34",
      SKUName: "Text Description",
      SKUAttr1: "ABC",
      SKUAttr2: "Group A",
      SKUAttr3: "PTH",
      SKUAttr4: 50,
      SKUAttr5: "Arrow New",
      SKUAttr6: "Red",
      SKUAttr7: 25,
      SKUAttr8: "mm",
      SKUAttr9: 35,
      SKUAttr10: "ABC",
      SKUAttr11: "SubCategory",
      SKUAttr12: "2022-11-08",
      SKUAttr13: "Dymmy Value",
      SKUAttr14: "ABC Group",
      SKUAttr15: "Dummy Value",
      SKUAttr16: "mm",
    },
  ],
};

export const MasterData:MDMMasterState[] = [
    { 
      id: 1,
      name: 'SKU', 
      fields:[
          {
            displayName:'SKU Code',
            key:"sku_code",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName:'SKU Name',
            key:"sku_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName: "Item Category Code",
            key: "item_category_code",
            visible:false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
      ],
      colDefs:[],
      progress:'default',
      filters:[
          {
            id:generateRandomId(),
            masterId:1,
            field:'',
            operator:'',
            text:''
          }
      ],
      rowData:[],
      isChecked:true
    },
    { 
      id: 2,
      name: 'Location', 
      fields:[
          {
            displayName:'Location Code',
            key:"location_code",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName:'Location Name',
            key:"location_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName: "c1",
            key: "LocAttr1",
            visible: false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
      ],
      colDefs:[],
      progress:'default',
      filters:[
        {
          id:generateRandomId(),
          masterId:2,
          field:'',
          operator:'',
          text:''
        }
    ],
      rowData:[],
      isChecked:true
    },
    { 
      id: 3,
      name: 'SKU Location', 
      fields:[
          {
            displayName:'SKU Code',
            key:"sku_code",
            visible:true, isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName:'SKU Name',
            key:"sku_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName: "Segment",
            key: "SKULocAttr1",
            visible: false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
      ],
      colDefs:[],
      progress:'default',
      filters:[
        {
          id:generateRandomId(),
          masterId:3,
          field:'',
          operator:'',
          text:''
        }
    ],
      rowData:[] ,
      isChecked:true
    },
    { 
      id: 11,
      name: 'Seasonality', 
      fields:[
          {
            displayName:'SKU Code',
            key:"sku_code",
            visible:true, isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName:'SKU Name',
            key:"sku_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName: "Segment",
            key: "SKULocAttr1",
            visible: false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
      ],
      colDefs:[],
      progress:'default',
      filters:[
        {
          id:generateRandomId(),
          masterId:3,
          field:'',
          operator:'',
          text:''
        }
    ],
      rowData:[] ,
      isChecked:true

    },
    { 
      id: 7,
      name: 'Phase In Phase Out', 
      fields:[
          {
            displayName:'SKU Code',
            key:"sku_code",
            visible:true, isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName:'SKU Name',
            key:"sku_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName: "Segment",
            key: "SKULocAttr1",
            visible: false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
      ],
      colDefs:[],
      progress:'default',
      filters:[
        {
          id:generateRandomId(),
          masterId:3,
          field:'',
          operator:'',
          text:''
        }
    ],
      rowData:[] ,
      isChecked:true

    },
  ];

  export const MasterDataWithSubmittedMaster:MDMMasterState[] =  [
    { 
      id: 1,
      name: 'SKU', 
      fields:[
          {
            displayName:'SKU Code',
            key:"sku_code",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName:'SKU Name',
            key:"sku_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName: "Item Category Code",
            key: "item_category_code",
            visible:false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
      ],
      colDefs:[],
      progress:'submitted',
      filters:[
          {
            id:generateRandomId(),
            masterId:1,
            field:'',
            operator:'',
            text:''
          }
      ],
      rowData:[],
      isChecked:true

    },
    { 
      id: 2,
      name: 'Location', 
      fields:[
          {
            displayName:'Location Code',
            key:"location_code",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName:'Location Name',
            key:"location_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName: "c1",
            key: "LocAttr1",
            visible: false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
      ],
      colDefs:[],
      progress:'default',
      filters:[
        {
          id:generateRandomId(),
          masterId:2,
          field:'',
          operator:'',
          text:''
        }
    ],
      rowData:[],
      isChecked:true

    },
    { 
      id: 3,
      name: 'SKU Location', 
      fields:[
          {
            displayName:'SKU Code',
            key:"sku_code",
            visible:true, isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName:'SKU Name',
            key:"sku_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true, 
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName: "Segment",
            key: "SKULocAttr1",
            visible: false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
      ],
      colDefs:[],
      progress:'default',
      filters:[
        {
          id:generateRandomId(),
          masterId:3,
          field:'',
          operator:'',
          text:''
        }
    ],
      rowData:[] ,
      isChecked:true

    },
    { 
      id: 11,
      name: 'Seasonality', 
      fields:[
          {
            displayName:'SKU Code',
            key:"sku_code",
            visible:true, isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName:'SKU Name',
            key:"sku_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
          {
            displayName: "Segment",
            key: "SKULocAttr1",
            visible: false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
            dataType:'String'
          },
      ],
      colDefs:[],
      progress:'default',
      filters:[
        {
          id:generateRandomId(),
          masterId:3,
          field:'',
          operator:'',
          text:''
        }
    ],
      rowData:[],
      isChecked:true
 
    },
    { 
      id: 7,
      name: 'Phase In Phase Out', 
      fields:[
          {
            displayName:'SKU Code',
            key:"sku_code",
            visible:true, isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
             dataType:'String'
          },
          {
            displayName:'SKU Name',
            key:"sku_name",
            visible:true,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
             dataType:'String'
          },
          {
            displayName: "Segment",
            key: "SKULocAttr1",
            visible: false,
            isAdd:true,
            isDownload:true,
            isEdit:true,
            col_Position:'1',
            isApplicable:true,
             dataType:'String'
          },
      ],
      colDefs:[],
      progress:'default',
      filters:[
        {
          id:generateRandomId(),
          masterId:3,
          field:'',
          operator:'',
          text:''
        }
    ],
      rowData:[] ,
      isChecked:true

    },
  ]

  export const getAllDraftsMock:any = {
    recordCount: null,
    data: [
        {
            ActionType:2,
            DraftId: "1121423100749",
            Masters: " SKU",
            userid: "1",
            LastModifiedDateTime: "2023-12-14T10:07:49",
            SearchKeys: "SKU"
        }
    ],
    status: 200,
    msg: "Data fetched successfully"
}

export const getDraftByIdMockData:any = {
  recordCount: null,
  data: [
      {
          MasterId: 1,
          Status: 0,
          GridState: "[{\"field\":\"SKUCode\",\"colId\":\"SKUCode\",\"headerName\":\"SKU Code\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"SKUDescription\",\"colId\":\"SKUDescription\",\"headerName\":\"SKU Name\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c1\",\"colId\":\"c1\",\"headerName\":\"STYLE CODE\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c2\",\"colId\":\"c2\",\"headerName\":\"Programme\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c3\",\"colId\":\"c3\",\"headerName\":\"Type\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c4\",\"colId\":\"c4\",\"headerName\":\"Style status\",\"hide\":true,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c5\",\"colId\":\"c5\",\"headerName\":\"IMPORT\",\"hide\":true,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c6\",\"colId\":\"c6\",\"headerName\":\"Colour\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c7\",\"colId\":\"c7\",\"headerName\":\"Used in FG Codes\",\"hide\":true,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c8\",\"colId\":\"c8\",\"headerName\":\"SIZE\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c9\",\"colId\":\"c9\",\"headerName\":\"EAN\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c10\",\"colId\":\"c10\",\"headerName\":\"UoM\",\"hide\":true,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c11\",\"colId\":\"c11\",\"headerName\":\"MRP\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c12\",\"colId\":\"c12\",\"headerName\":\"BRAND\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c13\",\"colId\":\"c13\",\"headerName\":\"SUB BRAND\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c14\",\"colId\":\"c14\",\"headerName\":\"CATEGORY\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1},{\"field\":\"c15\",\"colId\":\"c15\",\"headerName\":\"SEASON\",\"hide\":false,\"minWidth\":180,\"floatingFilter\":true,\"filter\":\"agMultiColumnFilter\",\"cellStyle\":{\"text-align\":\"center\"},\"flex\":1}]"
      }
  ],
  status: 200,
  msg: "Data fetched successfully"
}

export const getDraftCountMockData:any = {
    recordCount: "[{\"masterid\":1,\"recordCount\":7}]",
    data: null,
    status: 200,
    msg: null,
    errorCount: null,
    error: null,
    conflictErrorCount: null,
    conflictError: null
}

export const getTaskCountMockData:any = {
  recordCount: "[{\"masterid\":1,\"recordCount\":7}]",
  data: null,
  status: 200,
  msg: null,
  errorCount: null,
  error: null,
  conflictErrorCount: null,
  conflictError: null
}

export const approveTaskMockData:any = {
  recordCount: "",
  data: null,
  status: 200,
  msg: "Task Approved Successfully.",
  errorCount: null,
  error: null,
  conflictErrorCount: null,
  conflictError: null
}

export const getMasterUIConfigurationMockData:any = {
  recordCount: "7",
  data: [
      {
          id: "1",
          name: "SKUMaster",
          fields: [
            {
              displayName: "SKUCode",
              key: "sc",
              visible: true,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "Description",
              key: "sd",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "ElephantOrderCapping",
              key: "ec",
              visible: true,
              isAdd: true,
              isEdit: false,
              isDownload: true
            },
            {
              displayName: "Weight",
              key: "wt",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "Volume",
              key: "vm",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c1",
              key: "c1",
              visible: true,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c2",
              key: "c2",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c3",
              key: "c3",
              visible: true,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c4",
              key: "c4",
              visible: true,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c5",
              key: "c5",
              visible: true,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c6",
              key: "c6",
              visible: true,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c7",
              key: "c7",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c8",
              key: "c8",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c9",
              key: "c9",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c10",
              key: "c10",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c11",
              key: "c11",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c12",
              key: "c12",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c13",
              key: "c13",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c14",
              key: "c14",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            },
            {
              displayName: "c15",
              key: "c15",
              visible: false,
              isAdd: true,
              isEdit: true,
              isDownload: true
            }
          ]
      },
  ],
  status: 200,
  msg: null
}


export const getTaskPendingForReviewMockData = {
  recordCount: null,
  data: [
      {
         TaskID: "1_20231206175429",
          PendingSince: "2023-12-06T17:59:01.667",
          TaskName: "M_SKU",
          Approver: "Approver1,Approver2",
          Requester: "Admin",
          TaskStatus: "Pending",
          Approvers: [
              {
                 TaskID: "1_20231206175429",
                  PendingSince: "2023-12-06T17:59:01.667",
                  TaskName: "M_SKU",
                  Approver: "Approver1",
                  Requester: "Admin",
                  TaskStatus: "Pending",
                  ApproverId: "1"
              },
              {
                 TaskID: "1_20231206175429",
                  PendingSince: "2023-12-06T17:59:01.667",
                  TaskName: "M_SKU",
                  Approver: "Approver2",
                  Requester: "Admin",
                  TaskStatus: "Pending",
                  ApproverId: "2"
              }
          ]
      },
      {
         TaskID: "1_20231206182017",
          PendingSince: "2023-12-06T18:20:36.320",
          TaskName: "M_SKU",
          Approver: "Approver2",
          Requester: "Admin",
          TaskStatus: "Pending",
          Approvers: [
              {
                 TaskID: "1_20231206182017",
                  PendingSince: "2023-12-06T18:20:36.320",
                  TaskName: "M_SKU",
                  Approver: "Approver1",
                  Requester: "Admin",
                  TaskStatus: "Pending",
                  ApproverId: "1"
              },
              {
                 TaskID: "1_20231206182017",
                  PendingSince: "2023-12-06T18:20:36.320",
                  TaskName: "M_SKU",
                  Approver: "Approver2",
                  Requester: "Admin",
                  TaskStatus: "Pending",
                  ApproverId: "2"
              }
          ]
      },
      {
         TaskID: "1_202312061821491222",
          PendingSince: "2023-12-06T18:20:36.320",
          TaskName: "M_SKU",
          Approver: "Approver1,Approver2",
          Requester: "Admin",
          TaskStatus: "Pending",
          Approvers: [
              {
                 TaskID: "1_202312061821491222",
                  PendingSince: "2023-12-06T18:20:36.320",
                  TaskName: "M_SKU",
                  Approver: "Approver1",
                  Requester: "Admin",
                  TaskStatus: "Pending",
                  ApprovedDate: "15/12/2023 01:51 AM",
                  ApproverId: "1"
              },
              {
                 TaskID: "1_202312061821491222",
                  PendingSince: "2023-12-06T18:20:36.320",
                  TaskName: "M_SKU",
                  Approver: "Approver2",
                  Requester: "Admin",
                  TaskStatus: "Pending",
                  ApproverId: "2"
              }
          ]
      },
      {
         TaskID: "1_20231206182149",
          PendingSince: "2023-12-06T18:21:59.460",
          TaskName: "M_SKU",
          Approver: "Approver1,Approver2",
          Requester: "Admin",
          TaskStatus: "Pending",
          Approvers: [
              {
                 TaskID: "1_20231206182149",
                  PendingSince: "2023-12-06T18:21:59.460",
                  TaskName: "M_SKU",
                  Approver: "Approver1",
                  Requester: "Admin",
                  TaskStatus: "Partially Approved - DB update Pending",
                  ApprovedDate: "Dec 12 2023 12:15PM",
                  ApproverId: "1"
              },
              {
                 TaskID: "1_20231206182149",
                  PendingSince: "2023-12-06T18:21:59.460",
                  TaskName: "M_SKU",
                  Approver: "Approver2",
                  Requester: "Admin",
                  TaskStatus: "Partially Approved - DB update Pending",
                  ApprovedDate: "Dec 12 2023 12:15PM",
                  ApproverId: "2"
              }
          ]
      },
      {
         TaskID: "1_20231207113016",
          PendingSince: "2023-12-07T11:34:47.813",
          TaskName: "M_LOC",
          Approver: "Approver1",
          Requester: "Admin",
          TaskStatus: "Pending",
          Approvers: [
              {
                 TaskID: "1_20231207113016",
                  PendingSince: "2023-12-07T11:34:47.813",
                  TaskName: "M_LOC",
                  Approver: "Approver1",
                  Requester: "Admin",
                  TaskStatus: "Pending",
                  ApproverId: "1"
              },
              {
                 TaskID: "1_20231207113016",
                  PendingSince: "2023-12-07T11:34:47.813",
                  TaskName: "M_LOC",
                  Approver: "Approver2",
                  Requester: "Admin",
                  TaskStatus: "Pending",
                  ApproverId: "NA"
              }
          ]
      },
      {
         TaskID: "1_20231207113620",
          PendingSince: "2023-12-07T11:36:24.930",
          TaskName: "M_LOC",
          Approver: "Approver1",
          Requester: "Admin",
          TaskStatus: "Pending",
          Approvers: [
              {
                 TaskID: "1_20231207113620",
                  PendingSince: "2023-12-07T11:36:24.930",
                  TaskName: "M_LOC",
                  Requester: "Admin",
                  TaskStatus: "Pending",
                  ApproverId: "NA"
              },
              {
                 TaskID: "1_20231207113620",
                  PendingSince: "2023-12-07T11:36:24.930",
                  TaskName: "M_LOC",
                  Approver: "Approver1",
                  Requester: "Admin",
                  TaskStatus: "Approved - DB Updated",
                  ApproverId: "1"
              }
          ]
      }
  ],
  status: 200,
  msg: null
}

export const getTaskDetailsMockData = {
  recordCount: null,
  data: [
      {
          MasterId: 1,
          data: [
              {
                  "new": "{\"SKUCode\":\"X9I689125STXL001\",\"SKUDescription\":\"ksls\",\"c1\":\"X9I689125STXL\",\"c2\":\"XL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}",
                  "old": "{\"SKUCode\":\"X9I689125STXL001\",\"SKUDescription\":\"ksls      \",\"c1\":\"X9I689125STXL\",\"c2\":\"XL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}"
              },
              {
                "new": "{\"SKUCode\":\"X9I689125STXL001\",\"SKUDescription\":\"ksls\",\"c1\":\"X9I689125STXL\",\"c2\":\"XL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}",
                "old": "{\"SKUCode\":\"X9I689125STXL001\",\"SKUDescription\":\"ksls      \",\"c1\":\"X9I689125STXL\",\"c2\":\"XL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}"
              },
              {
                "new": "{\"SKUCode\":\"X9I689125STXL001\",\"SKUDescription\":\"ksls\",\"c1\":\"X9I689125STXL\",\"c2\":\"XL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}",
                "old": "{\"SKUCode\":\"X9I689125STXL001\",\"SKUDescription\":\"ksls      \",\"c1\":\"X9I689125STXL\",\"c2\":\"XL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}"
            }
          ]
      }
  ],
  status: 200,
  msg: null
}

export const getTaskStatusDataMockData = {
  "recordCount": null,
  "data": [
      {
          "TaskID": "2_20240427194750",
          "PendingSince": "27/04/2024 07:47 PM",
          "ageing": 3,
          "TaskName": "Modify-SKUMaster",
          "RequesterName": "jayesh",
          "Actiontype": 2
      },
      {
          "TaskID": "4_20240428152628",
          "PendingSince": "28/04/2024 03:26 PM",
          "ageing": 2,
          "TaskName": "Modify-SKUMaster",
          "RequesterName": "Akanksha",
          "Actiontype": 2
      },
      {
          "TaskID": "2_20240429105701",
          "PendingSince": "29/04/2024 10:57 AM",
          "ageing": 1,
          "TaskName": "Modify-SKUMaster",
          "RequesterName": "jayesh",
          "Actiontype": 2
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "2_20240429154939",
          "PendingSince": "29/04/2024 03:49 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "jayesh",
          "Actiontype": 3
      },
      {
          "TaskID": "4_20240429162944",
          "PendingSince": "29/04/2024 04:29 PM",
          "ageing": 1,
          "TaskName": "Modify-LocationMaster",
          "RequesterName": "Akanksha",
          "Actiontype": 2
      },
      {
          "TaskID": "4_20240429163007",
          "PendingSince": "29/04/2024 04:30 PM",
          "ageing": 1,
          "TaskName": "Modify-LocationMaster",
          "RequesterName": "Akanksha",
          "Actiontype": 2
      },
      {
          "TaskID": "2_20240429163443",
          "PendingSince": "29/04/2024 04:34 PM",
          "ageing": 1,
          "TaskName": "Add-SKUMaster",
          "RequesterName": "jayesh",
          "Actiontype": 1
      },
      {
          "TaskID": "4_20240429165332",
          "PendingSince": "29/04/2024 04:53 PM",
          "ageing": 1,
          "TaskName": "Modify-SKUMaster",
          "RequesterName": "Akanksha",
          "Actiontype": 2
      },
      {
          "TaskID": "4_20240429165339",
          "PendingSince": "29/04/2024 04:53 PM",
          "ageing": 1,
          "TaskName": "Modify-SKUMaster",
          "RequesterName": "Akanksha",
          "Actiontype": 2
      },
      {
          "TaskID": "4_20240429165533",
          "PendingSince": "29/04/2024 04:55 PM",
          "ageing": 1,
          "TaskName": "Modify-SKUMaster",
          "RequesterName": "Akanksha",
          "Actiontype": 2
      },
      {
          "TaskID": "4_20240429200710",
          "PendingSince": "29/04/2024 08:07 PM",
          "ageing": 1,
          "TaskName": "Remove-SkuLocationMaster",
          "RequesterName": "Akanksha",
          "Actiontype": 3
      }
  ],
  "status": 200,
  "msg": "Data fetched successfully",
  "errorCount": null,
  "error": null,
  "conflictErrorCount": null,
  "conflictError": null
}


export const getTaskDetailsDownloadDataMockData = {
  recordCount: null,
  data: [
    {
      "new": "{\"SKUCode\":\"X9I689125STXL001\",\"SKUDescription\":\"ksls      \",\"c1\":\"X9I689125STXL\",\"c2\":\"XL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}",
      "old": "{\"SKUCode\":\"X9I689125STXL001\",\"SKUDescription\":\"ksls      \",\"c1\":\"X9I689125STXL\",\"c2\":\"XL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}",
      "Status": "3",
      "Comments": ""
    },
    {
      "new": "{\"SKUCode\":\"X9I689125STXXL001\",\"SKUDescription\":\"ksls      \",\"c1\":\"X9I689125STXXL\",\"c2\":\"XXL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}",
      "old": "{\"SKUCode\":\"X9I689125STXXL001\",\"SKUDescription\":\"ksls      \",\"c1\":\"X9I689125STXXL\",\"c2\":\"XXL\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}",
      "Status": "3",
      "Comments": ""
    },
    {
      "new": "{\"SKUCode\":\"X9I689195STM001\",\"SKUDescription\":\"ksls      \",\"c1\":\"X9I689195STM\",\"c2\":\"M\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}",
      "old": "{\"SKUCode\":\"X9I689195STM001\",\"SKUDescription\":\"ksls      \",\"c1\":\"X9I689195STM\",\"c2\":\"M\",\"c3\":\"8.91E+12\",\"c4\":\"PC\",\"c5\":\"999\",\"c7\":\"UI\",\"c6\":\"USPA\"}",
      "Status": "4",
      "Comments": "C2 data is wrong"
    }
  ],
  status: 200,
  msg: null
}

export const createDraftMockData = {
  recordCount: null,
  data: '123456QA',
  status: 200,
  msg: null
}

export const deleteDraftMockData = {
  recordCount: null,
  data: '123456QA',
  status: 201,
  msg: "Draft Deleted Successfully"
}

export const deleteTaskMockData = {
  recordCount: null,
  data: '123456QA',
  status: 200,
  msg: "Task Deleted Successfully"
}

export const getSeasonalityDetailsMockData = {
  recordCount:null,
  data:{
    norm:[
        {
            "date":"4/1/2023",
            "old_norm":"97",
            "new_norm":"311",
            "change_reason":"Sesonality"
        },
        {
            "date":"4/5/2023",
            "old_norm":"311",
            "new_norm":"200",
            "change_reason":"Forced Norm Change"
        },
        {
            "date":"4/12/2023",
            "old_norm":"311",
            "new_norm":"415",
            "change_reason":"Forced Norm Change"
        },
        {
            "date":"5/15/2023",
            "old_norm":"415",
            "new_norm":"314",
            "change_reason":"Forced Norm Change"
        },
        {
            "date":"5/30/2023",
            "old_norm":"314",
            "new_norm":"500",
            "change_reason":"Forced Norm Change"
        }
    ],
    dailyData:[
        {
            "date":"4/1/2023",
            "stock":"50",
            "git":"45"
        },
        {
            "date":"4/2/2023",
            "stock":"50",
            "git":"45"
        },
        {
            "date": "4/3/2023",
            "stock": "48",
            "git": "42"
        },
        {
            "date": "4/4/2023",
            "stock": "47",
            "git": "43"
        },
        {
            "date": "4/5/2023",
            "stock": "49",
            "git": "44"
        },
        {
            "date": "4/6/2023",
            "stock": "51",
            "git": "46"
        },
        {
            "date": "4/7/2023",
            "stock": "52",
            "git": "47"
        },
        {
            "date": "4/8/2023",
            "stock": "50",
            "git": "45"
        },
        {
            "date": "4/9/2023",
            "stock": "48",
            "git": "42"
        },
        {
            "date": "4/10/2023",
            "stock": "47",
            "git": "43"
        },
        {
            "date": "4/11/2023",
            "stock": "49",
            "git": "44"
        },
        {
            "date": "4/12/2023",
            "stock": "51",
            "git": "46"
        },
        {
            "date": "4/13/2023",
            "stock": "52",
            "git": "47"
        },
        {
            "date": "4/14/2023",
            "stock": "50",
            "git": "45"
        },
        {
            "date": "4/15/2023",
            "stock": "48",
            "git": "42"
        },
    ]
},
  status:200,
  msg:null
}

export const modifyMasterMockData = {
  recordCount: null,
  taskId: '123456QA',
  status: 200,
  msg: null
}

export const SeasonalityRowData = {
  sc:"V9I004615P1L001",
  wc:"3017",
  skd:"T Shirt",
  sd:"5/05/2023",
  ed:"5/20/2023",
  ln:"Bangalore",
  tn:"300",
  bd:"7",
  onm:'50',
  r:"10"
}

export const ChartData = {
  labels:['4/1/2023','4/2/2023','4/3/2023','4/4/2023','4/5/2023'],
  datasets: [
    {
      type: 'line' as const,
      label: 'Norm',
      borderColor: '#002060',
      borderWidth: 3,
      data: [90,100,100,200,300],
      pointBackgroundColor: "#00B0F0",
      pointStyle:'circle',
      pointRadius:[8,8,0,8,8],
    },
    {
      type: 'line' as const,
      label: 'Season',
      borderWidth: 0,
      fill:{
        target:'origin',
        above:'rgba(207, 167, 187, 0.4)'
      },
      data: [300,300,300,300,300],
      pointRadius:0,
      pointStyle:'rect',
    },
    {
      type: 'line' as const,
      label: 'BuildUpDuration',
      borderWidth: 0,
      fill:{
        target:'origin',
        above:'rgba(127, 0, 255, 0.4)'
      },
      data: [300,300,300,300,300],
      pointRadius:0,
      pointStyle:'rect',
      pointBackgroundColor: "rgba(127, 0, 255, 0.4)",
    },
    {
      type: 'line' as const,
      label: 'RLT',
      borderWidth: 0,
      fill:{
        target:'origin',
        above:'rgba(9, 38, 53, 0.4)'
      },
      data: [300,300,300,300,300],
      pointRadius:0,
      pointStyle:'rect',
      pointBackgroundColor: "rgba(9, 38, 53, 0.4)",
    },
    {
      type: 'bar' as const,
      label: 'Stock',
      backgroundColor: '#E33A3A',
      data: [50,50,48,47,49],
      stack:'bar',
      pointStyle:'rect',
      pointHitRadius:0
    },
    {
      type: 'bar' as const,
      label: 'GIT',
      backgroundColor: '#52B735',
      data: [45,45,42,43,44],
      stack:'bar',
      pointStyle:'rect',
      pointHitRadius:0
    },
  ],
};

export const validateMasterMockData = {
  recordCount: null,
  data: {
    'sc':'ABCDEF',
    "error":'dummy error',
    'warning':'dummy warning'
  },
  status: 200,
  msg: null
}

export const getUploadProgressMockData:any = {
  recordCount: null,
  data: {
    progress:'1000',
    total_rows:'1000'
  },
  status: 200,
  msg: "Data fetched successfully"
}

export const getSkuLocMockData =
  {
    "recordCount": null,
    "data": [
        {
            "SKUCode": "WMSDXEE16KDWT"
        },
        {
            "SKUCode": "WMSDXEE16KDWT"
        },
        {
            "SKUCode": "WMSDXEE16KDWT"
        }
    ],
    "status": 200,
    "msg": null,
    "errorCount": null,
    "error": null,
    "conflictErrorCount": null,
    "conflictError": null
}

export const getTaskMasterHistoryMockData = {
  "recordCount": "18",
  "data": [
    {
      "id": "1",
      "name": "SKU",
      "fields": [
        {
          "displayName": "SKUCode",
          "key": "sc",
          "col_Position": "1",
          "visible": true,
          "isAdd": true,
          "isEdit": false,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "Description",
          "key": "sd",
          "col_Position": "2",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "ElephantOrderCapping",
          "key": "ec",
          "col_Position": "3",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "Weight",
          "key": "wt",
          "col_Position": "4",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "Volume",
          "key": "vm",
          "col_Position": "5",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "c1",
          "key": "c1",
          "col_Position": "6",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "c2",
          "key": "c2",
          "col_Position": "7",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "c3",
          "key": "c3",
          "col_Position": "8",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "c4",
          "key": "c4",
          "col_Position": "9",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "c5",
          "key": "c5",
          "col_Position": "10",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "c6",
          "key": "c6",
          "col_Position": "11",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "c7",
          "key": "c7",
          "col_Position": "12",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "c8",
          "key": "c8",
          "col_Position": "51",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "c9",
          "key": "c9",
          "col_Position": "52",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "c10",
          "key": "c10",
          "col_Position": "53",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "c11",
          "key": "c11",
          "col_Position": "54",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "c12",
          "key": "c12",
          "col_Position": "55",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "c13",
          "key": "c13",
          "col_Position": "57",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "c14",
          "key": "c14",
          "col_Position": "58",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "c15",
          "key": "c15",
          "col_Position": "59",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "SL1",
          "key": "SL1",
          "col_Position": "60",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "SL2",
          "key": "SL2",
          "col_Position": "61",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "SL3",
          "key": "SL3",
          "col_Position": "62",
          "visible": true,
          "isAdd": true,
          "isEdit": true,
          "isDownload": true,
          "isApplicable": true
        },
        {
          "displayName": "SL4",
          "key": "SL4",
          "col_Position": "63",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        },
        {
          "displayName": "SL5",
          "key": "SL5",
          "col_Position": "64",
          "visible": false,
          "isAdd": false,
          "isEdit": false,
          "isDownload": false,
          "isApplicable": false
        }
      ]
    }
  ]
};

      


