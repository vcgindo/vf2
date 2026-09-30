import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader"
import VFTable from "../../Common/VFTable"
import { mapRowDataWithSrNo } from "../../../../../helpers/utils"
import useTaskPendingForReview from "./useTaskPendingForReview"
import TaskPendingTaskBar from "./TaskPendingTaskBar"
import { TaskPendingWrapper } from "./styles"
import { useUserData } from "../../../../../context"


const MTOTaskPendingForReview = ()=>{

    const {isSideBarOpen} = useUserData();

    const {
        ref,
        viewTableColDefs,
        detailTableColDefs,
        detailTableRowData,
        isViewTableOpen,
        showLoader,
        selectedRows,
        onCancel,
        onTaskSubmit,
        mtoPendingTaskData,
        mtoSubmitTask,
        currentMaster
    } = useTaskPendingForReview()

    if(showLoader) return <VFLoader/>

   


    if(isViewTableOpen){
        return(
            <TaskPendingWrapper>
                <VFTable
                // ref = {gridRef}
                height={"100%"}
                columnDefs={viewTableColDefs}
                gridOptions={{
                    getRowStyle: (params: any) => {
                      if (params.node.rowIndex % 2 === 0) {
                        return { background: "#EBEBEB" };
                      }
                      return { background: "#F7F7F7" };
                    },
                    enableRangeSelection:true,
                    rowSelection:'multiple',
                    defaultColDef:{
                      flex: 1
                    }
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
                rowData={mapRowDataWithSrNo(mtoPendingTaskData)}
                // rowData={mtoPendingTaskData}
                pagination={true}
                paginationPageSize={parseInt(process.env.REACT_APP_TASKPENDINGFORREVIEW_PAGE || '100')}  
                disableZoomScaling
                maintainColumnOrder
            />
            </TaskPendingWrapper>
        )
    }
    return (
        <TaskPendingWrapper>
            <VFTable
                height={"85%"}
                ref={ref}
                columnDefs={detailTableColDefs}
                gridOptions={{
                    defaultColDef: {
                      flex: currentMaster===503?  1: 0
                    },
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
                suppressRowClickSelection 
                pagination={true}
                  
                paginationPageSize={parseInt(process.env.REACT_APP_TASKPENDINGFORREVIEW_PAGE || '100')}  
                // suppressPaginationPanel={true}
                disableZoomScaling
                maintainColumnOrder
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
          
                    <div style={{zoom:0.8}}>
                  {

              (!(detailTableRowData&& detailTableRowData.length>0 && detailTableRowData)) ?

              <TaskPendingTaskBar
              isSideBarOpen={isSideBarOpen}
              disableSubmit={selectedRows!==detailTableRowData.length}
              onCancel={onCancel}
              onSubmit={onTaskSubmit}
              />
              :

              <TaskPendingTaskBar
              isSideBarOpen={isSideBarOpen}
              disableSubmit={false}
              onCancel={onCancel}
              onSubmit={mtoSubmitTask}
              />
              
            }
            </div>
        </TaskPendingWrapper>
        
    )
}

export default MTOTaskPendingForReview