

import VFTable from "../../../../../components/VectorFLOW/commons/VFTable"
import ActionToolBar from "../../SupplyChainIntelligenceHub/Planning/ActionToolBar"
import BPRSubmiRemarkToolTip from "../../SupplyChainIntelligenceHub/BPR/BPRSubmitRemarkToolTip"


import { GridStateContext } from "../../../../../context/GridStateContext"
import useInTransitWhereAbouts from "./useInTransitWhereAbouts"
import ContactDetailsModal from "./ContactDetailsModal"
import RemarkModal from "./RemarkModal"
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader"
import { ButtonWrapper } from "../../SupplyChainIntelligenceHub/OpenExpeditingRequests/styles"
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline"
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import { useState } from "react"
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"


const InTransitWhereAbouts = ()=>{


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
        colDefs,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        currentUserDetails,
        isContactModalOpen,
        onCloseContactModal,
        isSubmitETAToolTipOpen,
        etaValue,
        setETAValue,
        submitETAToolTipPosition,
        onCloseSubmitETA,
        isSubmitCurrentLocationTipOpen,
        submitCurrentLocationToolTipPosition,
        currentLocationValue,
        setCurrentLocationValue,
        onCloseSubmitCurentLocation,
        recordCount,
        currentPage,
        currentFilter,
        setCurrFilter,
        onDeleteFilter,
        onApplyFilter,
        onExportToExcelCallBack,
        tempRef,
        tempAgGridProps,
        onSubmitCurrentLocation,
        onSubmitETA,
        handlePageChange,
        editedRows,
        onSubmitEditedRows,
        themeUi,
        lastRunDate,
        onResetCallback,
        savePageSize,
        userPageSize
    } = useInTransitWhereAbouts()

    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    

    return(
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
            <div style={{marginLeft:'10px',marginBottom:'10px'}}>
                <ActionToolBar 
                view={'grid'} 
                setCurrentTab={''} 
                currCategory={'InTransitWhereabouts'} 
                currentTab={''} 
                tabsList={[]} 
                onFloatingTabChange={()=>console.log('')} 
                onGoBack={()=>console.log('')} 
                onViewChange={()=>console.log('')}
                genericRecordCount={recordCount}
                onExportToExcelCallBack={onExportToExcelCallBack}
                multiFilter={currentFilter}
                lastRunDate={lastRunDate}
                setMultiFilter={setCurrFilter}
                onDelete={onDeleteFilter}
                onApplyFilter={onApplyFilter}
                onSubmitEditedRows={onSubmitEditedRows}
                disableSubmitEditedRowsBtn={editedRows.length===0}
                disableChartAndGridViewToggle
              />
              </div>
              {lastRunDate && (
        <LastRunDateComponent lastRunDate={lastRunDate} />
      )}
          
        {
            isLoading
            ?
            <VFLoader/>
            :
            <div style={{height:'70%',marginLeft:'15px'}}>
                <VFTable
                    columnDefs={colDefs}
                    rowData={rowData}
                    {...agGridProps}
                    ref={ref}
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
                <div style={{marginBottom:'10px'}}>
                <div>
             {
              rowData?.length  > 0 &&
                <VFPagination
                    selectedRows={0}
                    totalRows={recordCount}
                    currentPage={currentPage}
                    rowsPerPage={100}
                    handleChangePage={handlePageChange}
                    resetGridRef={ref} 
                    isDisabled={isDisabled}
                    customPageSizeEnabled={true}
                    userPageSize={userPageSize}
                    savePageSize={savePageSize}
                />
             }
                </div>
                </div>
                {/* <ButtonWrapper>
                    <VFButtonOutline disabled={editedRows.length===0} themeUi={themeUi} width={169} style={{fontSize:'20px', fontWeight:'500'}} onClick={onSubmitEditedRows}>Save  Remarks</VFButtonOutline>
                </ButtonWrapper> */}
            </div>
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
        {isSubmitETAToolTipOpen && (
            <BPRSubmiRemarkToolTip
                remark={etaValue}
                setRemark={(e)=>setETAValue(e.target.value)}
                style={submitETAToolTipPosition}
                onSuccess={onSubmitETA}
                onClose={onCloseSubmitETA}
                isDate
                themeUi={themeUi}
            />
        )}
         {isSubmitCurrentLocationTipOpen && (
            <BPRSubmiRemarkToolTip
                remark={currentLocationValue}
                setRemark={(e)=>setCurrentLocationValue(e.target.value)}
                style={submitCurrentLocationToolTipPosition}
                onSuccess={onSubmitCurrentLocation}
                onClose={onCloseSubmitCurentLocation}
                themeUi={themeUi}
            />
        )}
            <ContactDetailsModal isOpen={isContactModalOpen} onClose={onCloseContactModal} data={currentUserDetails}/>
            <RemarkModal isOpen={isRemarkHistoryToolTipOpen} onClose={onCloseRemarkHistory} data={remarkHistory}/>
            <div style={{display:'none'}}>                
                  <VFTable
                    ref={tempRef}
                    columnDefs={colDefs}
                    rowData={exportExcelRowData}
                    {...tempAgGridProps}
                    maintainColumnOrder
                  />
                </div>
        </GridStateContext.Provider>
    )
}

export default InTransitWhereAbouts