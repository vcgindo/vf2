import ActionToolBar from "../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import useProcPlanning from "./useProcPlanning";
import VFFloatingTab from "../../../../../components/VectorFLOW/commons/VFFloatingTab";
import { useEffect, useState } from "react";
import moment from "moment";
import OverlayLoader from "../../Common/Loader";
import useFilter from "../../../../../hooks/useFilter";
import { useGetFilterData } from "../../../../../VectorFlow/Services/MTO/Common/CommonFilter";
import { FilterPageName } from "../../Common/Enum";
import { useUserData } from "../../../../../context";
import ConfirmationModel from "../../Common/ConfirmationModel";
const APIFilterConfig = {
  filSecVisConfig: {
    Proc_Procurement_Planning: {
      mjr: false,
      or: true,
      res: true,
      cus: true,
    },
  },
};

const ProcurementPlanning = () => {
  const [filterData, setFilterData] = useState({});
  const [showExcelModal, setShowExcelModal] = useState(false);

  const {
    state: currFilter,
    setState: setCurrFilter,
    onFilterRemove,
    isFilterOpen,
    isMfgSelected,
    onAddFilter,
    onApplyFilter,
    toggleFilter,
    appliedFilters,
  } = useFilter(
    filterData,
    APIFilterConfig.filSecVisConfig.Proc_Procurement_Planning
  );
  const {
    mutateAsync: getPageWiseFilterData,
    isLoading: getFilterdataLoading,
  } = useGetFilterData();
  const {
    renderView,
    toggleCurrentTab,
    fetchData,
    isLoading,
    currentTab,
    handleResetClick,
    handleSaveClick,
    selectedDate,
    setSelectedDate,
    isPivot,
    gridRef
  } = useProcPlanning(appliedFilters);

  const handleDateChange = (date: string) => {
    setSelectedDate(date);
  };

  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  const getFilterData = async () => {
    try {
      const response = await getPageWiseFilterData({
        page_name: FilterPageName.Proc_Procurement_Planning,
        release_date: selectedDate,
      });
      setFilterData(response?.data.data);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    getFilterData();
  }, []);

  const ExcelExportData = () => {
    const gridApi = gridRef?.current?.api; 

    if (!gridApi) {
      console.error("Grid API not available for export.");
      return;
    }

    const isRowGroupingActive = gridApi.getRowGroupColumns().length > 0;
    const isValueActive =  gridApi.getValueColumns().length > 0;

    if (isPivot || isRowGroupingActive || isValueActive) {
      const exportName = `${FilterPageName.Proc_Procurement_Planning}_${moment().format("DD-MM-YYYY")}`;
      
      gridApi.exportDataAsExcel({
          fileName: exportName,
          sheetName: exportName
      });
      return;
    }
    else{
      setShowExcelModal(true);
    } 
  };

  
const handleExcelConfirm = (option: string, includeDetails: boolean) => {
    setShowExcelModal(false);
    
    let status = currentTab?.label === "Shortage" ? "0" : "1";
    if (option === "shortage") status = "0";
    if (option === "completely_available") status = "1";

    const excelScopeParam = option === "all" ? "all" : "";

    const detailsFlag = includeDetails ? 1 : 0;

    fetchData(
      selectedDate,
      1,
      status, 
      true,         
      1,            
      detailsFlag,   
      excelScopeParam
    );
  };


  return (
    <>
      <ConfirmationModel  
        open={showExcelModal}
        onClose={() => setShowExcelModal(false)}
        onConfirm={handleExcelConfirm}
        themeUi={themeUi}
        headerText={"Excel Export"}
        messageText={" BOM details :"}        
      />

      {(isLoading || getFilterdataLoading) && <OverlayLoader />}

      <div
        style={{
          display: "flex",
          height: "100%",
          flexDirection: "column",
          paddingBottom: "2rem",
        }}
      >
        <ActionToolBar
          comp={"Procurement Planning"}
          onDateChange={handleDateChange}
          isReleaseDate
          isAddFilterButton
          themeUi={themeUi}
          isExcelExport
          onExcelExportClick={ExcelExportData}
          submitDate={() => {
            fetchData(
              selectedDate,
              1,
              currentTab?.label === "Shortage" ? "0" : "1"
            );
          }}
          date={selectedDate}
          handleSaveClick={handleSaveClick}
          handleResetClick={handleResetClick}
          isFilterOpen={isFilterOpen}
          onAddFilter={onAddFilter}
          toggleFilter={toggleFilter}
          onApplyFilter={onApplyFilter}
          multiFilter={currFilter}
          setMultiFilter={setCurrFilter}
          onFilterRemove={onFilterRemove}
          isMfgSelected={isMfgSelected}
        />

        <div style={{ zoom: 0.75 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              marginBottom: "2px",
            }}
          >
            <VFFloatingTab
              handleClick={(tab) => toggleCurrentTab(tab)}
              tabs={[
                {
                  id: "ca",
                  label: "Completely Available",
                  value: "ca",
                },
                {
                  id: "short",
                  label: "Shortage",
                  value: "short",
                },
              ]}
            />
          </div>
        </div>
        {/* <ProcurementLayout> */}
        {renderView()}
        {/* </ProcurementLayout> */}
      </div>
    </>
  );
};

export default ProcurementPlanning;
