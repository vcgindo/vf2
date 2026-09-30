import { useEffect, useMemo, useState } from "react";
import "allotment/dist/style.css";
import { AgChartOptions } from "ag-charts-community";
import { reasonColConfig } from "../mockData";
import { ManufacturingHub } from "../../../../Common/String";
import VFInfoToolTip from "../../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import SplitGraphContainer from "../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer";
import { getColumnDefinations } from "../../../../../../../helpers/utils";
import { TooltipRenderer } from "../common";
import moment from "moment";

const OTIFFailureGraph = (props: any) => {
  const { month, graphData, lastRunDate, subtractStartMonths, subtractEndMonths} =props; 
  const [startDate, setStartDate] = useState(lastRunDate);
  const [endDate, setEndDate] = useState('-');
  const [hideChart1, toggleChart1] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [rawData, setRawData] = useState<any>([]);

  const options: AgChartOptions = {
    data: rawData,

    series: [
        {
          type: "bar",
          direction: "horizontal",
          xKey: "r",
          yKey: "co",
          yName: "Count Of Orderes",
          stacked: true,
          fill: "#AD5000",
          tooltip: {
            renderer: TooltipRenderer,
          },
        },
      ],
  
      axes: [
        {
          type: "category",
          position: "left",
          // title: {
          //   text: "Major | Minor Reasons",
          //   fontSize: 10,
          //   fontWeight: "bold",
          // },
          label: {
            fontSize: 8,
            fontWeight: "bold", 
            color: "black",
            padding: 10,
          },
          gridLine: {
            enabled: false,
          },
        },
        {
          title: {
            text: "Count Of Orders",
            fontSize: 10,
            fontWeight: "bold",
            spacing: 3,
          },
          type: "number",
          position: "bottom",
          line: { enabled: true },
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
  
      // legend: {
      //   item: {
      //     label: {
      //       fontSize: 10,
      //     },
      //   },
      // },
  };

  const colDefs = useMemo(() => {
    return getColumnDefinations(reasonColConfig, {}, []);
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
          style={{
            fontSize: "13px",
            margin: "0 auto",

            textAlign: "center",
          }}
        >
          <span style={{ fontWeight: 500 }}>{`${ManufacturingHub.reasonHeading}  `}</span>
          <span style={{ fontWeight: 300 }}>{`(${endDate} - ${startDate})`}</span>
        </div>
        <div style={{ display: "flex" }}>
          <div style={{ marginLeft: 30, marginBottom: "-5px" }}>
            <VFInfoToolTip
              infoList={[
                `The graph highlights the top contriuting reasons behind OTIF failures for orders completed between ${endDate} - ${startDate}.`,
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
    );
  };

  useEffect(()=>{
    if(graphData){
      setStartDate(moment(lastRunDate).subtract(subtractStartMonths, 'months').subtract(1, 'days').format('DD-MMM-YYYY'));
      setEndDate( moment(lastRunDate).subtract(subtractEndMonths, 'months').format('DD-MMM-YYYY'));
      const data = Object.keys(graphData)?.map((key: string) => ({ r: key, co: graphData[key]}));
      setRawData(data);
    }
  },[graphData])

  let styles: any = { 
    height: "100%", 
    display: "flex", 
    paddingBottom: '10px' 
  }

  if(month ==='current'){
    styles = { ... styles, justifyContent: "right", marginLeft: '10px', }
  }else{
    styles = { ... styles, justifyContent: "left", marginRight: '8px', }
  }

  return (
    <div style={{...styles}}>
      <SplitGraphContainer
        tableLoading={tableLoading}
        chartLoading={chartLoading}
        setTableLoading={setTableLoading}
        setChartLoading={setChartLoading}
        data={rawData}
        rowData={options.data}
        graphTitle={""}
        tableTitle={ManufacturingHub.reasonHeading}
        options={options}
        colDef={colDefs}
        header={generateHeader}
        hideChart={hideChart1}
        toggleChart={toggleChart1}
        TooltipRenderer={TooltipRenderer}
        graphType={14}
      />
    </div>
  );
};

export default OTIFFailureGraph;
