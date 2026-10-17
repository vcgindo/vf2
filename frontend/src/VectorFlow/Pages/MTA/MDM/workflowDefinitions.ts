// Existing workflow screen definitions, shared with their initialization state.
import { Field } from '../../../../VectorFlow/types/MDM';
import { ColDef } from 'ag-grid-enterprise';

export const savedDraftFields: Field[] = [
            {

              displayName: "Sr No.",
              key: "sr_no",
              visible: true,
              isAdd:true,
              isDownload:true,
              isDelete:true,
              isEdit:true,
              "col_Position":'1',
              "isApplicable":true,
              dataType:'String'
            },
            {
              displayName: "Last Modification Date",
              key: "LastModifiedDateTime",
              visible: true,
              isAdd:true,
              isDownload:true,
              isDelete:true,
              isEdit:true,
              "col_Position":'2',
              "isApplicable":true,
              dataType:'String'
            },
            {
              displayName: "Instance Name",
              key: "Masters",
              visible: true,
              isAdd:true,
              isDownload:true,
              isEdit:true,
              isDelete:true,
              "col_Position":'3',
              "isApplicable":true,
              dataType:'String'
            },
            // {
            //   displayName: "Search Key",
            //   key: "SearchKeys",
            //   visible: true,
            //   isAdd:true,
            //   isDownload:true,
            //   isEdit:true,
            //   "col_Position":'4',
            //   "isApplicable":true
            // },
            {
                displayName:"Action",
                key:"action",
                visible:true,
                isAdd:true,
                isDownload:true,
                isDelete:true,
                isEdit:true,
                "col_Position":'5',
                "isApplicable":true,
                dataType:'String'
            }
          ];

export const taskStatusColumns: ColDef[] = [
                    {
                        field:"TaskID",
                        colId:"TaskID",
                        headerName:"Task Id",
                        flex:1,
                        cellStyle: {
                            "textAlign": "center",
                        },
                        cellRenderer: 'agGroupCellRenderer'
                    },
                    {
                        field:"PendingSince",
                        colId:"PendingSince",
                        headerName:"Date",
                        flex:1,
                        cellStyle: {
                            "textAlign": "center",
                        }
                    },
                    {
                        field:"TaskName",
                        colId:"TaskName",
                        headerName:"Activity",
                        flex:1,
                        cellStyle: {
                            "textAlign": "center",
                        }
                    },
                    {
                        field:"Approver",
                        colId:"Approver",
                        headerName:"Approver Name",
                        flex:1,
                        cellStyle: {
                            "textAlign": "center",
                        }
                    },
                    {
                        field:"Requester",
                        colId:"Requester",
                        headerName:"Requester Name",
                        flex:1,
                        cellStyle: {
                            "textAlign": "center",
                        }
                    },
                    {
                        field:"TaskStatus",
                        colId:"TaskStatus",
                        headerName:"Status",
                        flex:1,
                        cellStyle: {
                            "textAlign": "center",
                        }
                    }
                ];

export const pendingTaskColumns = (renderer?: any, onClick?: any): ColDef[] => [
            {
                field:"SrNo",
                colId:"SrNo",
                headerName:"Sr No.",
            },
            {
                field:"PendingSince",
                colId:"PendingSince",
                headerName:"Pending Since",
            },
            {
                field:"ageing",
                colId:"ageing",
                headerName:"Ageing",
            },
            {
                field:"TaskName",
                colId:"TaskName",
                headerName:"Task Name",
                cellRenderer:renderer,
                cellRendererParams:{
                    onClick:onClick
                }
            },
            {
                field:"RequesterName",
                colId:"RequesterName",
                headerName:"Requester",
            }
        ];

export const historyColumns: ColDef[] = [
                {
                    headerName: "Date",
                    colId: 'Date',
                    field: 'PendingSince',
                    sort: 'desc',

                },
                {
                    headerName: "RequesterName",
                    colId: 'Requester',
                    field: 'RequesterName',
                },
                {
                    headerName: "ApproverName",
                    colId: 'Approver',
                    field: 'ApproverName',
                },
        ];
