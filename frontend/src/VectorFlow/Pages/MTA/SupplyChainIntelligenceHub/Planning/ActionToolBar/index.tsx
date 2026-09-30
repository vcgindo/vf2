import VFButton from "../../../../../../components/VectorFLOW/commons/VFButton";
import VFFloatingTab from "../../../../../../components/VectorFLOW/commons/VFFloatingTab";
import VFSelectedFilters from "../../../../../../components/VectorFLOW/commons/VFSelectedFilters";
import { useState, useMemo, useContext, useEffect } from "react";
import { useLocation, Link } from "react-router-dom";
import useSaveAllState from "../../../../../../hooks/useSaveAllState";
import Tooltip from '../../../../../../../src/VectorFlow/Pages/MTO/Common/Tooltip';
import {
  SCTaskBarContainer,
  SCGoBackContainer,
  SCGoBackText,
  SCViewContainer,
  SCViewBackground,
  SCVerticalDivider,
  SCViewImage,
  SCCustomActionsContainer,
  SCViewContainerWithBg,
  SCTaskFilterContainer,
  LastRunDateHeader,
} from "./styles";
import { useUserData } from "../../../../../../context/UserDataContext";
// import { DBMApplyNormChange } from "../../../DBM/DBMNormSuggestions/applyNormButton";
import { PlanningCounts } from "../../../../../../VectorFlow/types/MTA";
import VFButtonOutline from "../../../../../../components/VectorFLOW/commons/VFButtonOutline";
import { GridStateContext } from "../../../../../../context/GridStateContext";
import { useDispatch, useSelector } from "react-redux";
import { UPDATE_PLANNING_DATA } from "../../../../../../redux/actions/MTA";
import { RootState } from "../../../../../../redux/store/store";
import useGetLocation from "../../../../../../hooks/useGetLocation";
import { Skeleton } from "../../../../../../components/commons/styled";
import ConfirmationDataModal from "../../../DBM/DBMNormSuggestions/ConfirmationModal";
import MTAVFMultiFilter from "../../../Common/MTAVFMultiFilter";
import { UIColumnConfigName } from "../../../../../../helpers/Enum";

interface ActionToolBarProps {
  view: string;
  currentTab: string;
  setCurrentTab: any;
  currCategory?: any;
  tabsList: Array<{ id: string; label: string; value: string }>;
  onFloatingTabChange: (tab: any) => void;
  onGoBack: () => void;
  onViewChange: (view: string) => void;
  disableChartAndGridViewToggle?: boolean;
  showAllTick?: any;
  handleGoButton?: any;
  handleGoButtonForSleep?: any;
  onChangeHorizon?: (value: number) => void;
  onApplyFilter?: (params: any) => void;
  planningCount?: PlanningCounts;
  genericRecordCount: number;
  onExportToExcelCallBack: any;
  multiFilter: any;
  setMultiFilter: any;
  onDelete: any;
  horizon?:number
  onUpdateInsight?: () => void;
  hideUpdateInsightsBtn?: boolean;
  onSubmitEditedRows?: () => void;
  disableSubmitEditedRowsBtn?: boolean;
  lastRunDate?:string 
  isPlanning?:boolean,
  generalFilterOptions?:any
  
}

