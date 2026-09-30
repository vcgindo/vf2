import {RRRLayout} from './styles'
import useRRR from './useRRR';
import VFTable from "../../../../../components/VectorFLOW/commons/VFTable"
import ActionToolBar from "../Planning/ActionToolBar"
import { GridStateContext } from '../../../../../context/GridStateContext';
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import OverlayLoader from '../../../../../VectorFlow/Pages/MTO/Common/Loader';
import { useState } from 'react';
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"
import { useSelector } from 'react-redux';
import { RootState } from '../../../../../redux/store/store';




const RRR = () => {

 const { 
  RRRColumns,
  agGridProps,
  RRRRowData, 
  isLoading,
  RRRDataCount,
  reportError,
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
  getRRRRowData,
  onApplyFilter,
  currFilter,
  setCurrFilter,
  onDeleteFilter,
  isSavedDataLoading,
  ref,
  generalFilterOptions,
  onResetCallback,
  lastRunDate,
  userPageSize,
  savePageSize
} = useRRR();

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
        currCategory={'RRR'} 
        currentTab={''} 
        tabsList={[]} 
        onApplyFilter={(e)=>onApplyFilter(e)}
        onFloatingTabChange={()=>console.log('')} 
        onGoBack={()=>console.log('')} 
        onViewChange={()=>console.log('')}
        genericRecordCount={RRRDataCount}
        onExportToExcelCallBack={onExportToExcelCallBack}
        multiFilter={currFilter}
        lastRunDate={lastRunDate}
        generalFilterOptions={generalFilterOptions}
        setMultiFilter={setCurrFilter}
        onDelete={onDeleteFilter}
      />
    </div>
    {lastRunDate && (
        <LastRunDateComponent lastRunDate={lastRunDate} />
      )}
    <RRRLayout>
        {reportError && <p role="alert">{reportError}</p>}
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
        {(isLoading || isSavedDataLoading) && <OverlayLoader/>}
          <div style={{height:'70vh'}} hidden={Boolean(reportError)}>

          <VFTable
                  ref={ref}
                  {...agGridProps}
                  columnDefs={RRRColumns}
                  rowData={RRRRowData}
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
                height={"95%"}
                maintainColumnOrder
                onFilterChanged={() => {
                  const filterModel = ref?.current?.api?.getFilterModel();
                  if (filterModel && Object.keys(filterModel).length > 0) {
                    setIsDisabled(false);
                  } else {
                    setIsDisabled(true);
                  }
                }}
                // onColumnVisible={(params) => params.api.sizeColumnsToFit()}
                // onGridSizeChanged={(params) => params.api.sizeColumnsToFit()}
              />  
            {
            RRRRowData?.length  > 0 &&  
            <VFPagination 
                selectedRows={0} 
                totalRows={RRRDataCount} 
                currentPage={currentPage} 
                rowsPerPage={userPageSize}
                handleChangePage={(e)=>getRRRRowData(e , userPageSize)} 
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
            columnDefs={RRRColumns}
            rowData={exportExcelRowData}
            {...tempAgGridProps}
          />
        </div>
    </RRRLayout>
  </GridStateContext.Provider>
  )
}

export default RRR
