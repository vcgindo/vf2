import _ from "lodash";
import React, { useCallback, useEffect, useState } from "react";
import { useSelector } from "react-redux";
import { v4 as uuidv4 } from "uuid";
import VFTab from "../../../../../components/VectorFLOW/commons/MTO/VFTab";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline";
import VFFilter from "../../../../../components/VectorFLOW/commons/VFFilterMDM";
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";
import VFOverlay from "../../../../../components/VectorFLOW/commons/VFOverlay";
import SelectMaster from "../../../../../components/VectorFLOW/layouts/SelectMasterMTO";
import { useUserData } from "../../../../../context";
import {
  operators,
} from "../../../../../helpers/MtoMDMConstants";
import { notifyError, notifyLoader, notifySuccess } from "../../../../../helpers/notify";
import {
  areMasterFiltersValid,
  generateMTOFilterOptions,
} from "../../../../../helpers/utils";
import { ColorsMTO } from "../../../../../VectorFlow/Pages/MTO/Common/Colors";
import { } from "../../../../Services/MTA/MDM";
import { type Filter } from "../../../../types/MDM";
import VFTable from "../../Common/VFTable";
import { CustomStatusPanel } from "../CustomStatusPannel";
import CalenderModalCard from "./CalenderModalCard";
import {
  MTOPoogiTableContainer,
  PoogiAddButtonWrapper,
  PoogiSection,
  SCContainer,
  SCFilterAddButton,
  SCFilterAddButtonWrapper,
  SCFilterAddControls,
  SCFilterButtonGroup,
  SCFilterContainer,
  SCFilterControls,
  SCFilterSeperator,
  SCLegend,
} from "./styles";
import SubmitConflictModal from "./SubmitConflictModal";
import useViewModify from "./useViewModify";
import VFTaskBar from "./VFTaskbar";
import WarningModal from "./WarningModal";
import useSimpleBlocker from "./UseSimpleBlocker";
import OverlayLoader from "../../Common/Loader";
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard";


