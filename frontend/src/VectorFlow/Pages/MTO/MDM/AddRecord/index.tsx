import React, { useCallback, useEffect, useState } from "react";
import SelectGroupedMasters from "../../../../../components/VectorFLOW/layouts/SelectMTOGroupedMasters";
import useViewModify from "../ViewModify/useViewModify";
import useAdd from "./useAdd";
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";
import VFTab from "../../../../../components/VectorFLOW/commons/MTO/VFTab";
import { SCContainer } from "../ViewModify/styles";
import VFTable from "../../Common/VFTable";
import UploadModal from "../ViewModify/UploadModal";
import VFTaskBar from "../ViewModify/VFTaskbar";
import VFPagination from "../../../../../components/VectorFLOW/commons/VFPagination";
import VFOverlay from "../../../../../components/VectorFLOW/commons/VFOverlay";
import { useUserData } from "../../../../../context";
import {getUploadModalRadioButtons } from "../../../../../helpers/utils";
import { useDispatch } from "react-redux";
import { TOGGLE_SELECT_MASTER_SCREEN } from "../../../../../redux/actions/MDM";
import { MDMMasterState,Field } from "../../../../types/MDM";
import { CustomStatusPanel } from "../CustomStatusPannel";
import { notifyError, notifyLoader, notifySuccess } from "../../../../../helpers/notify";
import useSimpleBlocker from "../ViewModify/UseSimpleBlocker";


