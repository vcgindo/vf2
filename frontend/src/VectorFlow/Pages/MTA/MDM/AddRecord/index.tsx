import React, { useEffect, useState } from "react";

import SelectGroupedMasters from "../../../../../components/VectorFLOW/layouts/SelectGroupedMasters";


import useViewModify from "../ViewModify/useViewModify";
import useAdd from "./useAdd";


import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";
import VFTab from "../../../../../components/VectorFLOW/commons/VFTab";
import { SCContainer } from "../ViewModify/styles";
import VFTable from "../../../../../components/VectorFLOW/commons/VFTable";
import UploadModal from "../ViewModify/UploadModal";
import VFTaskBar from "../ViewModify/VFTaskbar";
import VFPagination from "../../../../../components/VectorFLOW/commons/VFPagination";
import VFOverlay from "../../../../../components/VectorFLOW/commons/VFOverlay";
import { GridFilterWrapper ,TextBtn} from "../../../MTO/Common/VFPagination/styles";
import { useUserData } from "../../../../../context";
import {getUploadModalRadioButtons } from "../../../../../helpers/utils";
import { useDispatch, useSelector } from "react-redux";
import { TOGGLE_SELECT_MASTER_SCREEN } from "../../../../../redux/actions/MDM";

import { MDMMasterState,Field } from "../../../../types/MDM";
import { useLocation } from "react-router";
import { RootState } from "../../../../../redux/store/store";

const AddRecord = () => {

    const {user} = useUserData()
    const themeUi = user?.user?.theme_ui;
    const [disabled,setDisabled]=useState(true);

    const location = useLocation();

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
        isSavingToDraft,
        exportToExcel,
        onBackButton,
        onBackButton1,
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
        onDiscardDraftCallback

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
        selectedOptions,
        errorCount,
        isSubmitDisabled
    } = useAdd()
    
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig); 
    const ADDRECORD_PAGE = EnvConfig['ADDRECORD_PAGE'];  
    const RECORD_UPLOAD_LIMIT = EnvConfig['RECORD_UPLOAD_LIMIT']; 
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

         const clearGridFilter = () =>{
                  ref?.current?.api.setFilterModel(null);
                  setDisabled(true)
              }
          
             
              const CustomStatusPanel = () => {
                  return (
                      <GridFilterWrapper style={{marginTop:'25px'}}>
                          <TextBtn onClick={clearGridFilter} disabled={disabled} themeUi={themeUi}>
                              Clear All Grid Filters
                          </TextBtn>  
                      </GridFilterWrapper>           
                  );
              };


    if(isSelectMasterOpen){
      return(
          <SelectGroupedMasters  
              onSubmit={handleSubmitSelectMaster}  //console.log()
              onCancel={onCancel}
              handleOnClickMaster={handleOnClickMaster}
              allMasters={allMasters}
              selectedMasters={selectedMasters}
              text="add"
              shouldShowMasterGroup={showMasterGroup}
              shouldShowMaster={showMaster}
              options={options}
              selectedOptions={selectedOptions}
              isAdd={true}
          />
      )
    }
    const dispatch = useDispatch();
    const suppressMovable = true;
    return(
        <React.Fragment>
          <SCContainer>
              <VFTab 
                activeMaster={activeMaster}
                themeUi={themeUi}
                onTabChange={handleTabChange}
                onTabClose={handleTabClose}
                newTabTitle={"Add Master"}
                newTabIcon={"/assets/img/VectorFLOW/NMS/add-circle.svg"}
                newTabHandler={addNewMaster}
                >
                  <VFTable
                    height={"calc(100% )"}
                    ref={ref}
                    columnDefs={activeMaster.colDefs}
                    suppressMovableColumns={suppressMovable}
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
                      { statusPanel: CustomStatusPanel, align: "right" },
                    ]:
                    [],
                    
                  }}
                  onFilterChanged={() => {
                    const filterModel = ref?.current?.api?.getFilterModel();
                    if (filterModel && Object.keys(filterModel).length > 0) {
                      setDisabled(false);
                    } else {
                      setDisabled(true);
                    }
                }}
                  />
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
                    rowsPerPage={parseInt(ADDRECORD_PAGE  || '100')} 
                    handleChangePage={(e)=>handleChangePage(e)}  
                  />
              }
          </SCContainer>
          {isUploadModalOpen && 
          <UploadModal 
            header={"Addition"}
            openModal={isUploadModalOpen} 
            onCloseModal={() => {
              setFile(undefined);
              dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));
            }}
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
            onUpload={async ()=>{
              await onUploadMaster(RECORD_UPLOAD_LIMIT)
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
          <div style={{zoom:'var(--nms-filter-zoom)'}}>
            <VFTaskBar
              disableSubmit={isSubmitDisabled}
              showSubmittedExportError={activeMaster?.rowData.length > 0 && errorCount>0}
              enableEditOnlineReset={false}
              disableResumeSeasonality={()=>false}
              disableStopSeasonality={()=>false}
              masterProgress={activeMaster.progress}
              onReset={onReset}
              onSaveToDraft={onSaveToDraft}
              isSavingToDraft={isSavingToDraft ?? false}
              onEditOnlineSave={onEditOnlineSave}
              editOnline={editOnline}
              onEditOnline={()=>onEditOnline('editOnline')}
              onBack={() => onBackButton(location?.state?.backUrl)}
              onBack1={() => onBackButton1(location?.state?.backUrl)}
              onClearAndExportErrors={onClearExportError}
              onModifyData={()=>toggleUploadModal(true)}
              onExportData={exportToExcel}
              onSubmit={onSubmit}
              onDeleteSelected={deleteSelected}
              onPhaseInPhaseOutStop={()=>console.log('')}
              onSeasonalityResume={()=>console.log('')}
              onSeasonalityStop={()=>console.log('')}
              onDeleteData={()=>console.log('')}
              onDeleteOnline={()=>console.log('')}
              onDeleteOnlineReset={()=>console.log('')}
              onSubmitConflictData={()=>console.log('')}
              onDeleteOnlineSubmit={()=>console.log('')}
              masterId={activeMaster.id}
              DataCount={activeMaster.rowData.length}
              onDiscardDraftCallback={onDiscardDraftCallback}
            />
          </div>
        }
        </React.Fragment>
    )
}

export default AddRecord;