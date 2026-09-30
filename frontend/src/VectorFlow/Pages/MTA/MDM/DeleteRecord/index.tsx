import React,{ useEffect, useState } from "react";


import useDelete from "./useDelete";
import useViewModify from "../ViewModify/useViewModify";
import { useUserData } from "../../../../../context";


import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";
import SelectGroupedMasters from "../../../../../components/VectorFLOW/layouts/SelectGroupedMasters";
import { SCContainer, SCFilterContainer, SCFilterControls, SCLegend, SCFilterAddControls, SCFilterAddButton, SCFilterAddButtonWrapper, SCFilterSeperator, SCFilterButtonGroup} from "../ViewModify/styles";
import VFTab from "../../../../../components/VectorFLOW/commons/VFTab";
import VFTable from "../../../../../components/VectorFLOW/commons/VFTable";
import UploadModal from "../ViewModify/UploadModal";
import WarningModal from "../ViewModify/WarningModal";
import VFTaskBar from "../ViewModify/VFTaskbar";
import VFFilter from "../../../../../components/VectorFLOW/commons/VFFilter";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline";
import VFPagination from "../../../../../components/VectorFLOW/commons/VFPagination";
import VFOverlay from "../../../../../components/VectorFLOW/commons/VFOverlay";
import { GridFilterWrapper ,TextBtn} from "../../../MTO/Common/VFPagination/styles";



import { getUploadModalRadioButtons,generateOptions, getMDMTableHeight } from "../../../../../helpers/utils";
import { Filter } from "../../../../../VectorFlow/types/MDM";
import { operators } from "../../../../../helpers/MDMConstants";
import { useLocation } from "react-router";
import { useSelector } from "react-redux";
import { RootState } from "../../../../../redux/store/store";