const ActionToolBar = ({
  view,
  currentTab,
  tabsList,
  onFloatingTabChange,
  onGoBack,
  onViewChange,
  currCategory,
  disableChartAndGridViewToggle,
  planningCount,
  showAllTick,
  handleGoButton,
  handleGoButtonForSleep,
  genericRecordCount,
  onExportToExcelCallBack,
  onApplyFilter,
  multiFilter,
  setMultiFilter,
  onDelete,
  horizon = 0,
  onUpdateInsight,
  hideUpdateInsightsBtn,
  onSubmitEditedRows,
  disableSubmitEditedRowsBtn,
  lastRunDate,
  isPlanning,
  onChangeHorizon,
  generalFilterOptions
}: ActionToolBarProps) => {

  const { user } = useUserData();
  const { ref } = useContext(GridStateContext);

  const {locations} = useGetLocation()
  // const {state:multiFilter,setState:setMultiFilter,onDelete} = useBPRFilter()
  const { onSaveState, onResetAllState,onExportToExcelOld} = useSaveAllState(isPlanning);
  const { currentCategory } = useSelector(
    (state: RootState) => state.mta.planning
  );
  const { pathname } = useLocation();
  const dispatch = useDispatch();

  const themeUi = user?.user?.theme_ui;
  const [isFilterOpen, toggleFilter] = useState<boolean>(false);
  const [isFilterButtonVisible,setIsFilterButtonVisible] = useState<boolean>(false);
  const [isConfirmationModalOpen, setIsConfirmationModalOpen] = useState<null | "norm" | "sleep">(null);
  const closeModal = () => setIsConfirmationModalOpen(null);
  const handleFailure = () => {
    closeModal();
  };
  const handleApplyFilter = (params: any) => {
    if (onApplyFilter) onApplyFilter(params);
    toggleFilter(false);
  };

  const getTotalFilterCount = (multiFilter: any) => {
    let total = 0;
    for (const key in multiFilter) {
      if (multiFilter[key]?.filters) {
        total += multiFilter[key].filters.length;
      }
    }
    return total;
  };
  const handleResetAllState = () => {
    onResetAllState(`${currCategory}${currentTab}`);
  };
  
  const [isNewFilterOpen, setIsFilterOpen] = useState(false);

  const handleApplyFilters = (filters: any) => {
    console.log('Applied filters:', filters);
    setIsFilterOpen(false);
    // You can pass these filters to your parent component or context
  };

  const handleResetFilters = () => {
    console.log('Filters reset');
    // Handle reset logic if needed beyond the modal
  };

  const currentPageRecordCount = useMemo(() => {
    switch (currCategory) {
      case "GITFromParent":
        return planningCount?.parentMonitorCount;
      case "GITToChild":
        return planningCount?.childMonitorCount;
      case "ExpediteFromParent":
        return planningCount?.parentExpediteCount;
      case "ExpediteToChild":
        return planningCount?.childExpediteCount;
      case "ExcessInventory":
        return planningCount?.reviewExcessInventoryCount;
      case "OrderFulfillment":
        return planningCount?.reviewOrderFulfillmentCount;
      default:
        return genericRecordCount;
    }
  }, [currCategory, currentTab, genericRecordCount]);

  const handleExportToExcel = () => {
    if (
      pathname === "/mta/supply-chain-intelligence-hub/open-expediting-requests"
    ) {
      ref.current.api.exportDataAsExcel({
        fileName: "OpenExpeditingRequests",
      });
    }

    // else if(pathname  === '/supply-chain-intelligence-hub/bpr'){
    //   onExportToExcel({
    //     // pagination: { recordCount: currentPageRecordCount || 0, chunkSize: 5000 },
    //     // callBack: onExportToExcelCallBack,
    //     name:currCategory + currentTab,
    //     filters:multiFilter
    //   });
    // }
    else if(pathname==="/mta/insights-and-trends/buffer-trend-report" || pathname=== "/mta/supply-chain-intelligence-hub/bpr" || pathname=== "/mta/supply-chain-intelligence-hub/rrr" || pathname==="/mta/supply-chain-intelligence-hub/bor" || pathname==="/mta/supply-chain-intelligence-hub/bor-color-bandwise" || pathname==="/mta/supply-chain-intelligence-hub/rrr-color-bandwise"){
      onExportToExcelCallBack();
    }
    else{
      onExportToExcelOld({
        pagination: { recordCount: currentPageRecordCount || 0, chunkSize: 5000 },
        callBack: onExportToExcelCallBack,
      });
    }
  };


  useEffect(() => {
    if (
      pathname !== "/mta/supply-chain-intelligence-hub/SupplierWiseAllocation" &&
      pathname !== "/mta/supply-chain-intelligence-hub/sdr" &&
      pathname !== "/mta/supply-chain-intelligence-hub/eo" &&
      pathname !== "/mta/supply-chain-intelligence-hub/total-requirement-report"
    ) {
      setIsFilterButtonVisible(true);
    }
    if(pathname === "/mta/insights-and-trends/buffer-trend-report" 
      ||  pathname === "/mta/insights-and-trends/buffer-trends"  
      || pathname === "/mta/supply-chain-intelligence-hub/bpr"
    || pathname === "/mta/supply-chain-intelligence-hub/rrr"
    || pathname ===  "/mta/supply-chain-intelligence-hub/rrr-color-bandwise"
    || pathname === "/mta/supply-chain-intelligence-hub/bor"
    || pathname === "/mta/supply-chain-intelligence-hub/bor-color-bandwise"
  ){
      toggleFilter(true);
    }
  }, [pathname]);

  const renderFilter = () => {
    switch (currCategory) {
      case "GITFromParent":
        return (
          <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}      
          />
        );
      case "GITToChild":
        return (
          <MTAVFMultiFilter
            isOpen={isFilterOpen}
            onApply={handleApplyFilter}
            multiFilter={multiFilter}
            onClose={() => toggleFilter(false)}
            onReset={handleResetFilters}      
          />
        );
      case "ExpediteFromParent":
        return (
          <MTAVFMultiFilter
            isOpen={isFilterOpen}
            onApply={handleApplyFilter}
            multiFilter={multiFilter}
            onClose={() => toggleFilter(false)}
            onReset={handleResetFilters}      
          />
        );
      case "ExpediteToChild":
        return (
          <MTAVFMultiFilter
            isOpen={isFilterOpen}
            onApply={handleApplyFilter}
            multiFilter={multiFilter}
            onClose={() => toggleFilter(false)}
            onReset={handleResetFilters}      
          />
        );
      case "ExcessInventory":
        return (
            <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters} 
            />
        );
      case "OrderFulfillment":
        return (
            <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}      
              reportType="OrderFulfillment"     
            />
        );
      case "BPR":
        if (pathname === "/mta/supply-chain-intelligence-hub/bpr") {
          return (

            <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}
              currCategory={currCategory}
              reportName={UIColumnConfigName.BPR}
            />
          );
        }
        break;
      case "RRR":
        if (pathname === "/mta/supply-chain-intelligence-hub/rrr") {
          return (
             <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}      
              currCategory={currCategory}
              reportName={UIColumnConfigName.RRR}
            />
          );
        }
        break;
      case "RRRColorBandwise":
        if (pathname === "/mta/supply-chain-intelligence-hub/rrr-color-bandwise") {
          return (
              <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}   
              reportName={UIColumnConfigName.RRR_OA}
            />
          );
        }
        break;
      // case "SDR":
      //   if (pathname === "/supply-chain-intelligence-hub/sdr") {
      //     return (
      //       <VFMultiFilter
      //       isFilterOpen={isFilterOpen}
      //         onApplyFilter={handleApplyFilter}
      //         onGoBack={() => toggleFilter(false)}
      //         multiFilter={multiFilter}
      //         setMultiFilter={setMultiFilter}
      //         productFilterActive={true}
      //         locationFilterActive={true}
      //         generalFilterActive={false}
      //         generalFilterOptions={generalFilterOptions}
      //         availabilityFilterActive={true}
      //         supplyChainNodeFilterActive={true}
      //         supplyChainForLocationCheckBoxList={
      //           locations
      //         }
      //         supplyChainForChildrenOfCheckBoxList={locations.filter(
      //           (m:any) => ['plant', 'CWH', 'RWH'].includes(m.id)
      //         )}
      //       />
      //     );
      //   }
      //   break;
      case "BOR":
        if (pathname === "/mta/supply-chain-intelligence-hub/bor") {
          return (
              <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}   
              currCategory={currCategory}
              reportName={UIColumnConfigName.BOR}
            />
          );
        }
        break;
      case "BORColorBandwise":
        if (pathname === "/mta/supply-chain-intelligence-hub/bor-color-bandwise") {
          return (
             <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}   
              reportName={UIColumnConfigName.BOR_OA}
            />
          );
        }
        break;
        
      case "OrderAllocationReport":
        if (pathname === "/mta/supply-chain-intelligence-hub/order-allocation-report") {
          return (
          <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}   
              reportName={UIColumnConfigName.OAR}
            />
          );
        }
        break;
      case "BTR":
        if (pathname === "/mta/insights-and-trends/buffer-trend-report" && onChangeHorizon) {
          return (
             <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}
              currentTab={currentTab}
              reportName={UIColumnConfigName.BuffertrendReport}
            />
          );
        }
        break;
      case "BufferTrend":
        if (pathname === "/mta/insights-and-trends/buffer-trends") {
          return (
              <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}
                    
            />
          );
        }
        break;
      case "ResearchInsight":
        if (pathname === "/mta/insights-and-trends/research-insights") {
          return (
             <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}      
            />
          );
        }
        break;
      case "GuidedInsight":
        if (pathname === "/mta/insights-and-trends/guided-insights") {
          return (
            <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}      
            />
          );
        }
        break;
      case "DBMNorm":
        if (pathname === "/mta/dbm/dbm-norm-suggestions") {
          return (
        <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}  
              reportName={UIColumnConfigName.DBM}
            />
          );
        }
        break;
      case "OpenExpeditingRequests":
        if (
          pathname === "/mta/supply-chain-intelligence-hub/open-expediting-requests"
        ) {
          return (
           <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}     
              reportName={UIColumnConfigName.OER}
            />
          );
        }
        break;
      case "InTransitWhereabouts":
        if (pathname === "/mta/logistics/intransit-whereabouts") {
          return (
           <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}      
            />
          );
        }
        break;
      case "chronicunavailability":
        return (
            <MTAVFMultiFilter
              isOpen={isFilterOpen}
              onApply={handleApplyFilter}
              multiFilter={multiFilter}
              onClose={() => toggleFilter(false)}
              onReset={handleResetFilters}      
            />
        );
      default:
        <></>;
    }
  };

    const handleGIExportExcel = () => {
      ref?.current?.api?.exportDataAsExcel({
          fileName:  'ChronicUnavailabilityexport.xlsx', 
      });
  };

  const renderFloatingTab = () => {
    return (
      <VFFloatingTab
        tabs={tabsList}
        
        defaultTab={
          tabsList.findIndex((object) => {
            return object.value === currentTab;
          }) == -1
            ? 0
            : tabsList.findIndex((object) => {
                return object.value === currentTab;
              })
        }
        handleClick={onFloatingTabChange}
      />
    );
  };
  return (
    <>
      {view === "chart" && (
        <SCTaskBarContainer>
          {currCategory === "GuidedInsight" ? null : (
            <SCGoBackContainer onClick={onGoBack}>
              <img src="/assets/img/VectorFLOW/BPR/goback.svg" alt="" />
              <SCGoBackText>
                <b>Go Back</b>
              </SCGoBackText>
            </SCGoBackContainer>
          )}

          <SCTaskFilterContainer
          
            style={{
              maxWidth: currCategory === "GuidedInsight" ? "100%" : "50%",
              width: currCategory === "GuidedInsight" ? "100%" : "unset",
              justifyContent:
                currCategory === "GuidedInsight" ? "flex-start" : "unset",
              marginLeft: "10px",
            }}
          >
            {tabsList.length > 0 && renderFloatingTab()} 

            {currCategory === "GuidedInsight" && (
          <div
            style={{marginLeft: "-10px", maxWidth:'40%'}}>
            <VFSelectedFilters filters={multiFilter} onRemoveFilter={onDelete} />
          </div>
          )}
          </SCTaskFilterContainer>

          <SCCustomActionsContainer>
            {/* currentTab === "chronicunavailability" || || currentTab==="dbmnormsuggestions" || currentTab === "excessinventorytrend" */}
          {( currentTab === "availabilitytrend"|| currentTab === "availabilityageingtrend" ) &&
               <>
                  <VFButton onClick={() => toggleFilter(true)} themeUi={themeUi} disabled={false}>
                    {getTotalFilterCount(multiFilter) > 0 ? "Edit Filter" : "Add Filter"}
                  </VFButton>
                  {isFilterOpen && renderFilter()}
                </>
            }
            {currentTab === "dbmnormsuggestions" && (
              <>
                <Link
                  to="/mta/dbm/dbm-norm-suggestions"
                  style={{ textDecoration: "none" }}
                >
                  <VFButtonOutline
                    onClick={() => toggleFilter(true)}
                    themeUi={themeUi}
                    width={140}
                    disabled={false}
                    color={themeUi === "REGALBLAZE" ? "#FCA311" : "#bc3d81"}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "5px",
                      paddingLeft: "12px",
                      paddingRight: "13px",
                    }}
                  >
                    <img
                      src={
                        themeUi === "REGALBLAZE"
                          ? "/assets/img/VectorFLOW/BPR/NormAction-regal.svg"
                          : "/assets/img/VectorFLOW/BPR/NormAction.svg"
                      }
                    ></img>
                    Norm Action
                  </VFButtonOutline>
                </Link>
                {/* <SCVerticalDivider/> */}
              </>
            )}

            {currentTab === "custom" && (
              <>
                <SCViewContainerWithBg
                  onClick={() =>
                    ref.current.api.exportDataAsExcel({
                      fileName: `${currentCategory}${currentTab}`,
                    })
                  }
                >
                  <SCViewImage
                    src={
                      themeUi === "REGALBLAZE"
                        ? "/assets/img/VectorFLOW/BPR/excel-regal.svg"
                        : "/assets/img/VectorFLOW/BPR/excel.svg"
                    }
                    alt=""
                  />
                  <p>Excel Export</p>
                </SCViewContainerWithBg>
                <SCVerticalDivider />
              </>
            )}
            {
              // ( currentTab==="availabilitytrend" || currentTab==="availabilityageingtrend" || currentTab==="dbmnormsuggestions"  || currentTab==='custom' ) &&
              currentTab === "custom" && (
                <>
                  <SCViewContainerWithBg
                    onClick={() => onSaveState(`${currCategory}${currentTab}`)}
                  >
                    <SCViewImage
                      src={
                        themeUi === "REGALBLAZE"
                          ? "/assets/img/VectorFLOW/BPR/diskette-regal.svg"
                          : "/assets/img/VectorFLOW/BPR/diskette.svg"
                      }
                      alt=""
                    />
                    <p>Save Layout</p>
                  </SCViewContainerWithBg>
                  <SCViewContainerWithBg
                    onClick={() =>
                      handleResetAllState()
                    }
                  >
                    <SCViewImage
                      src={
                        themeUi === "REGALBLAZE"
                          ? "/assets/img/VectorFLOW/BPR/refresh-regal.svg"
                          : "/assets/img/VectorFLOW/BPR/refresh.svg"
                      }
                      alt=""
                    />
                    <p>Reset Layout</p>
                  </SCViewContainerWithBg>
                  {!disableChartAndGridViewToggle && <SCVerticalDivider />}
                </>
              )
            }

            {!disableChartAndGridViewToggle && (
              <>
                {/* <SCVerticalDivider/> */}
                <SCViewBackground>
                  <SCViewContainer>
                    <SCViewImage
                      src={
                        themeUi === "REGALBLAZE"
                          ? "/assets/img/VectorFLOW/BPR/chart-view-regal.svg"
                          : "/assets/img/VectorFLOW/BPR/chart-view-pink.svg"
                      }
                      alt=""
                    />
                    <p
                      style={{
                        color: themeUi === "REGALBLAZE" ? "#FCA311" : "#bc3d81",
                      }}
                    >
                      Chart View
                    </p>
                  </SCViewContainer>
                  <div>
                    <SCVerticalDivider />
                  </div>
                  <SCViewContainer
                    onClick={() => {
                      onViewChange("grid");
                      dispatch(
                        UPDATE_PLANNING_DATA({
                          currentTab: currentTab,
                          currentCategory: currentCategory,
                          currentView: "grid",
                        })
                      );
                    }}
                  >
                    <SCViewImage
                      src={"/assets/img/VectorFLOW/BPR/grid-view-grey.svg"}
                      alt=""
                    />
                    <p style={{ color: "#b0acac" }}>Grid View</p>
                  </SCViewContainer>
                </SCViewBackground>
              </>
            )}
          </SCCustomActionsContainer>
        </SCTaskBarContainer>
      )}

     

      {view === "grid" && (
        <SCTaskBarContainer>
          <SCTaskFilterContainer
            style={{
              maxWidth: currCategory === "GuidedInsight" ? "100%" : "50%",
              width: currCategory === "GuidedInsight" ? "100%" : "unset",
              justifyContent:
                currCategory === "GuidedInsight" ? "flex-start" : "unset",
            }}
          >
            {currCategory === "GITFromParent" ||
            currCategory === "GITToChild" ||
            currCategory === "ExpediteFromParent" ||
            currCategory === "ExpediteToChild" ||
            currCategory === "ExcessInventory" ||
            currCategory === "OrderFulfillment" ? (
              <SCGoBackContainer onClick={onGoBack}>
                <img
                  src="/assets/img/VectorFLOW/BPR/goback.svg"
                  alt=""
                  onClick={onGoBack}
                />
                <SCGoBackText>
                  <b>Go Back</b>
                </SCGoBackText>
              </SCGoBackContainer>
            ) : null}

            {currCategory === "DBMNorm" && (
              <VFButton onClick={() => setIsConfirmationModalOpen("norm")} themeUi={themeUi}>
                Norm Changes
              </VFButton>
            )}

            {currCategory === "DBMNorm" && (
              <VFButton onClick={() => setIsConfirmationModalOpen("sleep")} themeUi={themeUi}>
                Sleep
              </VFButton>
            )}

            {isConfirmationModalOpen === "norm" && (
            <ConfirmationDataModal
              mode={isConfirmationModalOpen}
              onSuccess={handleGoButton}
              onFailure={handleFailure}
              onCloseModal={closeModal}
            />
          )}

          {isConfirmationModalOpen === "sleep" && (
            <ConfirmationDataModal
              mode={isConfirmationModalOpen}
              onSuccess={handleGoButtonForSleep}
              onFailure={handleFailure}
              onCloseModal={closeModal}
            />
          )}

            {/* (currCategory === 'GuidedInsight' && view!=='grid') :null ?
            <VFSelectedFilters filters={multiFilter} onRemoveFilter={onDelete}></VFSelectedFilters> */}
            {/* }
            {/* {tabsList.length > 0 && renderFloatingTab()} */}

            {tabsList.length > 0 && renderFloatingTab()}
            {/* {onSubmitEditedRows && (
                                 <VFButtonOutline disabled={disableSubmitEditedRowsBtn} themeUi={themeUi} width={169} style={{fontSize:'20px', fontWeight:'500'}} onClick={onSubmitEditedRows}>Save  Changes</VFButtonOutline> 
                            )} */}

            {currCategory === "GuidedInsight" && view === "grid" ? (
              <div style={{ marginRight: "60px", maxWidth: "400px" }}>
                <VFSelectedFilters
                  filters={multiFilter}
                  onRemoveFilter={onDelete}
                ></VFSelectedFilters>
              </div>
            ) : (currCategory === "GuidedInsight" && view !== "grid") ||
              currCategory === "ResearchInsight" ? null : (
              <VFSelectedFilters
                filters={multiFilter}
                onRemoveFilter={onDelete}
              ></VFSelectedFilters>
            )}

            {/* {currCategory === "BPR" && onSubmitEditedRows && (
              <VFButtonOutline
                onClick={onSubmitEditedRows}
                themeUi={themeUi}
                disabled={disableSubmitEditedRowsBtn}
              >
                Save Remarks
              </VFButtonOutline>
            )} */}
            
            {/* {(currCategory === "BPR" || currCategory === "BOR" || currCategory === "BORColorBandwise") && onSubmitEditedRows && (
              <VFButtonOutline
                onClick={onSubmitEditedRows}
                themeUi={themeUi}
                disabled={disableSubmitEditedRowsBtn}
              >
                Save Remarks
              </VFButtonOutline>
            )} */}


            {currCategory === "ResearchInsight" && (
              <>
                {!hideUpdateInsightsBtn && (
                  <VFButtonOutline
                    themeUi={themeUi}
                    width={169}
                    style={{ fontSize: "20px", fontWeight: "500" }}
                    onClick={() => (onUpdateInsight ? onUpdateInsight() : {})}
                  >
                    Update Insight
                  </VFButtonOutline>
                )}
                <VFSelectedFilters
                  filters={multiFilter}
                  onRemoveFilter={onDelete}
                  style={{ maxWidth: "700px" }}
                ></VFSelectedFilters>
              </>
            )}
          </SCTaskFilterContainer>
          {/* {(currCategory==='BPR' && lastRunDate) && (
            lastRunDate === "Loading"?(
              <Skeleton style={{height:30,width:150}}/>
            ):(
              <LastRunDateHeader>{lastRunDate}</LastRunDateHeader>
            )
          )} */}
          <SCCustomActionsContainer>

          {( pathname != "/mta/supply-chain-intelligence-hub/SupplierWiseAllocation" && pathname != "/mta/supply-chain-intelligence-hub/sdr" && pathname !== "/mta/supply-chain-intelligence-hub/total-requirement-report" && pathname != "/mta/supply-chain-intelligence-hub/eo" ) && currentTab !== "custom" &&
               <>
                    <VFButton
                    onClick={() => toggleFilter(true)}
                    themeUi={themeUi}
                    disabled={false}
                  >
                      {getTotalFilterCount(multiFilter) > 0 ? "Edit Filter" : "Add Filter"}
                  </VFButton> 
                  {isFilterOpen && renderFilter()}
                </>
            
            }

            {/* <VFButton themeUi={themeUi} onClick={()=>console.log("test")}>   Edit Filter</VFButton> */}

            {currCategory === "BufferTrend" ? null : (
              <>
                {currCategory === "GuidedInsightchronicunavailability" ||
                ((currCategory === "BTR" && currentTab === "both")  ) ? null : (
                  <>
                    {isFilterButtonVisible && <SCVerticalDivider />}
                    {/* <SCViewContainerWithBg onClick={handleExportToExcel}> */}
                    <SCViewContainerWithBg onClick={() => {currCategory === "GuidedInsight" ? handleGIExportExcel() : handleExportToExcel()}}>
                      <>
                        <SCViewImage
                          src={
                            themeUi === "REGALBLAZE"
                              ? "/assets/img/VectorFLOW/BPR/excel-regal.svg"
                              : "/assets/img/VectorFLOW/BPR/excel.svg"
                          }
                          alt=""
                        />
                         <p>{(currCategory === "BTR" || currCategory === "BPR" || currCategory === "RRR" ||  currCategory === "BOR" || currCategory === "BORColorBandwise" || currCategory === "RRRColorBandwise") ? "CSV Export" : "Excel Export"}</p>
                      </>
                      {/* <SCViewImage src={"/assets/img/VectorFLOW/BPR/excel.svg"} alt="" onClick={onGoBack} />
                                    <p>Excel Export</p> */}
                    </SCViewContainerWithBg>
                  </>
                )}
                {(currCategory === "GuidedInsight" &&
                  currentTab === "chronicunavailability") ||
                (currCategory === "BTR" && currentTab === "both") ? null : (
                  <>
                    <SCVerticalDivider />
                    <SCViewContainerWithBg
                      onClick={() =>
                        onSaveState(`${currCategory}${currentTab}`)
                      }
                    >
                      <SCViewImage
                        src={
                          themeUi === "REGALBLAZE"
                            ? "/assets/img/VectorFLOW/BPR/diskette-regal.svg"
                            : "/assets/img/VectorFLOW/BPR/diskette.svg"
                        }
                        alt=""
                      />
                      <p>Save Layout</p>
                    </SCViewContainerWithBg>
                    <SCViewContainerWithBg
                      onClick={() =>
                        handleResetAllState()
                      }
                    >
                      <SCViewImage
                        src={
                          themeUi === "REGALBLAZE"
                            ? "/assets/img/VectorFLOW/BPR/refresh-regal.svg"
                            : "/assets/img/VectorFLOW/BPR/refresh.svg"
                        }
                        alt=""
                      />
                      <p>Reset Layout</p>
                    </SCViewContainerWithBg>
                    {/* {!disableChartAndGridViewToggle && <SCVerticalDivider/> } */}
                    {!disableChartAndGridViewToggle &&
                      (currCategory === "ExcessInventory" ||
                      currCategory === "GITToChild" ||
                      currCategory === "OrderFulfillment" ||
                      currCategory === "ExpediteToChild" ||
                      currCategory === "ExpediteFromParent" ? (
                        <SCVerticalDivider />
                      ) : null)}
                  </>
                )}
              </>
            )}

            {currCategory === "CustomScreens" ||
            currCategory === "BufferTrend" ||
            currCategory === "BPR" ||
            currCategory === "SDR" ||
            currCategory === "EO" ||
            currCategory === "RRR" ||
            currCategory === "BOR" ||
            currCategory === "BTR" ||
            currCategory === "ResearchInsight" ||
            currCategory === "DBMNorm" ||
            (currCategory === "GuidedInsight" &&
              currentTab !== "chronicunavailability") ||
            currCategory === "OpenExpeditingRequests" ||
            currCategory === "InTransitWhereabouts"
              ? null
              : !disableChartAndGridViewToggle && (
                  <>
                    <SCViewBackground>
                      <SCViewContainer
                        onClick={() => {
                          onViewChange("chart");
                          dispatch(
                            UPDATE_PLANNING_DATA({
                              currentTab: currentTab,
                              currentCategory: currentCategory,
                              currentView: "chart",
                            })
                          );
                        }}
                      >
                        <SCViewImage
                          src={"/assets/img/VectorFLOW/BPR/chart-view-grey.svg"}
                          alt=""
                        />
                        <p style={{ color: "#b0acac" }}>Chart View</p>
                      </SCViewContainer>
                      <div>
                        <SCVerticalDivider />
                      </div>

                      <SCViewContainer>
                        <SCViewImage
                          src={
                            themeUi === "REGALBLAZE"
                              ? "/assets/img/VectorFLOW/BPR/grid-view-regal.svg"
                              : "/assets/img/VectorFLOW/BPR/grid-view-pink.svg"
                          }
                          alt=""
                          onClick={onGoBack}
                        />
                        <p
                          style={{
                            color:
                              themeUi === "REGALBLAZE" ? "#FCA311" : "#bc3d81",
                          }}
                        >
                          Grid View
                        </p>
                      </SCViewContainer>
                    </SCViewBackground>
                  </>
                )}
          </SCCustomActionsContainer>
        </SCTaskBarContainer>
      )}
    </>
  );
};

export default ActionToolBar;
