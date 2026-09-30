import { AgChartOptions } from "ag-charts-community";
import "allotment/dist/style.css";
import { useEffect, useMemo, useState } from "react";
// import { APIMock } from "../StplAndFullKitsData";
import VFInfoToolTip from "../../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import { getColumnDefinations } from "../../../../../../../helpers/utils";
import SplitGraphContainer from '../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer';
import { ProductionInsightsAndTrendsString } from "../../../../Common/String";
import { columnConfigData } from "../ColumnData";


const FullKitGraph = (props: any) => {
  const { graphData, lastRunDate } = props;

  const [hideChart1, toggleChart1] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [rawData, setRawData] = useState<any>([]);

  function TooltipRenderer({ datum, xKey }: any) {
    return `
    <div class="ag-chart-tooltip-title" style="background-color: #6C696A; display: flex; justify-content: center; align-items: center">
        ${datum[xKey]}
    </div>
    <div class="ag-chart-tooltip-content" style="color: white; background-color: #6C696A">
    
    <div>
        <div style="display: flex;">
            <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: gray">
            </div>
            <div style="display:flex ; width: 100%; justify-content: space-between">
                <div>${ProductionInsightsAndTrendsString.fullKitInDays}
                </div>
                <div> ${datum["days"]}
                </div>
            </div>
        </div>
    </div>`;
  }

  const options: AgChartOptions = {
    data: rawData,
    series: [
      {
        type: "bar",
        xKey: "ccr_n",
        yKey: "days",
        yName: "Full Kit In Days",
        strokeOpacity: 0,
        fill: "gray",
        tooltip: {
          renderer: TooltipRenderer,
        },
      },
    ],
    axes: [
      {
        type: "category",
        position: "bottom",
        title: { text: "CCR", fontSize: 10, fontWeight: "bold" },
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
        },
        gridLine: {
          enabled: false,
        },
      },
      {
        title: { text: "Days", fontSize: 10, fontWeight: "bold", spacing: 3 },
        type: "number",
        line: { enabled: true },
        position: "left",
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
        },
        gridLine: {
          enabled: false,
        },
      },
    ],

    legend: {
      item: {
        label: {
          fontSize: 10,
        },
      },
    },
  };

  const colDefs = useMemo(() => {
    return getColumnDefinations(columnConfigData?.fullkitTableColumn, {}, [])
  }, []);

  const generateHeader = () => {
    return (
      <div
        className="title"
        style={{
          backgroundColor: "white",
          height: "40px",
          display: "flex",
          justifyContent: "right",
          alignItems: "center",
          width: "100%",
        }}
      >
        <div
          data-testid="fullKit-graph"
          style={{
            fontSize: "14px",
            margin: "0 auto",
            textAlign: "center",
          }}>
          <span style={{ fontWeight: 500, }}>
            {`${ProductionInsightsAndTrendsString.fullKitInDays}  `}
          </span>
          <span style={{ fontWeight: 300, }}>
            {` (${lastRunDate})`}
          </span>
        </div>
        <div style={{ display: "flex" }}>
          <div style={{ marginLeft: 30, marginBottom: "-5px" }}>
            <VFInfoToolTip
              infoList={[
                "The graph highlights the amount of unreleased Full-kits (In Days) present for execution at each CCR.",
              ]}
            />
          </div>
          <div
            data-testid="grid-toggle-btn"
            onClick={() => {
              toggleChart1(!hideChart1);
            }}
            style={{
              marginLeft: 10,
              marginBottom: "-5px",
              marginRight: "10px",
            }}
          >
            <img
              src="/assets/img/VectorFLOW/BPR/minimize.svg"
              height={13}
              width={13}
              color={"#CCCCCC"}
            />
          </div>
        </div>
      </div>
    )
  }

  useEffect(()=>{
    if(graphData){
      setRawData(graphData);
    }
  },[graphData])

  return (
    <div style={{ height: "100%", display: "flex", justifyContent: "left", marginLeft: '12px', paddingBottom: '10px' }}>

      <SplitGraphContainer
        tableLoading={tableLoading}
        chartLoading={chartLoading}
        setTableLoading={setTableLoading}
        setChartLoading={setChartLoading}
        data={rawData}
        rowData={options.data}
        graphTitle={''}
        tableTitle={ProductionInsightsAndTrendsString.fullKitInDays}
        options={options}
        colDef={colDefs}
        header={generateHeader}
        hideChart={hideChart1}
        toggleChart={toggleChart1}
        TooltipRenderer={TooltipRenderer}
        graphType={5}
      />
    </div>
  );
};

export default FullKitGraph;