const MTOViewModify = () => {
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [isDisabledPoogi1,setIsDisabledPoogi1,] = useState(true)
  const [isDisabledPoogi2,setIsDisabledPoogi2,] = useState(true)


  // const disabled=true;
  // const dummyFn =()=>{return}

  const {
    isSelectMasterOpen,
    options,
    selectedOptions,
    activeMaster,
    filterButtonStatus,
    setFilterButtonStatus,
    handleSelectMasterSubmit,
    handleTabChange,
    handleTabClose,
    addNewMaster,
    handleOnAddFilter,
    handleOnDeleteFilter,
    allMastersState,
    isLoading,
    handleApplyFilter,
    isWarningModalOpen,
    toggleUploadModal,
    onWarningModalClose,
    onWarningModalSuccess,
    isOverlayVisible,
    isTableDataLoading,
    onBackButton,
    onClearExportError,
    agGridProps,
    ref,
    tempRef,
    tempAgGridProps,
    deleteSelected,
    plantNames,
    ccrNames,
    onSubmit,
    // isUploadButtonDisabled,
    editOnline,
    onEditOnline,
    onSaveToDraft,
    rowsPerPage,
    calendarFormData,
    onReset,
    onEditOnlineSave,
    conflictCount,
    errorCount,
    isConflictModalOpen,
    isShowAll,
    onIgnoreSubmitErrors,
    onReviewConflicts,
    onPIPOStatusUpdate,
    enableEditOnlineReset,
    submittedDataCount,
    uploadProgress,
    totalProgress,
    tempRecordCount,
    addRowToMtoGrid,
    onMTOSaveBufferData,
    onMTOSaveAsDraft,
    MTOPoogiMajorColdef,
    MTOPoogiMinorColdef,
    onMajReasonSelected,
    minReasonRowData,
    isModalOpen,
    setIsModalOpen,
    onMinReasonEditingStopped,
    addRowToMtoMinGrid,
    onSaveHandler,
    selectedData,
    setSelectedData,
    setCalendarFormData,
    getCombinedPoogiDataForExcelExport,
    onExcelExport,
    showModal,
    setShowModal,
    bufferDataConfirm,
    isAPILoading
  } = useViewModify("modify");

  useSimpleBlocker(activeMaster, onBackButton);
  
  const bufferModifyData = useSelector(
    (state: any) => state.mto.bufferModifyData
  );
  const ccrModifyData = useSelector((state: any) => state.mto.ccrModifyData);
  const editStatus: string = useSelector((state: any) => state.mto.editStatus);

  const handleExportData = useCallback(() => {
    notifyLoader('Exporting Data')
    try {
      ref?.current?.api?.exportDataAsExcel(onExcelExport());
      notifySuccess('Exported Data Successfully')
    } catch (error:any) {
      notifyError(error.message || "Failed to Export Data")
    }
  }, [ref, onExcelExport]);
  
  const calendarOnClickHandler = () => {
      setCalendarFormData({
        iwd: true,
        dsc: "",
        rb: "Once",
        sd: "",
        dow: [{id: 0, mn: "", md: ""}],
        ccr_id : [],
        plid: "",
        rd: null,
        plnm:"",
        ccr:"",
        ed: "",
        hid: uuidv4(),
        ia:false,
        id:false,
        iu:false,
      });
      setIsModalOpen(true);
  };


  useEffect(() => {
    if (ref.current && ref.current.api) {
      if (isTableDataLoading) {
        ref.current?.api.showLoadingOverlay();
      } else {
        ref.current?.api.hideOverlay();
      }
    }
  }, [isTableDataLoading]);


  const tempRefPoogi = React.useRef<any>(null);

  const clearGridFilterPoogi1 = () =>{
    ref?.current?.api.setFilterModel(null);
      setIsDisabledPoogi1(true);
  }
  const clearGridFilterPoogi2 = () =>{
    tempRefPoogi?.current?.api.setFilterModel(null);
    setIsDisabledPoogi2(true);
  }

  const isDataModified = () => {
    const bufferData = bufferModifyData?.filter((ele: any) => !ele.isdel);
    const ccrData = ccrModifyData?.filter((ele:any)=> !ele.isdel)

    const bufferModifiedDataExists = (activeMaster.id === 501 && !(bufferData && bufferData?.length > 0));
    const CCRModifiedDataExists = (activeMaster.id === 502 && !(ccrData && ccrData?.length > 0));
    
    return bufferModifiedDataExists || CCRModifiedDataExists;
  }

  return (
    <>
      <SCContainer>
        {(isAPILoading) && (
          <div>
            <OverlayLoader></OverlayLoader>
          </div>
        )}
        {isSelectMasterOpen && (
          <div style={{ zoom: 0.8 }}>
            <SelectMaster
              data={allMastersState}
              options={options}
              selectedOptions={selectedOptions}
              filterButtonStatus={filterButtonStatus}
              setFilterButtonStatus={setFilterButtonStatus}
              themeUi={themeUi}
              isLoading={isLoading}
              handleSubmit={() => {
                handleSelectMasterSubmit();
              }}
            />
          </div>
        )}
        {!isSelectMasterOpen && (
          <React.Fragment>
            <VFTab
              activeMaster={activeMaster}
              themeUi={themeUi}
              onTabChange={handleTabChange}
              onTabClose={handleTabClose}
              newTabTitle={"Add Master"}
              newTabIcon={"/assets/img/VectorFLOW/BPR/add-circle.svg"}
              newTabHandler={addNewMaster}
            >
              {(activeMaster.progress === "default" ||
                activeMaster.progress === "view") && (
                <SCFilterContainer style={{ zoom: 0.8, display: "none" }}>
                  <SCFilterControls>
                    <SCLegend>Filter</SCLegend>
                    {activeMaster.filters.map((f: Filter) => {
                      if (f.masterId == activeMaster?.id) {
                        return (
                          <VFFilter
                            onDelete={() => {
                              handleOnDeleteFilter(f.id);
                            }}
                            operators={operators}
                            filters={activeMaster.filters}
                            fields={generateMTOFilterOptions(
                              [activeMaster],
                              activeMaster.filters
                            )}
                            currFilter={f}
                            key={f.id}
                            isDisabled={false}
                          />
                        );
                      }
                    })}
                  </SCFilterControls>
                  <SCFilterAddControls>
                    {activeMaster.filters.map((f: Filter, index: number) => {
                      if (f.masterId === activeMaster?.id && index === 0) {
                        return (
                          <SCFilterAddButtonWrapper key={index}>
                            <SCFilterAddButton
                              onClick={() => {
                                handleOnAddFilter();
                              }}
                              src={
                                themeUi === "REGALBLAZE"
                                  ? "/assets/img/VectorFLOW/NMS/add-filter-regal.svg"
                                  : "/assets/img/VectorFLOW/NMS/add-filter.svg"
                              }
                              key={f.id}
                              data-testid="add-filter"
                            />
                          </SCFilterAddButtonWrapper>
                        );
                      }
                    })}
                  </SCFilterAddControls>
                  <SCFilterSeperator />
                  <SCFilterButtonGroup>
                    <VFButton
                      disabled={!areMasterFiltersValid(activeMaster.filters)}
                      themeUi={themeUi}
                      onClick={() => {
                        handleApplyFilter();
                      }}
                    >
                      Apply Filter
                    </VFButton>
                  <>
                    {(isTableDataLoading) && (
                      <div>
                          <OverlayLoader></OverlayLoader>
                      </div>
                    )}
                    <VFButtonOutline
                      onClick={() => handleApplyFilter(true)}
                      themeUi={themeUi}
                    >
                      {areMasterFiltersValid(activeMaster.filters)
                        ? "Clear Filters"
                        : "Show All"}
                    </VFButtonOutline>
                  </>
                  </SCFilterButtonGroup>
                </SCFilterContainer>
              )}
              {activeMaster?.isMTO && activeMaster?.id === 503 ? (
                <PoogiSection>
                  <MTOPoogiTableContainer
                    id="myGrid"
                    style={{ display: "flex", height: "50%", flex: "1" }}
                  >
                    <VFTable
                      
                      ref={ref}
                      columnDefs={MTOPoogiMajorColdef}
                      rowData={activeMaster.rowData}
                      {...agGridProps}
                      statusBar={{
                        statusPanels: [
                          {
                            statusPanel: "agTotalAndFilteredRowCountComponent",
                            align: "left",
                          },
                          {
                                    statusPanel: CustomStatusPanel,
                                    key: 'clearGridFilters',
                                    align:'right',
                                    statusPanelParams: {
                                      isDisabled: isDisabledPoogi1,
                                      clearGridFilter:clearGridFilterPoogi1,
                                      themeUi,
                                    },  
                          },
                          {
                            statusPanel: "agTotalRowCountComponent",
                            align: "left",
                          },
                          {
                            statusPanel: "agFilteredRowCountComponent",
                            align: "left",
                          },
                          {
                            statusPanel: "agSelectedRowCountComponent",
                            align: "left",
                          },
                          {
                            statusPanel: "agAggregationComponent",
                            align: "left",
                          },
                        ],
                      }}
                      defaultColDef={{ ...agGridProps.defaultColDef, flex: 1 }}
                      rowSelection={"single"}
                      tabToNextCell={()=>{
                        return null;
                      }}
                      onCellKeyDown={(e:any)=>{
                        if(e.event.key === 'Tab'){
                          return;
                        }
                      }}
                      suppressRowClickSelection={
                        activeMaster.colDefs.some(
                          (colDef) =>
                            colDef.field === "actions" ||
                            colDef.field === "pactions"
                        )
                          ? true
                          : false
                      }
                      onSelectionChanged={onMajReasonSelected}
                      height={
                        activeMaster.rowData?.length > 0
                          ? activeMaster.progress === "view"
                            ? "90%"
                            : "95%"
                          : "90%"
                      }
                      onFilterChanged={() => {
                        if(ref && ref.current && ref.current.api){
        
                          Object.keys(ref.current.api.getFilterModel())?.length > 0
                            ? setIsDisabledPoogi1(false)
                            : setIsDisabledPoogi1(true);
                        }
                      }}
                    />
                    <VFTable
                      columnDefs={MTOPoogiMinorColdef}
                      rowData={minReasonRowData}
                      ref={tempRefPoogi}
                      {...agGridProps}
                      tabToNextCell={()=>{
                        return null;
                      }}
                      onCellKeyDown={(e:any)=>{
                        if(e.event.key === 'Tab'){
                          return;
                        }
                      }}
                      statusBar={{
                        statusPanels: [
                          
                          {
                            statusPanel: CustomStatusPanel,
                            key: 'clearGridFilters',
                            align:'right',
                            statusPanelParams: {
                              isDisabled: isDisabledPoogi2,
                              clearGridFilter:clearGridFilterPoogi2,
                              themeUi,
                            },  
                          },
                          {
                            statusPanel: "agTotalAndFilteredRowCountComponent",
                            align: "left",
                          },
                          {
                            statusPanel: "agTotalRowCountComponent",
                            align: "left",
                          },
                          {
                            statusPanel: "agFilteredRowCountComponent",
                            align: "left",
                          },
                          {
                            statusPanel: "agSelectedRowCountComponent",
                            align: "left",
                          },
                          {
                            statusPanel: "agAggregationComponent",
                            align: "left",
                          },
                        ],
                      }}
                      defaultColDef={{ ...agGridProps.defaultColDef, flex: 1 }}
                      height={
                        activeMaster.rowData?.length > 0
                          ? activeMaster.progress === "view"
                            ? "90%"
                            : "95%"
                          : "90%"
                      }
                      overlayNoRowsTemplate={
                        "Select a major reason to see the corresponding minor reason"
                      }
                      onCellEditingStopped={onMinReasonEditingStopped}
                      suppressRowClickSelection={true}
                      onFilterChanged={() => {
                        if(tempRefPoogi && tempRefPoogi.current && tempRefPoogi.current.api){
        
                          Object.keys(tempRefPoogi.current.api.getFilterModel())?.length > 0
                            ? setIsDisabledPoogi2(false)
                            : setIsDisabledPoogi2(true);
                        }
                      }}

                    />
                  </MTOPoogiTableContainer>
                  <PoogiAddButtonWrapper>
                    <button
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        width: "90px",
                        margin: "8px",
                        cursor: "pointer",
                        background: "#fff",
                      }}
                      onClick={() => {
                        !activeMaster.colDefs.some(
                          (x) => x.field === "actions" || x.field === "pactions"
                        ) && addRowToMtoGrid();
                      }}
                    >
                      {!activeMaster.colDefs.some(
                        (x) => x.field === "actions" || x.field === "pactions"
                      ) ? (
                        <>
                          <img
                            src="/assets/img/AddBufferMasterIcon.svg"
                            alt="Add Master Button"
                          />
                          <p
                            style={{
                              fontSize: "10px",
                              color: ColorsMTO.Pink.code,
                            }}
                          >
                            Add Major Reason
                          </p>
                        </>
                      ) : (
                        <>
                          <img
                            src="/assets/img/AddBufferMasterIconGrey.svg"
                            alt="Add Master Button"
                          />
                          <p
                            style={{
                              fontSize: "10px",
                              color: ColorsMTO.LightGrey.code,
                            }}
                          >
                            Add Major Reason
                          </p>
                        </>
                      )}
                    </button>
                    <button
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        width: "90px",
                        margin: "8px",
                        cursor: "pointer",
                        background: "#fff",
                      }}
                      onClick={() => {
                        !activeMaster.colDefs.some(
                          (x) => x.field === "actions" || x.field === "pactions"
                        ) &&
                          ref &&
                          ref.current &&
                          ref?.current?.api?.getSelectedRows()?.length > 0 &&
                          addRowToMtoMinGrid();
                      }}
                    >
                      {!activeMaster.colDefs.some(
                        (x) => x.field === "actions" || x.field === "pactions"
                      ) &&
                      ref &&
                      ref.current &&
                      ref?.current?.api?.getSelectedRows()?.length > 0 ? (
                        <>
                          <img
                            src="/assets/img/AddBufferMasterIcon.svg"
                            alt="Add Master Button"
                          />
                          <p
                            style={{
                              fontSize: "10px",
                              color: ColorsMTO.Pink.code,
                            }}
                          >
                            Add Minor Reason
                          </p>
                        </>
                      ) : (
                        <>
                          <img
                            src="/assets/img/AddBufferMasterIconGrey.svg"
                            alt="Add Master Button"
                          />
                          <p
                            style={{
                              fontSize: "10px",
                              color: ColorsMTO.LightGrey.code,
                            }}
                          >
                            Add Minor Reason
                          </p>
                        </>
                      )}
                    </button>
                  </PoogiAddButtonWrapper>
                </PoogiSection>
              ) : (
                <VFTable
                  ref={ref}
                  columnDefs={activeMaster.colDefs}
                  rowData={activeMaster.rowData}
                  {...agGridProps}
                  suppressPaginationPanel={false}
                  height={
                    activeMaster?.rowData?.length > 0
                      ? activeMaster.progress === "view"
                        ? "65%"
                        : "95%"
                      : "75%"
                  }
                  readOnlyEdit
                  maintainColumnOrder
                />
              )}
              {/* {
                (!['default'].includes(activeMaster.progress) && (!isDataAvailableLocally && !isSelectMasterOpen) && !(activeMaster.id===503))
                &&
                <VFPagination
                  selectedRows={selectedRowsCount}
                  totalRows={recordCount}
                  currentPage={currentPage}
                  rowsPerPage={rowsPerPage}
                  handleChangePage={(e) => handleChangePage(e)}
                />
              } */}
              {/* <VFTable
                  ref={veryTempRef}
                  columnDefs={activeMaster.colDefs}
                  rowData={activeMaster.rowData}
                  enableBrowserTooltips={true}
                /> */}
              <div style={{ display: "none" }}>
                <VFTable
                  ref={tempRef}
                  rowData={getCombinedPoogiDataForExcelExport()}
                  columnDefs={[...MTOPoogiMajorColdef, ...MTOPoogiMinorColdef].filter((ele)=>ele.field!=='Warning' && ele.field!=='Error')}
                  {...tempAgGridProps}
                />
                
              </div>
              {activeMaster.isMTO && activeMaster.id !== 503 && (
                <>
                  <button
                    style={{
                      display: "flex",
                      justifyContent: "left",
                      gap: "8px",
                      width: "110px",
                      margin: "8px",
                      cursor:  "pointer",
                      background: "#fff",
                    }}
                    // disabled={activeMaster?.rowData?.length === 0}
                    onClick={() => {
                      
                        if (activeMaster.id !== 504) {
                          addRowToMtoGrid();
                        }
                        else{
                          calendarOnClickHandler();
                        }
                      }
                    
                    }
                  >
                    
                      <>
                        <img
                          src="/assets/img/AddBufferMasterIcon.svg"
                          alt="Add Master Button"
                          height={14}
                          width={14}
                        />
                        <p
                          style={{
                            fontSize: "12px",
                            color: ColorsMTO.Pink.code,
                          }}
                        >
                          Add {activeMaster.name}
                        </p>
                      </>
                    
                  </button>
                </>
              )}
            </VFTab>
          </React.Fragment>
         )}
      </SCContainer>
      {isModalOpen && (
        <CalenderModalCard
          selectedData={selectedData}
          setSelectedData={setSelectedData}
          plantNames={plantNames}
          calendarFormData={calendarFormData}
          ccrNames={ccrNames}
          onSaveHandler={onSaveHandler}
          setIsModalOpen={setIsModalOpen}
          isModalOpen={isModalOpen} 
        />
      )}
      {isWarningModalOpen && (
        <WarningModal
          count={tempRecordCount}
          onCloseModal={onWarningModalClose}
          onFailure={onWarningModalClose}
          onSuccess={() => onWarningModalSuccess()}
          showAll={isShowAll}
          rowsPerPage={rowsPerPage}
        />
      )}
      {isConflictModalOpen && (
        <SubmitConflictModal
          totalCount={activeMaster.rowData?.length}
          modificationCount={conflictCount}
          errorCount={errorCount}
          recordCount={submittedDataCount}
          onSuccess={onReviewConflicts}
          onFailure={onIgnoreSubmitErrors}
          onCloseModal={() => {
            return;
          }}
        />
      )}
      {isOverlayVisible && (
        <VFOverlay>
          <div style={{ backgroundColor: "white", borderRadius: "6px" }}>
            <VFLoader />
            <h1
              style={{
                backgroundColor: "white",
                padding: "15px",
                borderRadius: "8px",
              }}
            >
              Validating Data. Please Wait this might take some time....{" "}
              {uploadProgress === "" || parseInt(uploadProgress) === 0
                ? ""
                : "Progress: " + uploadProgress + " / " + totalProgress}
            </h1>
          </div>
        </VFOverlay>
      )}
      {!isSelectMasterOpen && (
          <VFTaskBar
            showSubmittedExportError={errorCount > 0}
            // masterProgress={(!bufferModifyData)?"initial":(bufferModifyData?"editOnline":"editOnlineSubmitted")}
            masterProgress={editStatus}
            disableSubmit={activeMaster.rowData?.length === 0}
            enableEditOnlineReset={enableEditOnlineReset}
            disableDeleteSelected={activeMaster.rowData?.length < 1}
            onReset={onReset}
            onSaveToDraft={
              activeMaster.isMTO ? onMTOSaveAsDraft : onSaveToDraft
            }
            onEditOnlineSave={onEditOnlineSave}
            editOnline={editOnline}
            onEditOnline={() => onEditOnline("editOnline")}
            onBack={onBackButton}
            onClearAndExportErrors={onClearExportError}
            onModifyData={() => toggleUploadModal(true)}
            onExportData={() => {
              if(activeMaster.id === 503){
                tempRef?.current?.api &&
                tempRef?.current?.api.exportDataAsExcel({
                  fileName: `${activeMaster.name} (MTO)`,
                  columnKeys: [...MTOPoogiMajorColdef, ...MTOPoogiMinorColdef].filter((ele)=>ele.field!=='Warning' && ele.field!=='Error').map((col) => col.field)
                });
                return;
              }
              handleExportData();
            }}
            onSubmit={onSubmit}
            onSubmitConflictData={() => onSubmit(true)}
            onDeleteSelected={deleteSelected}
            onPhaseInPhaseOutStop={() => onPIPOStatusUpdate()}
            onDeleteData={() => console.log("")}
            onDeleteOnlineReset={() => console.log("")}
            onDeleteOnlineSubmit={() => console.log("")}
            onDeleteOnline={() => console.log("")}
            masterId={activeMaster.id}
            mtoSaveData={true}
            onMTOSaveData={onMTOSaveBufferData}
            isMTOSaveDataDisabled={isDataModified()}
            isMTODraftDisabled={
              (activeMaster.id === 501 &&
                !(bufferModifyData && bufferModifyData?.length > 0)) ||
              (activeMaster.id === 502 &&
                !(ccrModifyData && ccrModifyData?.length > 0))
            }
            onMTOSaveAsDraft={onMTOSaveAsDraft}
          />
      )}

    <VFModalCard key={"key2"} openModal={showModal} closeModal={() => { setShowModal(false) }} headerText={'Warning'} headerIcon={'/assets/img/ist/warning.svg'} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"} paddingLeftAndRight={0} headerTextColor={'black'} backgroundColor={'f4f4f4'} data-testid="vfmultifilter-img" >
        <div style={{ margin: "0 2rem" }}>
          <div style={{ minHeight: '10vh', fontSize: '16px', padding: "20px", textAlign: "center" }}>
            There is some incomplete data in your task <br /> Are you sure you want to save it without this data?
          </div>
          <div style={{ zoom: '0.7', display: 'flex', justifyContent: 'right', gap: '8px', borderTop: '2px dashed #A0A0A0', padding: '20px 20px 20px 0' }}>

            <VFButton onClick={() => { setShowModal(false) }} themeUi={themeUi}>
              Cancel
            </VFButton>
            <VFButtonOutline onClick={() => {
              setShowModal(false)
              bufferDataConfirm();
            }} themeUi={themeUi}>
              Yes
            </VFButtonOutline>
          </div>
        </div>
      </VFModalCard>
    </>
  );
};

export default MTOViewModify;
