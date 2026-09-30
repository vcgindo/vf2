import { useEffect, useMemo, useState } from "react";
import "allotment/dist/style.css";
import { AgChartOptions } from "ag-charts-community";
import { graphColumnConfig } from "../MockData";
import { Poogi } from "../../../../Common/String";
import VFInfoToolTip from "../../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import SplitGraphContainer from "../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer";
import { getColumnDefinations } from "../../../../../../../helpers/utils";
import { TooltipRenderer } from "../OTIFCommon";
import { useGetDate } from "../../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting";
import moment from "moment";

const OTIFTrendsGraph = (props: any) => {
  const { graphData } = props;
  // const [startDate, setStartDate] = useState('-');
  // const [endDate, setEndDate] = useState('-');
  const [hideChart1, toggleChart1] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [rawData, setRawData] = useState([]);
  const { data: apiResponseData } = useGetDate();


  function createSeriesData(val: number) {
    const seriesData: any = [];
    const labels = ["OTIF % Trends", "OTIF % Trends (+3 days)"];
    for (let i = 0; i < val; i++) {
      const color = i === 0 ? "#BC3D81" : "#FCADD7";
      const key = i === 0 ? "otif" : "otif_plus";
      seriesData.push({
        type: "line",
        xKey: "m",
        yKey: key,
        yName: labels[i],
        lineDash: i === 0 ? null : [5, 5], // 5px dash, 5px gap
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
          text: "OTIF %",
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
    return getColumnDefinations(graphColumnConfig?.otif, {}, []);
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
          data-testid="ot-if-graph"
          style={{
            fontSize: "13px",
            margin: "0 auto",

            textAlign: "center",
          }}
        >
          <span style={{ fontWeight: 500 }}>{`${Poogi?.otif}  `}</span>
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
      setRawData(graphData.data);
    }
  }, [graphData])

  return (
    <div style={{ height: "100%", display: "flex", justifyContent: "left", marginRight: '8px', paddingBottom: '10px' }}>
      <SplitGraphContainer
        tableLoading={tableLoading}
        chartLoading={chartLoading}
        setTableLoading={setTableLoading}
        setChartLoading={setChartLoading}
        data={rawData}
        rowData={options.data}
        graphTitle={""}
        tableTitle={Poogi.otif}
        options={options}
        colDef={colDefs}
        header={generateHeader}
        hideChart={hideChart1}
        toggleChart={toggleChart1}
        TooltipRenderer={TooltipRenderer}
        graphType={8}
      />
    </div>
  );
};

export default OTIFTrendsGraph;
