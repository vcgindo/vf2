import { AgCharts } from "ag-charts-react";
import { useGetAvailabilityTrend } from "../../../../../Services/MTA/InsightsAndTrends";
import { useState, useEffect } from "react";
import VFInfoToolTip from "../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import OverlayLoader from "../../../../../../VectorFlow/Pages/MTO/Common/Loader";
import { chartParams1 } from "./chartParams";
import { generateChartOptions } from "../../../../../../helpers/utils";
import VFHorizon from "../../../../../../components/VectorFLOW/commons/VFHorizon";

const AvailabilityTrend = ({
  filter,
  horizon,
  setHorizon,
}: {
  themeUi: string;
  filter: any;
  horizon: number;
  setHorizon: any;
}) => {
  const { mutateAsync: GetAvailabilityTrend, isLoading } =
    useGetAvailabilityTrend();

  const greyShades = [
    "#333333",
    "#666666",
    "#808080",
    "#a6a6a6",
    "#cccccc",
    "#d8d8d8",
    "#4d4d4d",
    "#e0e0e0",
    "#f2f2f2",
    "#1a1a1a",
  ];

  const [options, setOptions] = useState({});
  const [locationTypeOrder, setLocationTypeOrder] = useState<string[]>([]);
  useEffect(() => {
    OnHorizonChange(horizon);
  }, [filter]);

  const OnHorizonChange = async (hvalue: any) => {
    setHorizon(hvalue);
    const param = { horison: hvalue, filters: filter };
    const AvailabilityTrend = await GetAvailabilityTrend(param);
    const data = AvailabilityTrend?.data?.data;

    if (!data || data.length === 0) {
      setOptions({});
      return;
    }

    let locationTypes: string[] = Array.from(
      new Set<string>(data.map((d: any) => String(d.locationtype)))
    ).sort();

    if (locationTypeOrder.length > 0) {
      const newTypes = locationTypes.filter((type: string) => !locationTypeOrder.includes(type));
      locationTypes = [...locationTypeOrder.filter((type: string) => locationTypes.includes(type)), ...newTypes];
    } else {
      setLocationTypeOrder(locationTypes);
    }
    
    const series = locationTypes.map((locationType, index) => {
      const seriesData = data
        .filter((d: any) => d.locationtype === locationType)
        .map((d: any) => ({ week: d.week, percentage: d.percentage }));
      return {
        ...chartParams1.series[0],
        yName: locationType,
        data: seriesData,
        stroke: greyShades[index % greyShades.length],
        marker: {
          fill: greyShades[index % greyShades.length],
          size: 5,
          stroke: greyShades[index % greyShades.length],
          strokeWidth: 3,
        },
      };
    });

    const chartProps = { ...chartParams1, series: series };
    const customizedChartProps = generateChartOptions(data, chartProps);
    customizedChartProps.data = data;
    setOptions(customizedChartProps);

  };

  if (isLoading) {
    return <OverlayLoader />;
  }

  return (
    <div style={{ marginTop: "25px", marginLeft: "20px", height: "70%" }}>
      <VFHorizon
        setHorizon={setHorizon}
        OnHorizonChange={OnHorizonChange}
        horizon={horizon}
        styles={{width:'500px'}}
      />
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
        <div style={{ fontSize: "14px", fontWeight: 500, textAlign: "center" }}>
          {chartParams1.title}
        </div>
        <div style={{ marginLeft: 10, marginBottom: "-5px" }}>
          <VFInfoToolTip infoList={chartParams1.graphInfo} />
        </div>
      </div>
      <div style={{ height: "85%" , padding:'30px 0px' }}>
        <AgCharts options={{...options, padding: { right: 20, left: 20 }}} />
      </div>
    </div>
  );
};
export default AvailabilityTrend;
