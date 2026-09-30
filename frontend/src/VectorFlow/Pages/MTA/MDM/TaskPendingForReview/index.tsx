import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader"
import VFTable from "../../../../../components/VectorFLOW/commons/VFTable"
import { mapRowDataWithSrNo } from "../../../../../helpers/utils"
import useTaskPendingForReview from "./useTaskPendingForReview"
import TaskPendingTaskBar from "./TaskPendingTaskBar"
import { TaskPendingWrapper } from "./styles"
import ApproveAllModal from "./ApproveAllModal"
import RejectAllModal from "./RejectAllModal"
import { useUserData } from "../../../../../context"
import VFPagination from "../../../../../components/VectorFLOW/commons/VFPagination"
import { useSelector } from "react-redux"
import { RootState } from "../../../../../redux/store/store"


const TaskPendingForReview = ()=>{

    const {isSideBarOpen} = useUserData();

    const {
        ref,
        viewTableColDefs,
        detailTableColDefs,
        detailTableRowData,
        isViewTableOpen,
        viewTableRowData,
        showLoader,
        selectedRows,
        onCancel,
        setSelectedRows,
        onTaskSubmit,
        showApproveAllModal,
        toggleApproveAllModal,
        showRejectAllModal,
        toggleRejectAllModal,
        onSelectionTypeSuccess,
        setSelectionType,
        noDataMessage
    } = useTaskPendingForReview()

    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const TASKPENDINGFORREVIEW_PAGE = EnvConfig['TASKPENDINGFORREVIEW_PAGE'];  

    if(showLoader) return <VFLoader/>
    const suppressMovable = true;
        return (
          isViewTableOpen ? (
            <TaskPendingWrapper>
                    <VFTable
                    height={"100%"}
                    columnDefs={viewTableColDefs}
                    suppressMovableColumns={suppressMovable}
                    gridOptions={{
                        getRowStyle: (params: any) => {
                          if (params.node.rowIndex % 2 === 0) {
                            return { background: "#EBEBEB" };
                          }
                          return { background: "#F7F7F7" };
                        },
                        enableRangeSelection:true,
                        rowSelection:'multiple',
                      }}
                      statusBar={{
                        statusPanels:[
                          { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                          { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                          { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                          { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                          { statusPanel: 'agAggregationComponent', align: 'left' },
                        ]
                      }}
                    rowData={mapRowDataWithSrNo(viewTableRowData)}
                    localeText={{ noRowsToShow: noDataMessage?.length>0?noDataMessage:"No data to approve."}}
                    pagination={true}
                    paginationPageSize={parseInt(TASKPENDINGFORREVIEW_PAGE || '100')}  
                />
                </TaskPendingWrapper>
          ): (
            <TaskPendingWrapper>
                <VFTable
                    height={"85%"}
                    ref={ref}
                    columnDefs={detailTableColDefs}
                    gridOptions={{
                        readOnlyEdit:false,
                        getRowStyle: (params: any) => {
    
                        if (params.node.rowIndex % 2 === 0) {
                            return { background: "#EBEBEB" };
                        }
    
                        return { background: "#F7F7F7" };
                        },
                        enableRangeSelection:true,
                        rowSelection:'multiple',
                      }}
                      statusBar={{
                        statusPanels:[
                          { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                          { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                          { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                          { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                          { statusPanel: 'agAggregationComponent', align: 'left' },
                        ]
                      }}
                    rowData={detailTableRowData}
                    localeText={{ noRowsToShow: noDataMessage?.length>0?noDataMessage:"No data to approve."}}
                    suppressRowClickSelection 
                    onSelectionChanged={()=>{
                        if(ref && ref.current){
                            setSelectedRows(ref.current.api.getSelectedRows().length)
                        }
    
                    }}
                    pagination={true}
                    paginationPageSize={parseInt(TASKPENDINGFORREVIEW_PAGE || '100')}  
                    // paginationPageSize={50}
                    // suppressPaginationPanel={true}
                />
    
    
                {/* <VFPagination
                    selectedRows={selectedRows}
                    totalRows={recordCount}
                    currentPage={currentPage}
                    rowsPerPage={rowsPerPage}
                    handleChangePage={handleChangePage}
                    showPagination={false}
                    showTotalItems={false}
    
                /> */}
                {
                    showApproveAllModal && 
                        <ApproveAllModal onSuccess={()=>onSelectionTypeSuccess('Approved')} onClose={()=>toggleApproveAllModal(false)} setSelectionType={setSelectionType}/>
                }
                {
                    showRejectAllModal && 
                        <RejectAllModal onSuccess={()=>onSelectionTypeSuccess('Rejected')} onClose={()=>toggleRejectAllModal(false)} setSelectionType={setSelectionType} />
                }
                <TaskPendingTaskBar
                    isSideBarOpen={isSideBarOpen}
                    disableSubmit={selectedRows!==detailTableRowData?.length}
                    onCancel={onCancel}
                    onSubmit={onTaskSubmit}
                />
            </TaskPendingWrapper>
          )
        )   
     
    // if(isViewTableOpen){
    //     return(
    //         <TaskPendingWrapper>
    //             <VFTable
    //             height={"100%"}
    //             columnDefs={viewTableColDefs}
    //             suppressMovableColumns={suppressMovable}
    //             gridOptions={{
    //                 getRowStyle: (params: any) => {
    //                   if (params.node.rowIndex % 2 === 0) {
    //                     return { background: "#EBEBEB" };
    //                   }
    //                   return { background: "#F7F7F7" };
    //                 },
    //                 enableRangeSelection:true,
    //                 rowSelection:'multiple',
    //               }}
    //               statusBar={{
    //                 statusPanels:[
    //                   { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
    //                   { statusPanel: 'agTotalRowCountComponent', align: 'left' },
    //                   { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
    //                   { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
    //                   { statusPanel: 'agAggregationComponent', align: 'left' },
    //                 ]
    //               }}
    //             rowData={mapRowDataWithSrNo(viewTableRowData)}
    //             localeText={{ noRowsToShow: noDataMessage?noDataMessage:"No data to approve."}}
    //             pagination={true}
    //             paginationPageSize={parseInt(process.env.REACT_APP_TASKPENDINGFORREVIEW_PAGE || '100')}  
    //         />
    //         </TaskPendingWrapper>
    //     )
    // }
    // return (
    //     <TaskPendingWrapper>
    //         <VFTable
    //             height={"85%"}
    //             ref={ref}
    //             columnDefs={detailTableColDefs}
    //             gridOptions={{
    //                 readOnlyEdit:false,
    //                 getRowStyle: (params: any) => {
                        
    //                 if (params.node.rowIndex % 2 === 0) {
    //                     return { background: "#EBEBEB" };
    //                 }
                    
    //                 return { background: "#F7F7F7" };
    //                 },
    //                 enableRangeSelection:true,
    //                 rowSelection:'multiple',
    //               }}
    //               statusBar={{
    //                 statusPanels:[
    //                   { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
    //                   { statusPanel: 'agTotalRowCountComponent', align: 'left' },
    //                   { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
    //                   { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
    //                   { statusPanel: 'agAggregationComponent', align: 'left' },
    //                 ]
    //               }}
    //             rowData={detailTableRowData}
    //             suppressRowClickSelection 
    //             onSelectionChanged={()=>{
    //                 if(ref && ref.current){
    //                     setSelectedRows(ref.current.api.getSelectedRows().length)
    //                 }
                    
    //             }}
    //             pagination={true}
    //             paginationPageSize={parseInt(process.env.REACT_APP_TASKPENDINGFORREVIEW_PAGE || '100')}  
    //             // paginationPageSize={50}
    //             // suppressPaginationPanel={true}
    //         />
                    

    //         {/* <VFPagination
    //             selectedRows={selectedRows}
    //             totalRows={recordCount}
    //             currentPage={currentPage}
    //             rowsPerPage={rowsPerPage}
    //             handleChangePage={handleChangePage}
    //             showPagination={false}
    //             showTotalItems={false}

    //         /> */}
    //         {
    //             showApproveAllModal && 
    //                 <ApproveAllModal onSuccess={()=>onSelectionTypeSuccess('Approved')} onClose={()=>toggleApproveAllModal(false)} setSelectionType={setSelectionType}/>
    //         }
    //         {
    //             showRejectAllModal && 
    //                 <RejectAllModal onSuccess={()=>onSelectionTypeSuccess('Rejected')} onClose={()=>toggleRejectAllModal(false)} setSelectionType={setSelectionType} />
    //         }
    //         <TaskPendingTaskBar
    //             isSideBarOpen={isSideBarOpen}
    //             disableSubmit={selectedRows!==detailTableRowData?.length}
    //             onCancel={onCancel}
    //             onSubmit={onTaskSubmit}
    //         />
    //     </TaskPendingWrapper>
        
    // )
}

export default TaskPendingForReview