import { useEffect, useMemo, useState } from "react";
import "allotment/dist/style.css";
import { AgChartOptions } from "ag-charts-community";
import { graphColumnConfig } from "../MockData";
import { Poogi } from "../../../../Common/String";
import VFInfoToolTip from "../../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import SplitGraphContainer from "../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer";
import { getColumnDefinations } from "../../../../../../../helpers/utils";
import { TooltipRenderer } from "../OTIFCommon";
import moment from "moment";
import { useGetDate } from "../../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting";

const OTAndIFTrendsGraph = (props: any) => {
  const { graphData } = props;
  // const [startDate, setStartDate] = useState('-');
  // const [endDate, setEndDate] = useState('-');
  const [hideChart1, toggleChart1] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  // const [rawData] = useState(APIMock.graph.ot_n_if_graph.data);
  const [rawData, setRawData] = useState([]);
  const { data: apiResponseData } = useGetDate();



  function createSeriesData(val: number) {
    const seriesData: any = [];
    const labels = ["On Time %", "In Full %"];
    for (let i = 0; i < val; i++) {
      const color = i === 0 ? "#838282" : "#CBCBCB";
      const key = i === 0 ? "ot" : "if";
      seriesData.push({
        type: "line",
        xKey: "m",
        yKey: key,
        yName: labels[i],
        fill: color,
        strokeWidth: 4,
        marker: {
          enabled: true,
          shape: 'circle',
          size: 8,
          fill: color
        },
        strokeOpacity: 1,
        stroke: color,
        tooltip: {
          renderer: TooltipRenderer,
        },
      });
    }

    return seriesData;
  }

  const options: AgChartOptions = {
    data: rawData,

    series: createSeriesData(2),

    axes: [
      {
        type: "category",
        position: "bottom",
        title: { text: "", fontSize: 10, fontWeight: "bold" },
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
          rotation: -25,
          avoidCollisions: true
        },
        gridLine: {
          enabled: false,
        },
      },
      {
        title: {
          text: "OT & In Full %",
          fontSize: 10,
          fontWeight: "bold",
          spacing: 3,
        },
        type: "number",
        line: { enabled: true },
        position: "left",
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
          formatter: (params) => `${params.value}%`
        },
        gridLine: {
          enabled: false,
        },
        min: 0
      },
    ],

    legend: {
      item: {
        label: {
          fontSize: 10,
          fontWeight: 'bold', // Make legend text bold
        },
        marker: {
          size: 15,
          strokeWidth: 0,
          shape: "square",
        },
      },
    },
  };

  const colDefs = useMemo(() => {
    return getColumnDefinations(graphColumnConfig?.ot_n_if, {}, []);
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
          data-testid="ot-and-if-graph"
          style={{
            fontSize: "13px",
            margin: "0 auto",

            textAlign: "center",
          }}
        >
          <span style={{ fontWeight: 500 }}>{`${Poogi.otNif}  `}</span>
          <span style={{ fontWeight: 350 }}>{`(${moment(apiResponseData?.data?.data || '-').subtract(90, 'days').format('D MMM YYYY')} - ${moment(apiResponseData?.data?.data || '-').format('D MMM YYYY')})`}</span>

        </div>
        <div style={{ display: "flex" }}>
          <div style={{ marginLeft: 30, marginBottom: "-5px" }}>
            <VFInfoToolTip
              infoList={[
                "The graph highlights the On-Time In-Full (OTIF) trend of completed orders.",
                "Orders are plotted based on their respective completion dates."
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

  useEffect(() => {
    if (graphData) {
      // setStartDate(format(new Date(graphData.start), 'dd MMM yyyy'));
      // setEndDate(format(new Date(graphData.end), 'dd MMM yyyy'));
      const updatedData = graphData.data?.map((d: any) => ({ ...d, ot: Number(d.ot.toFixed(2)), if: Number(d.if.toFixed(2)) }))

      setRawData(updatedData);
    }
  }, [graphData])

  return (
    <div style={{ height: "100%", display: "flex", justifyContent: "left", marginLeft: '10px', paddingBottom: '10px' }}>

      <SplitGraphContainer
        tableLoading={tableLoading}
        chartLoading={chartLoading}
        setTableLoading={setTableLoading}
        setChartLoading={setChartLoading}
        data={rawData}
        rowData={options.data}
        graphTitle={""}
        tableTitle={Poogi.otNif}
        options={options}
        colDef={colDefs}
        header={generateHeader}
        hideChart={hideChart1}
        toggleChart={toggleChart1}
        TooltipRenderer={TooltipRenderer}
        graphType={9}
      />
    </div>
  );
};

export default OTAndIFTrendsGraph;