const MTOAddRecord = () => {

    const {user} = useUserData()
    const themeUi = user?.user?.theme_ui;
   const [isDisabled, setIsDisabled] = useState(true);




    const {
        activeMaster,
        handleTabClose,
        addNewMaster,
        isLoading,
        toggleUploadModal,
        downloadFileName,
        setDownloadFileName,
        onUploadMaster,
        file,
        setFile,
        isTableDataLoading,
        exportToExcel,
        onBackButton,
        onClearExportError,
        agGridProps,
        ref,
        tempRef,
        tempAgGridProps,
        tempGridData,
        deleteSelected,
        selectedRowsCount,
        recordCount,
        currentPage,
        handleChangePage,
        editOnline,
        onEditOnline,
        isUploadModalOpen,
        onReset,
        onSaveToDraft,
        onEditOnlineSave,
        isDataAvailableLocally,
        isOverlayVisible,
        errorCount,
        onMTOSaveBufferData,
        onMTOSaveAsDraft,
        onExcelExport

    } = useViewModify('add');

    const {
      isSelectMasterOpen,
        handleSubmitSelectMaster,
        onCancel,
        allMasters,
        selectedMasters,
        handleOnClickMaster,
        handleRadioButton,
        handleTabChange,
        onSubmit,
        showMasterGroup,
        showMaster,
        options,
        selectedOptions
      } = useAdd()


    useSimpleBlocker(activeMaster,onBackButton);

    const handleExportData = useCallback(() => {
        notifyLoader('Exporting Data')
        try {
          ref?.current?.api?.exportDataAsExcel(onExcelExport());
          notifySuccess('Exported Data Successfully')
        } catch (error:any) {
          notifyError(error.message || "Failed to Export Data")
        }
      }, [ref, onExcelExport]);

    
    useEffect(()=>{
      if(ref.current && ref.current.api){
        if(isTableDataLoading){
          ref.current?.api.showLoadingOverlay();
        }
        else{
          ref.current?.api.hideOverlay();
        }
      }
    },[isTableDataLoading])



    if(isLoading){
        return <VFLoader/>
    }

    if(isSelectMasterOpen){
      return(
          <SelectGroupedMasters  
              onSubmit={handleSubmitSelectMaster}  
              onCancel={onCancel}
              handleOnClickMaster={handleOnClickMaster}
              allMasters={allMasters}
              selectedMasters={selectedMasters}
              text="add"
              shouldShowMasterGroup={showMasterGroup}
              shouldShowMaster={showMaster}
              options={options}
              selectedOptions={selectedOptions}
          />
      )
    }
    const dispatch = useDispatch();


    const onGridReady = (params: any) => {
      params.api.sizeColumnsToFit();
    };


   const calendarModifiedColDefs = ()=>{
    if(activeMaster.id === 504){
      const calendarModifiedColDef = activeMaster.colDefs.filter((colDef: any) => {
        if (colDef.field !== "plid" && colDef.field !== "rb" && colDef.field !== "rd") {
          return true;
        }
        return false;
      })
      return calendarModifiedColDef
    }else{
      return activeMaster.colDefs
    }
   }

   const clearGridFilter = () =>{
    ref?.current?.api.setFilterModel(null);
    setIsDisabled(true);
  }


    return(
        <React.Fragment>
          <SCContainer>
              <VFTab 
                activeMaster={activeMaster}
                themeUi={themeUi}
                isAdd={true}
                onTabChange={handleTabChange}
                onTabClose={(e)=>handleTabClose(e,activeMaster)}
                newTabTitle={"Add Master"}
                newTabIcon={"/assets/img/VectorFLOW/BPR/add-circle.svg"}
                newTabHandler={addNewMaster}
                >
                  <VFTable
                  height={"95%"}
                  ref={ref}
                  columnDefs={calendarModifiedColDefs()}
                  onGridReady={onGridReady}
                  
                  rowData={activeMaster.rowData}
                    {...agGridProps}
                    suppressPaginationPanel={!isDataAvailableLocally}
                    statusBar={{
                      statusPanels: isDataAvailableLocally?[
                        { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                        { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                        { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                        { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                      { statusPanel: 'agAggregationComponent', align: 'left' },
                      { statusPanel: CustomStatusPanel,
                        key: 'clearGridFilters',
                        align:'right',
                        statusPanelParams: {
                          isDisabled,
                          clearGridFilter,
                          themeUi,
                        },
                      },
                    ]:
                    [],
                  }}
                  onFilterChanged={()=>{
                    if(ref && ref.current && ref.current.api){
                      Object.keys(ref.current.api.getFilterModel())?.length > 0
                        ? setIsDisabled(false)
                        : setIsDisabled(true);
                    }
                  }}
                  defaultColDef= {
                    {flex: (activeMaster.id===501 || activeMaster.id===503)? 1: 0}
                  }
                  // onCellEditingStopped={ onDataChange}
                  maintainColumnOrder
                  />
                {/* } */}
                  <div style={{display:'none'}}>                
                    <VFTable
                      ref={tempRef}
                      rowData={tempGridData}
                      {...tempAgGridProps}
                      />
                  </div>

              </VFTab>
              {
                (!['default'].includes(activeMaster.progress) && (!isDataAvailableLocally && !isSelectMasterOpen)) 
                  && 
                  <VFPagination 
                    selectedRows={selectedRowsCount} 
                    totalRows={recordCount} 
                    currentPage={currentPage} 
                    rowsPerPage={parseInt(process.env.REACT_APP_ADDRECORD_PAGE  || '100')} 
                    handleChangePage={(e)=>handleChangePage(e)}  
                  />
              }
          </SCContainer>
          {isUploadModalOpen && 
          <UploadModal 
            header={"Addition"}
            openModal={isUploadModalOpen} 
            onCloseModal={()=>dispatch(TOGGLE_SELECT_MASTER_SCREEN(true))}
            // onDownload={()=>ref.current?.api.exportDataAsExcel({
            //   fileName:downloadFileName.length>0?downloadFileName :activeMaster.name,
            // })} 
            onDownload={()=>{
              const currentMaster = allMasters.find((master:MDMMasterState)=>master.id === activeMaster.id);
              const downloadableColumnKeys:string[] = [];
              activeMaster.fields.forEach((field:Field)=>{
                if(field.isAdd){
                  downloadableColumnKeys.push(field.key)
                }
              });
              if(currentMaster){
                ref.current?.api.exportDataAsExcel({fileName:downloadFileName ==='' ? currentMaster.name : downloadFileName,columnKeys:downloadableColumnKeys});
              }
            }}
            onUpload={()=>{
              onUploadMaster()
            }}
            inputText={downloadFileName}
            setInputText={setDownloadFileName}
            file={file}
            setFile={setFile}
            uploadButtonStatus={false}
            radioButtons={getUploadModalRadioButtons(activeMaster.id)}
            handleRadioButton={handleRadioButton}
            downloadFileText={'Download sample template'}
            />
        }
        {/* {isConflictModalOpen && 
          <SubmitErrorModal 
            totalCount={activeMaster.rowData.length}
            errorCount={errorCount}
            recordCount={activeMaster.rowData.length - conflictCount - errorCount}
            onSuccess={onIgnoreSubmitErrors}
            onCloseModal={onIgnoreSubmitErrors}

          />
        } */}
        {
          isOverlayVisible && (
            <VFOverlay>
             <h1 style={{backgroundColor:"white",padding:'15px',borderRadius:'8px'}}>Loading....</h1>
            </VFOverlay>
          )
        }
        {
          !isSelectMasterOpen && 
          <VFTaskBar
          showSubmittedExportError={errorCount>0}
            enableEditOnlineReset={false}
            masterProgress={activeMaster.progress}
            onReset={onReset}
            onSaveToDraft={onSaveToDraft}
            onEditOnlineSave={onEditOnlineSave}
            editOnline={editOnline}
            onEditOnline={()=>onEditOnline('editOnline')}
            onBack={onBackButton}
            onClearAndExportErrors={()=>onClearExportError()}
            onModifyData={()=>toggleUploadModal(true)}
            onExportData={handleExportData}
            onSubmit={onSubmit}
            onDeleteSelected={deleteSelected}
            onPhaseInPhaseOutStop={()=>console.log('')}
            onDeleteData={()=>console.log('')}
            onDeleteOnline={()=>console.log('')}
            onDeleteOnlineReset={()=>console.log('')}
            onSubmitConflictData={()=>console.log('')}
            onDeleteOnlineSubmit={()=>console.log('')}
            masterId={activeMaster.id}
            mtoSaveData={true}
            onMTOSaveData={ onMTOSaveBufferData}
            isMTOSaveDataDisabled={((activeMaster?.rowData?.some((row:any)=>row?.err?.error!=='')))}
            onMTOSaveAsDraft={onMTOSaveAsDraft}
            isMTODraftDisabled={((activeMaster?.rowData.some((row:any)=>row?.err?.error!=='')))}
            isMTOExcludeButton={activeMaster?.rowData.some((row:any)=>row?.err?.error!=='')}
          />
        }
        </React.Fragment>
    )
}

export default MTOAddRecord;