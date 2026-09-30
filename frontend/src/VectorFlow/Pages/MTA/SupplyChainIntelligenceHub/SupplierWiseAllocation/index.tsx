import VFTable from "../../../../../components/VectorFLOW/commons/VFTable"
import VFPagination from "../../../MTO/Common/VFPagination"

 import { BORLayout } from "./styles"
 import {useSupplierWiseAllocation} from "./useSupplierWiseAllocation"
 import ActionToolBar from "../Planning/ActionToolBar"
import { GridStateContext } from "../../../../../context/GridStateContext";
import DailyDataGraphModal from "../../../../../components/VectorFLOW/commons/DailyDataGraphModal";
import NormChangeHistoryTable from "../../../../../components/VectorFLOW/commons/NormChangeHistoryTable";
import VFSaveRemark from "../../../../../components/VectorFLOW/commons/VFSaveRemark"
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import BPRRemarkHistoryModal from "../BPR/BPRRemarkHistoryModal";
import OverlayLoader from "../../../MTO/Common/Loader";
import { useState } from "react";
import { useSelector } from "react-redux"
import { RootState } from "../../../../../redux/store/store"


const SupplierWiseAllocation = ()=>{

    const {     
     isLoading,      
        BORCBColumns,
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
        generalFilterOptions,
        onSubmitRemarks,
        editedRows,
        onResetCallback,
        lastRunDate,
        isRemarkHistoryToolTipOpen,
        remarkHistory,
        onCloseRemarkHistory,
         savePageSize,
        userPageSize
    } = useSupplierWiseAllocation()

    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const SUPPLY_WISE_ALLOCATION_HUB_ROWS_PER_PAGE = EnvConfig['SUPPLY_WISE_ALLOCATION_HUB_ROWS_PER_PAGE'];  

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
            currCategory={'SupplierWiseAllocation'}
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
            disableChartAndGridViewToggle
            lastRunDate={lastRunDate}
            generalFilterOptions={generalFilterOptions}
            onDelete={onDeleteFilter} 
            onSubmitEditedRows={onSubmitRemarks}
            disableSubmitEditedRowsBtn={editedRows.length===0}
            />
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
          {(isLoading || isSavedDataLoading) && <OverlayLoader/>}
              <div style={{ height: '78vh' }}>
                {showDailyDataGraphModal && <DailyDataGraphModal rowData={dailyData.rowData} chartData={dailyData.chartData} normChangeData={dailyData.normChangeData} masterData={dailyData.masterData} isModalOpen={showDailyDataGraphModal} suggestionData={dailyData.suggestionData} monitoringData={dailyData.monitoringData} skuKey={'SKUCode'} whKey={'WHDescription'} />}
                {showNormChangeHistoryTable && <NormChangeHistoryTable data={dailyData.normChangeData} />}

                <VFTable
                  {...agGridProps}
                  columnDefs={BORCBColumns}
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
                {rowData?.length  > 0 &&
                <VFPagination
                  selectedRows={0}
                  totalRows={recordCount}
                  currentPage={currentPage}
                  rowsPerPage={userPageSize }
                  handleChangePage={handleChangePage}
                  resetGridRef={ref} 
                  isDisabled={isDisabled}  
                  customPageSizeEnabled={true}
              userPageSize={userPageSize}
              savePageSize={savePageSize}
                  />
                }
                {/* <VFSaveRemark onSubmitRemarks={onSubmitRemarks} /> */}

              </div>
          <div style={{ display: 'none' }}>
            <VFTable
              ref={tempRef}
              columnDefs={BORCBColumns}
              rowData={exportExcelRowData}
              {...tempAgGridProps} />
          </div>
        </BORLayout>
        <BPRRemarkHistoryModal
                data={remarkHistory}
                isOpen={isRemarkHistoryToolTipOpen}
                onClose={onCloseRemarkHistory}
        />
      </GridStateContext.Provider>
    )
}

export default SupplierWiseAllocation