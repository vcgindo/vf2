import { useEffect } from "react";
import VFFloatingTab from "../../../../../components/VectorFLOW/commons/VFFloatingTab";
import useBufferTrends from "./useBufferTrends";
import ActionToolBar from "../../SupplyChainIntelligenceHub/Planning/ActionToolBar";

import ChartView from "../../InsightsAndTrends/BufferTrends/ChartView";
import BPRViewTable, {
  BPRViewTableColDef,
} from "../../SupplyChainIntelligenceHub/BPR/BPRViewTable";
import { AvailabilityContainer, AvailabilityContent, AvailabilityHeader, SummaryTableColumn } from "./styles";
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import OverlayLoader from "../../../../../VectorFlow/Pages/MTO/Common/Loader";

const BufferTrends = () => {
  const {
    currentTab,
    onFloatingTabChange,
    currentView,
    currentGraphData,
    summaryData,
    availability,
    BufferTrendsDataLoad,
    isLoading,
    currentPageTab,
    onFloatingTabChangeOnPages,
    graphs,
    updateGraphState,
    setHorizondays,
    handleSubmitClick,
    horizonDays,
    onGoBack,
    handleApplyFilter,
    multiFilterState,
    setMultiFilterState,
    onDeleteFilter,
    themeUI,
    lastRunDate
  } = useBufferTrends();

  const summaryColumnDefs: BPRViewTableColDef[] = [
    { headerName: "", colId: "category" },
    { headerName: <SummaryTableColumn color="black">Black</SummaryTableColumn>, colId: "sumB" },
    { headerName: <SummaryTableColumn color="red">Red</SummaryTableColumn>, colId: "sumR" },
    { headerName: <SummaryTableColumn color="#ffbf00ff">Yellow</SummaryTableColumn>, colId: "sumY" },
    { headerName: <SummaryTableColumn color="green">Green</SummaryTableColumn>, colId: "sumG" },
    { headerName: <SummaryTableColumn color="blue">Blue</SummaryTableColumn>, colId: "sumBU" },
    { headerName: <SummaryTableColumn color="gray">White</SummaryTableColumn>, colId: "sumW" },
  ];
  const renderView = () => {
    switch (currentView) {
      case "chart":
        return (
          <>
            <ChartView
              currentTab={currentTab}
              currentGraphData={currentGraphData}
              currentPageTab={currentPageTab}
              onFloatingTabChangeOnPages={onFloatingTabChangeOnPages}
              isLoading={isLoading}
              graphs={graphs}
              updateGraphState={updateGraphState}
              setHorizondays={setHorizondays}
              handleSubmitClick={handleSubmitClick}
              horizonDays={horizonDays}
            />

            <div style={{height:'200px'}}>
            
                <div style={{zoom:0.8,margin:'0px 10px 0px 25px',display:'flex'}}>
                  <BPRViewTable
                    tableHeader="Summary"
                    tablePrefixSrc=""
                    rowData={summaryData}
                    colDefs={summaryColumnDefs}
                  />
                  <AvailabilityContainer>
                    <AvailabilityHeader>
                        Overall Availability
                    </AvailabilityHeader>
                    <AvailabilityContent themeUI={themeUI}>
                        {availability} %
                    </AvailabilityContent>
                  </AvailabilityContainer>
                </div>
 
                {/* <div style={{zoom:0.7,margin:'0px 0px 0px 40px'}}>
                <BPRViewTable
                  tableHeader="Availability"
                  tablePrefixSrc="/assets/img/VectorFLOW/BTG/Availability-icon.svg"
                  rowData={[{ avail: availability + "%" }]}
                  colDefs={availColumnDefs}
                />
                </div> */}
            </div>
          </>
        );
    }
  };

  useEffect(() => {
    if(currentGraphData?.length) BufferTrendsDataLoad();
  }, [currentTab]);

  return (
    <>
      <ActionToolBar
        view={"grid"}
        setCurrentTab={currentTab}
        currCategory={"BufferTrend"}
        currentTab={""}
        tabsList={[]}
        onFloatingTabChange={onFloatingTabChange}
        onGoBack={onGoBack}
        onViewChange={() => console.log("")}
        onApplyFilter={handleApplyFilter}
        onExportToExcelCallBack
        genericRecordCount={0}
        multiFilter={multiFilterState}
        lastRunDate={lastRunDate}
        setMultiFilter={setMultiFilterState}
        onDelete={onDeleteFilter}
      />
      {lastRunDate && (
        <LastRunDateComponent lastRunDate={lastRunDate} />
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          marginBottom: "8px",
        }}
      >
        <div style={{ zoom: 0.7 }}>
          <VFFloatingTab
            tabs={[
              {
                id: "technical View",
                label: "On-Hand Inv. Availability Trend",
                value: "tech",
              },
              {
                id: "economicalView",
                label: "Pipeline Inv. Availability Trend",
                value: "eco",
              },
            ]}
            handleClick={onFloatingTabChange}
          />
        </div>
      </div>

      {isLoading ? <OverlayLoader /> : currentGraphData?.length && renderView()}
    </>
  );
};

export default BufferTrends;
