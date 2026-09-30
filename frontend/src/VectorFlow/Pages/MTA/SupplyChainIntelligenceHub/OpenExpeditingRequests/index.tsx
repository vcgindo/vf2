

import VFTable from "../../../../../components/VectorFLOW/commons/VFTable"
import ActionToolBar from "../Planning/ActionToolBar"
import BPRSubmiRemarkToolTip from "../BPR/BPRSubmitRemarkToolTip"

import useOpenExpeditingRequests from "./useOpenExpeditingRequests"
import { GridStateContext } from "../../../../../context/GridStateContext"
import RemarkModal from "./RemarkModal"

import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader"

import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline"
import { ButtonWrapper } from "./styles"
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import { useState } from "react"
import { GridFilterWrapper, TextBtn } from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination/styles"
import { useUserData } from "../../../../../context";
import VFSaveRemark from "../../../../../components/VectorFLOW/commons/VFSaveRemark"



const OpenExpeditingRequests = () => {

  const {
    agGridProps,
    rowData,
    remark,
    isLoading,
    remarkHistory,
    isSubmitRemarkToolTipOpen,
    isRemarkHistoryToolTipOpen,
    submitRemarkToolTipPosition,
    ref,
    updateRemark,
    onSubmitRemark,
    onCloseSubmitRemark,
    onCloseRemarkHistory,
    tempDownloadData,
    setTempDownloadData,
    OERColumns,
    exportExcelRowData,
    setExportExcelRowData,
    exportExcelColumns,
    setExportExcelColumns,
    currentFilter,
    setCurrentFilter,
    onDeleteFilter,
    onApplyFilter,
    editedRows,
    onSubmitEditedRows,
    themeUi,
    onResetCallback,
    lastRunDate
  } = useOpenExpeditingRequests()

    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    const {user} = useUserData()
    const theme_ui = user.user.theme_ui

    const clearGridFilter = () =>{
      ref?.current?.api.setFilterModel(null);
      setIsDisabled(true);
      }
  
    const CustomStatusPanel = () => {
      return (
        <GridFilterWrapper style={{marginTop:'25px'}}>
          <TextBtn onClick={clearGridFilter} disabled={isDisabled} themeUi={theme_ui}>
              Clear All Grid Filters
          </TextBtn>  
        </GridFilterWrapper>           
        );
    };
  
  return (
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
      <div style={{ marginLeft: '10px',marginBottom:'10px' }}>
        <ActionToolBar
          view={'grid'}
          setCurrentTab={''}
          currCategory={'OpenExpeditingRequests'}
          currentTab={''}
          tabsList={[]}
          onFloatingTabChange={() => console.log('')}
          onGoBack={() => console.log('')}
          onViewChange={() => console.log('')}
          genericRecordCount={12}
          onExportToExcelCallBack={() => { return }}
          multiFilter={currentFilter}
          lastRunDate={lastRunDate}
          setMultiFilter={setCurrentFilter}
          onDelete={onDeleteFilter}
          onApplyFilter={onApplyFilter}
          onSubmitEditedRows={onSubmitEditedRows}
          disableSubmitEditedRowsBtn={editedRows.length === 0}
        />
      </div>
      {lastRunDate && (
        <LastRunDateComponent lastRunDate={lastRunDate} />
      )}
      {(isLoading) ?
        (
          <VFLoader />
        )
        :
        (<div style={{ marginLeft: '15px', height: '70vh' }}>
          <VFTable
            columnDefs={OERColumns}
            rowData={rowData}
            enableRangeSelection={true}
            rowSelection="multiple"
            statusBar={{
              statusPanels: [
                { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                { statusPanel: 'agAggregationComponent', align: 'left' },
                { statusPanel: CustomStatusPanel, align: "right" },

              ],
            }}
            {...agGridProps}
            ref={ref}
            onGridReady={(params) => {
              agGridProps.onGridReady?.(params);
              params.api.addEventListener('filterChanged', () => {
                  const filterModel = params.api.getFilterModel();
                  if (Object.keys(filterModel).length > 0) {
                      setIsDisabled(false); 
                  } else {
                      setIsDisabled(true); 
                  }
                  });
            }}
            
            height={"95%"}
            maintainColumnOrder={true}
          />
          
          <VFSaveRemark onSubmitRemarks={onSubmitEditedRows} isDisabled={editedRows.length === 0}/>
          
          {/* <ButtonWrapper>
            <VFButtonOutline disabled={editedRows.length === 0} themeUi={themeUi} width={169} style={{ fontSize: '20px', fontWeight: '500' }} onClick={onSubmitEditedRows}>Save  Remarks</VFButtonOutline>
          </ButtonWrapper> */}
        </div>
        )
      }
      
      {isSubmitRemarkToolTipOpen && (
        <BPRSubmiRemarkToolTip
          remark={remark}
          setRemark={updateRemark}
          style={submitRemarkToolTipPosition}
          onSuccess={onSubmitRemark}
          onClose={onCloseSubmitRemark}
          themeUi={themeUi}
        />
      )}

      {isSubmitRemarkToolTipOpen && (
        <BPRSubmiRemarkToolTip
          remark={remark}
          setRemark={updateRemark}
          style={submitRemarkToolTipPosition}
          onSuccess={onSubmitRemark}
          onClose={onCloseSubmitRemark}
          themeUi={themeUi}
        />
      )}

      <RemarkModal
        isOpen={isRemarkHistoryToolTipOpen}
        data={remarkHistory}
        onClose={onCloseRemarkHistory}
      />
    </GridStateContext.Provider>
  )
}

export default OpenExpeditingRequests