import { SCChartContainer, SCDynamicContainer } from "../style";
import { AgCharts } from "ag-charts-react";
import { Allotment } from "allotment";
import {
  useGetExcessInventorySku,
  useGetExcessInventoryValue,
} from "../../../../../Services/MTA/InsightsAndTrends";
import VFInfoToolTip from "../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import { useEffect, useMemo, useState } from "react";
import OverlayLoader from "../../../../../../VectorFlow/Pages/MTO/Common/Loader";
import { createChartParams } from "./chartParams";
import {
  createTotalLegendForLineCharts,
  generateChartOptions,
} from "../../../../../../helpers/utils";
import VFHorizon from "../../../../../../components/VectorFLOW/commons/VFHorizon";
import { useSelector } from "react-redux";
import { RootState } from "../../../../../../redux/store/store";

const ExcessInventoryTrend = ({
  filter,
  horizon,
  setHorizon,
}: {
  themeUi: string;
  filter: any;
  horizon: number;
  setHorizon: any;
}) => {
  const [options1, setOptions1] = useState({});
  const [options2, setOptions2] = useState({});
  const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
  const CURRENCY = EnvConfig?.CURRENCY; 
  const chartParams1 = useMemo(() => createChartParams('skuCount'), []);
    const chartParams2 = useMemo(() => createChartParams('value', CURRENCY), [CURRENCY]);

  const greyShades = [
    "#333333",
    "#666666",
    "#808080",
    "#a6a6a6",
    "#cccccc",
    "#d8d8d8",
  ];

  const { mutateAsync: GetExcessInventorySku, isLoading: isLoaderGraph1 } =
    useGetExcessInventorySku();
  const { mutateAsync: GetExcessInventoryValue, isLoading: isLoaderGraph2 } =
    useGetExcessInventoryValue();

  useEffect(() => {
    OnHorizonChange(horizon);
    OnHorizon2Change(horizon);
  }, [filter]);

  const OnHorizonChange = async (hvalue: any) => {
    setHorizon(hvalue);
    const param = { horison: horizon, filters: filter };
    const ExcessInventorySkuData = await GetExcessInventorySku(param);
    const data = ExcessInventorySkuData?.data?.data;
    const locationTypes = Array.from(
      new Set(data.map((d: any) => d.locationtype))
    );
    const series: any = locationTypes.map((locationType, index) => {
      const seriesData = data
        .filter((d: any) => d.locationtype === locationType)
        .map((d: any) => ({ date: d.date, countSku: d.countSku }));
      return {
        ...chartParams1.series[0],
        yName: locationType,
        data: seriesData,
        stroke: greyShades[index % greyShades.length],
        strokeWidth: 3,
        marker: {
          fill: greyShades[index % greyShades.length],
          size: 5,
          stroke: greyShades[index % greyShades.length],
          strokeWidth: 2,
        },
      };
    });
    series.push(createTotalLegendForLineCharts(data, "countSku"));
    const chartProps = { 
    ...JSON.parse(JSON.stringify(chartParams1)), // Deep copy to break all references
    series: series 
};
    const customizedChartProps = generateChartOptions(data, chartProps);
    setOptions1(customizedChartProps);
  };

  const OnHorizon2Change = async (hvalue: any) => {
    setHorizon(hvalue);
    const param = { horison: horizon, filters: filter };
    const ExcessInventoryValueData = await GetExcessInventoryValue(param);
    const data = ExcessInventoryValueData?.data?.data;
    const locationTypes = Array.from(
      new Set(data.map((d: any) => d.locationtype))
    ); // dynamic labels
    const series: any = locationTypes.map((locationType, index) => {
      const seriesData = data
        .filter((d: any) => d.locationtype === locationType)
        .map((d: any) => ({ date: d.date, value: d.value }));
      return {
        ...chartParams2.series[0],
        yName: locationType,
        data: seriesData,
        stroke: greyShades[index % greyShades.length],
        strokeWidth: 3,
        marker: {
          fill: greyShades[index % greyShades.length],
          size: 8,
          stroke: "white",
          strokeWidth: 2,
        },
      };
    });
    series.push(createTotalLegendForLineCharts(data, "value"));
    const chartProps = { 
    ...JSON.parse(JSON.stringify(chartParams2)), // Deep copy
    series: series 
};
    const customizedChartProps = generateChartOptions(data, chartProps);
    setOptions2(customizedChartProps);
  };

  if (isLoaderGraph1 || isLoaderGraph2) {
    <OverlayLoader />;
  }
  return (
    <SCDynamicContainer>
      <Allotment minSize={0} maxSize={590}>

        <Allotment.Pane preferredSize={"50%"}>
          <div
            className="main"
            style={{
              marginTop: "20px",
              backgroundColor: "white",
              height: "415px",
              boxShadow: "-5px 5px 12px #0000001C",
              marginRight: "15px",
            }}
          >
            <VFHorizon
              setHorizon={setHorizon}
              OnHorizonChange={OnHorizonChange}
              horizon={horizon}
              styles={{width:'100%'}}
            />
            <CustomizedChartComponent chartOptions={options1} chartParams={chartParams1}/>
          </div>

        </Allotment.Pane>
        <div
          className="main"
          style={{
            marginTop: "20px",
            backgroundColor: "white",
            height: "415px",
            boxShadow: "-5px 5px 12px #0000001C",
            marginLeft: "25px",
          }}
        >
          <VFHorizon
            setHorizon={setHorizon}
            OnHorizonChange={OnHorizon2Change}
            horizon={horizon}
            styles={{width:'100%'}}
          />
          <CustomizedChartComponent chartOptions={options2} chartParams={chartParams2}/>
        </div>
      </Allotment>

    </SCDynamicContainer>
  );
};

export default ExcessInventoryTrend;

export const CustomizedChartComponent = ({chartOptions,chartParams}:any) => {
  const chartKey = chartOptions?.series?.length 
    ? `chart-series-${chartOptions.series.length}` 
    : 'chart-default';
  return (
    <SCChartContainer>
      <div
        style={{
          height: "300px",
          borderTop: "1px solid rgb(178, 178, 178)",
        }}
      >
        <div
          className="Title"
          style={{
            height: "50px",
            backgroundColor: "white",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <div
            style={{ fontSize: "14px", fontWeight: 500, textAlign: "center" }}
          >
            {chartParams.title}
          </div>
          <div style={{ marginLeft: 10, marginBottom: "-5px" }}>
            <VFInfoToolTip infoList={chartParams.graphInfo} />
          </div>
        </div>
        <AgCharts key={chartKey} options={chartOptions} />
      </div>
    </SCChartContainer>
  );
};
