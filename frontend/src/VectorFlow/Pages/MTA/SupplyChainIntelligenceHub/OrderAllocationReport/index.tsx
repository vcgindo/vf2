import {RRRLayout} from './styles'
import useOrderAllocation from './useOrderAllocationReport';
import VFTable from '../../../../../components/VectorFLOW/commons/VFTable';
import VFLoader from '../../../../../components/VectorFLOW/commons/VFLoader';
import ActionToolBar from "../Planning/ActionToolBar"
import { GridStateContext } from '../../../../../context/GridStateContext';
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"
import { useState } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../../../../../redux/store/store';

 

const OrderAllocationReport = () => {

 const { 
  colDefs,
  agGridProps,
  rowData, 
  isLoading,
  recordCount,
  currentPage,
  tempRef,
  tempDownloadData,
  setTempDownloadData,
  tempAgGridProps,
  exportExcelRowData,
  setExportExcelRowData,
  exportExcelColumns,
  setExportExcelColumns,
  onExportToExcelCallBack,
  handleChangePage,
  onApplyFilter,
  currFilter,
  setCurrFilter,
  onDeleteFilter,
  isSavedDataLoading,
  ref,
  generalFilterOptions,
  onResetCallback
} = useOrderAllocation();

  const [isDisabled, setIsDisabled]= useState<boolean>(true)
  const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
  const ORDER_ALLOCATION_ROWS_PER_PAGE = EnvConfig['ORDER_ALLOCATION_ROWS_PER_PAGE'];   
  
  return (
  <GridStateContext.Provider
  value={{
    ref:ref,
    exportExcelColumns:exportExcelColumns,
    setExportExcelColumns:setExportExcelColumns,
    tempDownloadData:tempDownloadData,
    setTempDownloadData:setTempDownloadData,
    exportExcelRowData:exportExcelRowData,
    setExportExcelRowData:setExportExcelRowData,
    onResetCallback:onResetCallback
}}
  >
    <div style={{marginLeft:'10px'}}>
      <ActionToolBar 
        view={'grid'} 
        setCurrentTab={''} 
        currCategory={'OrderAllocationReport'} 
        currentTab={''} 
        tabsList={[]} 
        onApplyFilter={(e)=>onApplyFilter(e)}
        onFloatingTabChange={()=>console.log('')} 
        onGoBack={()=>console.log('')} 
        onViewChange={()=>console.log('')}
        genericRecordCount={recordCount}
        disableChartAndGridViewToggle
        onExportToExcelCallBack={onExportToExcelCallBack}
        multiFilter={currFilter}
        generalFilterOptions={generalFilterOptions}
        setMultiFilter={setCurrFilter}
        onDelete={onDeleteFilter}
      />
    </div>
    <RRRLayout>
        {/* <RRRTaskBar style={{width:isSideBarOpen? '77%':'97%'}}>
            <VFButtonOutline
                    themeUi="NOIRFUSION"
                    onClick={()=>console.log('')}
                >
                    Excel Export 
            </VFButtonOutline>
            <VFButton
                    themeUi="NOIRFUSION"
                    onClick={()=>console.log('')}
                >
                    Edit Filter
            </VFButton>
            <VFButton
                    themeUi="NOIRFUSION"
                    onClick={()=>console.log('')}
                >
                    Reset Filter
            </VFButton>
        </RRRTaskBar> */}
        {(isLoading || isSavedDataLoading)?(
          <VFLoader/>
        ):
        (
          <div style={{height:'70vh'}}>

          <VFTable
                  ref={ref}
                  {...agGridProps}
                  columnDefs={colDefs}
                  rowData={rowData}
                  enableRangeSelection={true} // Added property
                rowSelection="multiple"
                statusBar = {{
                    statusPanels: [
                      { statusPanel: 'agTotalAndFilteredRowCountComponent', align:'left' },
                      { statusPanel: 'agTotalRowCountComponent', align:'left' },
                      { statusPanel: 'agFilteredRowCountComponent', align:'left' },
                      { statusPanel: 'agSelectedRowCountComponent', align:'left' },
                      { statusPanel: 'agAggregationComponent', align:'left' },
                    ],
                  }}
                height={"100%"}
                maintainColumnOrder
                onFilterChanged={() => {
                  const filterModel = ref?.current?.api?.getFilterModel();
                  if (filterModel && Object.keys(filterModel).length > 0) {
                    setIsDisabled(false);
                  } else {
                    setIsDisabled(true);
                  }
                }}
              />  
              <VFPagination 
                selectedRows={0} 
                totalRows={recordCount} 
                currentPage={currentPage} 
                rowsPerPage={parseInt(ORDER_ALLOCATION_ROWS_PER_PAGE|| '100')}
                handleChangePage={handleChangePage}
                resetGridRef={ref} 
                isDisabled={isDisabled}  
              />  
        </div>
        )}
        <div style={{display:'none'}}>                
          <VFTable
            ref={tempRef}
            columnDefs={colDefs}
            rowData={exportExcelRowData}
            {...tempAgGridProps}
          />
        </div>
    </RRRLayout>
  </GridStateContext.Provider>
  )
}

export default OrderAllocationReport