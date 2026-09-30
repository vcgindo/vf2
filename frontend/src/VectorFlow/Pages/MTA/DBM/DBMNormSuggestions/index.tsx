import {DBMLayout} from './styles'
import useDBM from './useDBM';
import VFTable from "../../../../../components/VectorFLOW/commons/VFTable"
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"
import ActionToolBar from '../../SupplyChainIntelligenceHub/Planning/ActionToolBar';
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader"
import DailyDataGraphModal from '../../../../../components/VectorFLOW/commons/DailyDataGraphModal';
import NormChangeHistoryTable from '../../../../../components/VectorFLOW/commons/NormChangeHistoryTable';
import { GridStateContext } from '../../../../../context/GridStateContext';
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import { useState } from 'react';

const DBM = () => {

 const { 
  isLoading,
  DBMColumns,
  agGridProps,
  DBMRowData,
  handleChangePage,
  DBMDataCount,
  currentPage,
  gridRef,
  showAllCheckbox,
  handleGoButton,
  handleGoButtonForSleep,
  showDailyDataGraphModal,
  showNormChangeHistoryTable,
  dailyData,
  tempRef,
  tempDownloadData,
  setTempDownloadData,
  tempAgGridProps,
  exportExcelRowData,
  setExportExcelRowData,
  exportExcelColumns,
  setExportExcelColumns,
  handleApplyFilter,
  currentFilter,
  setCurrentFilter,
  onDeleteFilter,
  onExportToExcelCallBack,
  recordsPerPage,
  generalFilterOptions,
  onResetCallback,
  lastRunDate,     
  savePageSize,
  userPageSize
} = useDBM();

const [isDisabled, setIsDisabled]= useState<boolean>(true)


 if(isLoading){
  return (
    <VFLoader/>
  )
}


  return (
    <>
      <GridStateContext.Provider
        value={{
          ref: gridRef,
          exportExcelColumns: exportExcelColumns,
          setExportExcelColumns: setExportExcelColumns,
          tempDownloadData: tempDownloadData,
          setTempDownloadData: setTempDownloadData,
          exportExcelRowData: exportExcelRowData,
          setExportExcelRowData: setExportExcelRowData,
          onResetCallback: onResetCallback,
        }}
      >
        <ActionToolBar
          view={"grid"}
          setCurrentTab={() => {
            return;
          }}
          currCategory={"DBMNorm"}
          currentTab={""}
          tabsList={[]}
          onFloatingTabChange={() => console.log("")}
          onGoBack={() => console.log("")}
          onViewChange={() => console.log("")}
          showAllTick={showAllCheckbox}
          handleGoButton={handleGoButton}
          handleGoButtonForSleep={handleGoButtonForSleep}
          genericRecordCount={DBMDataCount}
          onExportToExcelCallBack={onExportToExcelCallBack}
          onApplyFilter={handleApplyFilter}
          multiFilter={currentFilter}
          setMultiFilter={setCurrentFilter}
          lastRunDate={lastRunDate}
          generalFilterOptions={generalFilterOptions}
          onDelete={onDeleteFilter}
        />
        {lastRunDate && <LastRunDateComponent lastRunDate={lastRunDate} />}
        <DBMLayout>
          <div style={{ height: "70vh" }}>
            {showDailyDataGraphModal && (
              <DailyDataGraphModal
                rowData={dailyData.rowData}
                chartData={dailyData.chartData}
                normChangeData={dailyData.normChangeData}
                masterData={dailyData.masterData}
                isModalOpen={showDailyDataGraphModal}
                suggestionData={dailyData.suggestionData}
                monitoringData={dailyData.monitoringData}
                skuKey={"SKUCode"}
                whKey={"LocName"}
              />
            )}
            {showNormChangeHistoryTable && (
              <NormChangeHistoryTable data={dailyData.normChangeData} />
            )}

            <VFTable
              {...agGridProps}
              columnDefs={DBMColumns}
              rowData={DBMRowData}
              ref={gridRef}
              height={"100%"}
              enableRangeSelection={true}
              rowSelection="multiple"
              statusBar={{
                statusPanels: [
                  {
                    statusPanel: "agTotalAndFilteredRowCountComponent",
                    align: "left",
                  },
                  { statusPanel: "agTotalRowCountComponent", align: "left" },
                  { statusPanel: "agFilteredRowCountComponent", align: "left" },
                  { statusPanel: "agSelectedRowCountComponent", align: "left" },
                  { statusPanel: "agAggregationComponent", align: "left" },
                ],
              }}
              maintainColumnOrder
              tooltipShowDelay={500}                  
              onFilterChanged={() => {
                const filterModel = gridRef?.current?.api?.getFilterModel();
                if (filterModel && Object.keys(filterModel).length > 0) {
                  setIsDisabled(false);
                } else {
                  setIsDisabled(true);
                }
              }}
            />
            {
              DBMRowData?.length &&
            <VFPagination
              selectedRows={0}
              totalRows={DBMDataCount}
              currentPage={currentPage}
              rowsPerPage={userPageSize}
              handleChangePage={(e) => handleChangePage(e)}
              resetGridRef={gridRef} 
              isDisabled={isDisabled}
              customPageSizeEnabled={true}
              userPageSize={userPageSize}
              savePageSize={savePageSize}
            />
          }
          </div>
          <div style={{ display: "none" }}>
            <VFTable
              ref={tempRef}
              columnDefs={DBMColumns}
              rowData={exportExcelRowData}
              {...tempAgGridProps}
            />
          </div>
        </DBMLayout>
      </GridStateContext.Provider>
    </>
  );
}

export default DBM