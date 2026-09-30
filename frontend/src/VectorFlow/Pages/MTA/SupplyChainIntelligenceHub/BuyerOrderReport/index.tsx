import VFTable from "../../../../../components/VectorFLOW/commons/VFTable"
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"

 import { BORLayout } from "./styles"
 import {useBOR} from "./useBOR"
 import ActionToolBar from "../Planning/ActionToolBar"
import { GridStateContext } from "../../../../../context/GridStateContext";
import DailyDataGraphModal from "../../../../../components/VectorFLOW/commons/DailyDataGraphModal";
import NormChangeHistoryTable from "../../../../../components/VectorFLOW/commons/NormChangeHistoryTable";
import BPRRemarkHistoryModal from "../BPR/BPRRemarkHistoryModal";
import VFSaveRemark from "../../../../../components/VectorFLOW/commons/VFSaveRemark"
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import OverlayLoader from "../../../../../VectorFlow/Pages/MTO/Common/Loader";
import { useState } from "react"
import { useSelector } from "react-redux"
import { RootState } from "../../../../../redux/store/store"


const BuyerOrderReport = ()=>{


    const {     
     isLoading,      
        BORColumns,
        agGridProps,
        rowData,       
        currentPage,
        recordCount,
        ref,
        isSavedDataLoading,
        handleChangePage,
        tempRef,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        onExportToExcelCallBack,
        showDailyDataGraphModal,
        showNormChangeHistoryTable,
        dailyData,
        currFilter,
        setCurrFilter,
        onDeleteFilter, 
        onApplyFilter ,
        onSubmitRemarks,
        editedRows,
        isRemarkHistoryToolTipOpen,
        remarkHistory,
        generalFilterOptions,
        onCloseRemarkHistory,
        onResetCallback,
        lastRunDate,
         savePageSize,
        userPageSize
    } = useBOR()

    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const BOR_ROWS_PER_PAGE = EnvConfig['BOR_ROWS_PER_PAGE'];   
    return(
      <GridStateContext.Provider
        value={{
          ref: ref,
          exportExcelColumns: exportExcelColumns,
          setExportExcelColumns: setExportExcelColumns,
          tempDownloadData: tempDownloadData,
          setTempDownloadData: setTempDownloadData,
          exportExcelRowData: exportExcelRowData,
          setExportExcelRowData: setExportExcelRowData,
          onResetCallback:onResetCallback
        }}
      >
        <div style={{ marginLeft: '10px' }}>
          <ActionToolBar
            view={'grid'}
            setCurrentTab={''}
            currCategory={'BOR'}
            currentTab={''}
            tabsList={[]}
            onApplyFilter={(e) => onApplyFilter(e)}
            onFloatingTabChange={() => console.log('')}
            onGoBack={() => console.log('')}
            onViewChange={() => console.log('')}
            genericRecordCount={recordCount}
            onExportToExcelCallBack={onExportToExcelCallBack}
            multiFilter={currFilter}
            setMultiFilter={setCurrFilter}
            onSubmitEditedRows={onSubmitRemarks}
            disableSubmitEditedRowsBtn={editedRows.length===0}
            lastRunDate={lastRunDate}
            generalFilterOptions={generalFilterOptions}
            onDelete={onDeleteFilter} />
        </div>
        {lastRunDate && (
        <LastRunDateComponent lastRunDate={lastRunDate} />
      )}
        <BORLayout>
          {/* <BORTaskBar style={{width:'74%'}}>
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
    </BORTaskBar> */}
          {(isLoading || isSavedDataLoading) &&<OverlayLoader/>}
          
            
              <div style={{ height: '78vh' }}>
                {showDailyDataGraphModal && <DailyDataGraphModal rowData={dailyData.rowData} chartData={dailyData.chartData} normChangeData={dailyData.normChangeData} masterData={dailyData.masterData} isModalOpen={showDailyDataGraphModal} suggestionData={dailyData.suggestionData} monitoringData={dailyData.monitoringData} skuKey={'SKUCode'} whKey={'WHDescription'} />}
                {showNormChangeHistoryTable && <NormChangeHistoryTable data={dailyData.normChangeData} />}

                <VFTable
                  {...agGridProps}
                  columnDefs={BORColumns}
                  rowData={rowData}
                  ref={ref}
                  enableRangeSelection={true} // Added property
                  rowSelection="multiple"
                  statusBar={{
                    statusPanels: [
                      { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                      { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                      { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                      { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                      { statusPanel: 'agAggregationComponent', align: 'left' },
                    ],
                  }}
                  height={"80%"}
                  maintainColumnOrder
                  onFilterChanged={() => {
                    const filterModel = ref?.current?.api?.getFilterModel();
                    if (filterModel && Object.keys(filterModel).length > 0) {
                      setIsDisabled(false);
                    } else {
                      setIsDisabled(true);
                    }
                  }}
                  tooltipShowDelay={500}
                  />
              {
              rowData?.length  > 0 && 
              <>
              <VFPagination
                  selectedRows={0}
                  totalRows={recordCount}
                  currentPage={currentPage}
                  rowsPerPage={userPageSize || parseInt(BOR_ROWS_PER_PAGE || '100')}
                  handleChangePage={(e) => handleChangePage(e)}
                  resetGridRef={ref} 
                  isDisabled={isDisabled} 
                      customPageSizeEnabled={true}
                    userPageSize={userPageSize}
                    savePageSize={savePageSize}
                  />
                <VFSaveRemark onSubmitRemarks={onSubmitRemarks}/>
              </> 
                }
              </div>
          
          {/* <div style={{ display: 'none' }}>
            <VFTable
              ref={tempRef}
              columnDefs={BORColumns}
              rowData={exportExcelRowData}
              {...tempAgGridProps} />
          </div> */}



            {/* {isSubmitRemarkToolTipOpen && (
                <BPRSubmiRemarkToolTip
                    remark={remark}
                    setRemark={updateRemark}
                    style={submitRemarkToolTipPosition}
                    onSuccess={onSubmitRemark}
                    onClose={onCloseSubmitRemark}
                    themeUi={themeUi}
                />
            )} */}

            <BPRRemarkHistoryModal
                data={remarkHistory}
                isOpen={isRemarkHistoryToolTipOpen}
                onClose={onCloseRemarkHistory}
            />
            <div style={{display:'none'}}>                
                  <VFTable
                    key={'temp'} 
                    ref={tempRef}
                    columnDefs={BORColumns}
                    rowData={exportExcelRowData}
                    {...tempAgGridProps}
                    maintainColumnOrder
                  />
                </div>

        </BORLayout>
      </GridStateContext.Provider>
    )
}

export default BuyerOrderReport