const DeleteRecord = () => {

  const suppressMovable = true;
  const {user} = useUserData()
  const themeUi = user?.user?.theme_ui;
  const location = useLocation();
  const [disabled,setDisabled]=useState(true);
 

    const {
        isSelectMasterOpen,
        activeMaster,
        allMastersState,
        handleTabChange,
        handleTabClose,
        addNewMaster,
        handleOnAddFilter,
        handleOnDeleteFilter,
        isLoading,
        handleApplyFilter,
        isWarningModalOpen,
        recordCount,
        isUploadModalOpen,
        isSavingToDraft,
        toggleUploadModal,
        onWarningModalClose,
        onWarningModalSuccess,
        downloadFileName,
        setDownloadFileName,
        onUploadMaster,
        file,
        setFile,
        isTableDataLoading,
        exportToExcel,
        onClearExportError,
        agGridProps,
        ref,
        tempRef,
        tempAgGridProps,
        tempGridData,
        deleteSelected,
        editOnline,
        isShowAll,
        onSaveToDraft,
        selectedRowsCount,
        currentPage,
        rowsPerPage,
        handleChangePage,
        onReset,
        onEditOnlineSave,
        onBackButton,
        onBackButton1,
        isOverlayVisible,
        isDataAvailableLocally,
        enableEditOnlineReset,
        tempRecordCount,
        onDiscardDraftCallback
    } = useViewModify('remove');
    

    const {
        onCancel,
        selectedMasters, 
        onDeleteData,
        onSubmit,
        onDeleteOnline,
        onDeleteOnlineSubmit,
        onDeleteOnlineReset,
        handleOnClickMaster,
        handleSubmitSelectMaster,
        handleRadioButton,
        options,
        selectedOptions,
        showMaster,
        showMasterGroup,
        isSubmitDisabled,
        errorCount
    } = useDelete();
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const DELETERECORD_PAGE = EnvConfig['DELETERECORD_PAGE'];  
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
   // const [isDisabled, setIsDisabled]= useState<boolean>(true)
    

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
              onSubmit={handleSubmitSelectMaster}  
              onCancel={onCancel}
              handleOnClickMaster={handleOnClickMaster}
              allMasters={allMastersState}
              selectedMasters={selectedMasters}
              text="delete"
              selectedOptions={selectedOptions}
              options={options}
              shouldShowMaster={showMaster}
              shouldShowMasterGroup={showMasterGroup}
              isAdd={false}
          />
      )
    }
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
                  { (activeMaster.progress ==='default' || activeMaster.progress ==='deleteView') 
                    &&
                  <SCFilterContainer style={{zoom:'var(--nms-filter-zoom)'}}>
                    <SCFilterControls>
                      <SCLegend>Filter</SCLegend>
                      {activeMaster.filters.map((f:Filter)=>{
                        if(f.masterId==activeMaster?.id){
                          return(
                            <VFFilter 
                              onDelete={()=>handleOnDeleteFilter(f.id)}
                              operators={operators}
                              filters={activeMaster.filters}
                              fields={generateOptions([activeMaster])}
                              currFilter={f}
                              key={f.id}
                              isDisabled={false}
                            />
                          )
                        }
                      })}
                      
                    </SCFilterControls>
                    <SCFilterAddControls>
                      {activeMaster.filters.map((f:Filter,index:number)=>{
                          if(f.masterId===activeMaster?.id && index===0){
                            return (
                              <SCFilterAddButtonWrapper>
                                <SCFilterAddButton
                                  onClick={handleOnAddFilter}
                                  src={themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/NMS/add-filter-regal.svg":"/assets/img/VectorFLOW/NMS/add-filter.svg"}
                                  key={f.id}
                                  data-testid="add-filter"
                                />
                              </SCFilterAddButtonWrapper>
                              
                            )
                          }
                        })}
                    </SCFilterAddControls>
                    <SCFilterSeperator/>
                    <SCFilterButtonGroup>
                      <VFButton
                      themeUi={themeUi}
                      onClick={()=>{handleApplyFilter()}}
                      disabled={false}
                      >
                        Apply Filter
                      </VFButton>
                      <VFButtonOutline
                        onClick={()=>{handleApplyFilter(true)}}
                        themeUi={themeUi}
                        
                      >
                        Show All
                      </VFButtonOutline>
                    </SCFilterButtonGroup>
                  </SCFilterContainer>
                }
                  <VFTable
                    ref={ref}
                    height={getMDMTableHeight(activeMaster)}
                    columnDefs={activeMaster.colDefs}
                    suppressMovableColumns={suppressMovable}
                    rowData={activeMaster.rowData}
                    {...agGridProps}
                    suppressPaginationPanel={!isDataAvailableLocally}
                    onFilterChanged={() => {
                      const filterModel = ref?.current?.api?.getFilterModel();
                      if (filterModel && Object.keys(filterModel).length > 0) {
                        setDisabled(false);
                      } else {
                        setDisabled(true);
                      }
                    }}
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
                  />
                  {
                (!['default'].includes(activeMaster.progress) && (!isDataAvailableLocally && !isSelectMasterOpen)) 
                  && 
                  <VFPagination
                  resetGridRef={ref} 
                    selectedRows={selectedRowsCount} 
                    totalRows={recordCount} 
                    currentPage={currentPage} 
                    rowsPerPage={parseInt(DELETERECORD_PAGE || '100')}
                    handleChangePage={(e)=>handleChangePage(e)} 
                    isDisabled={disabled}
                  />
              }
                  <div style={{display:'none'}}>                
                    <VFTable
                      ref={tempRef}
                      rowData={tempGridData}
                      {...tempAgGridProps}
                    />
                  </div>

              </VFTab>
              
          </SCContainer>

          {isWarningModalOpen && 
          <WarningModal 
            rowsPerPage={rowsPerPage}
          showAll={isShowAll}
            count={tempRecordCount} 
            onCloseModal={onWarningModalClose} 
            onFailure={onWarningModalClose} 
            onSuccess={()=>onWarningModalSuccess()}
            />
        }
          {isUploadModalOpen && 
          <UploadModal 
            header={"Deletion"}
            openModal={isUploadModalOpen} 
            onCloseModal={()=>{setFile(undefined);toggleUploadModal(false)}} 
            onDownload={() => exportToExcel(true)} 
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
              enableEditOnlineReset={enableEditOnlineReset}
              disableResumeSeasonality={()=>false}
              disableStopSeasonality={()=>false}
              masterProgress={activeMaster.progress}
              onReset={onReset}
              onSaveToDraft={onSaveToDraft}
              isSavingToDraft={isSavingToDraft ?? false}
              onEditOnlineSave={onEditOnlineSave}
              editOnline={false}
              deleteOnline={editOnline}
              onBack={() => onBackButton(location?.state?.backUrl)}
              onBack1={() => onBackButton1(location?.state?.backUrl)}
              onClearAndExportErrors={onClearExportError}
              onModifyData={()=>toggleUploadModal(true)}
              onExportData={exportToExcel}
              onSubmit={()=>onSubmit(ref)}
              onDeleteSelected={deleteSelected}
              onEditOnline={()=>console.log('')}
              onPhaseInPhaseOutStop={()=>console.log('')}
              onSeasonalityResume={()=>console.log('')}
              onSeasonalityStop={()=>console.log('')}
              onSubmitConflictData={()=>console.log('')}
              onDeleteData={onDeleteData}
              onDeleteOnline={onDeleteOnline}
              onDeleteOnlineReset={onDeleteOnlineReset}
              onDeleteOnlineSubmit={onDeleteOnlineSubmit}
              masterId={activeMaster.id}
              DataCount={activeMaster.rowData.length}
              onDiscardDraftCallback={onDiscardDraftCallback}
              showExportErrors={activeMaster.rowData?.find((rowdata) => (rowdata.error && rowdata.error !== '')) ? true : false}
            />
          </div>
        }
        </React.Fragment>
    ) 
}

export default DeleteRecord;