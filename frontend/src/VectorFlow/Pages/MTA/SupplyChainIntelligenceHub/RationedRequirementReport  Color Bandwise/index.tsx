import {RRRLayout} from './styles'
import useRRRColorBandwise from './useRRRColorBandwise';
import VFTable from '../../../../../components/VectorFLOW/commons/VFTable';
import ActionToolBar from "../Planning/ActionToolBar"
import { GridStateContext } from '../../../../../context/GridStateContext';
import OverlayLoader from '../../../../..//VectorFlow/Pages/MTO/Common/Loader';
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"
import { useState } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../../../../../redux/store/store';


const RRRColorBandwise = () => {

 const { 
  RRRColorBandWiseColumns,
  agGridProps,
  rowData, 
  isLoading,
  recordsCount,
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
  getRRRBandwiseRowData,
  onApplyFilter,
  currFilter,
  setCurrFilter,
  onDeleteFilter,
  isSavedDataLoading,
  ref,
  generalFilterOptions,
  onResetCallback,
  savePageSize,
  userPageSize
} = useRRRColorBandwise();

  const [isDisabled, setIsDisabled]= useState<boolean>(true)
  
  const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
  const RRR_ROWS_PER_PAGE = EnvConfig['RRR_ROWS_PER_PAGE'];   
  
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
        currCategory={'RRRColorBandwise'} 
        currentTab={''} 
        tabsList={[]} 
        onApplyFilter={(e)=>onApplyFilter(e)}
        onFloatingTabChange={()=>console.log('')} 
        onGoBack={()=>console.log('')} 
        onViewChange={()=>console.log('')}
        genericRecordCount={recordsCount}
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
         {(isLoading || isSavedDataLoading) &&<OverlayLoader/>}
          
          <div style={{height:'70vh'}}>

          <VFTable
                  ref={ref}
                  {...agGridProps}
                  columnDefs={RRRColorBandWiseColumns}
                  rowData={rowData}
                  enableRangeSelection={true} // Added property
                   tooltipShowDelay={500}
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
              {
              rowData?.length  > 0 &&
              <VFPagination 
                selectedRows={0} 
                totalRows={recordsCount} 
                currentPage={currentPage} 
                rowsPerPage={userPageSize || parseInt(RRR_ROWS_PER_PAGE || '100')}
                handleChangePage={(e)=>getRRRBandwiseRowData(e,userPageSize)} 
                resetGridRef={ref} 
                isDisabled={isDisabled}
                customPageSizeEnabled={true}
                userPageSize={userPageSize}
                savePageSize={savePageSize}
              />  
              }
        </div>
    
        <div style={{display:'none'}}>                
          <VFTable
            ref={tempRef}
            columnDefs={RRRColorBandWiseColumns}
            rowData={exportExcelRowData}
            {...tempAgGridProps}
            maintainColumnOrder
          />
        </div>
    </RRRLayout>
  </GridStateContext.Provider>
  )
}

export default RRRColorBandwise