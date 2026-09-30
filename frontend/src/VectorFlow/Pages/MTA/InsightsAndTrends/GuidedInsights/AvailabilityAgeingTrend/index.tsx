import { AgCharts } from "ag-charts-react";
import { useGetAvailabilityAgeing } from "../../../../../Services/MTA/InsightsAndTrends";
import VFRangeSlider from "../../../../../../components/VectorFLOW/commons/VFRangeSlider";
import { useState, useEffect } from "react";
import VFInfoToolTip from "../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import OverlayLoader from "../../../../../../VectorFlow/Pages/MTO/Common/Loader";
import { chartParams1  } from "./chartParams";
import { generateChartOptions } from "../../../../../../helpers/utils";
import VFHorizon from "../../../../../../components/VectorFLOW/commons/VFHorizon";


const AvailabilityAgeingTrend = ({themeUi,filter, horizon, setHorizon}:{themeUi:string,filter:any, ageing:number, setAgeing:any, horizon:number, setHorizon:any}) => {
 

  const { mutateAsync: GetAvailabilityAgeing, isLoading } =useGetAvailabilityAgeing();
  const [options, setOptions] = useState({})
  const [age,setAgeing]=useState(1);
  
  const OnHorizonChange = async (hvalue: any) => {
    setHorizon(hvalue);
    const param = { horison: hvalue, ageing: age,filters:filter};
    const AvailabilityAgeing = await GetAvailabilityAgeing(param);
    const data = AvailabilityAgeing?.data?.data;
    // const customizedChartProps = generateChartOptions(data, chartParams1);
    // setOptions(customizedChartProps);
    const customizedChartProps = generateChartOptions(data, chartParams1);
    customizedChartProps.data = data; 
    setOptions(customizedChartProps);
  };

  const handleAgeChange = (event: any) => {
    setAgeing(parseInt(event.target.value));
  };

  useEffect(() => {
    OnHorizonChange(horizon);
  }, [filter]);

  // const AvailabilityAgeingTrendOptions: AgChartOptions = {
  //   // title: {
  //   //   text: "Trend of #SKU-Loations with Continuous Black/Red/White Status >= Selected Minimum Ageing",
  //   //   fontWeight: "500",
  //   //   fontSize:14
  //   // },
  //   data: AvailabilityAgeingTrendData,
  //   series: [
  //     {
  //       type: "line" as const,
  //       xKey: "date",
  //       yKey: "red",
  //       yName: "red",
  //       stroke: "#DA3535",
  //       marker: {
  //         fill: "red",
  //         stroke: "red",
  //         size: 8,
  //       },
  //     },
  //     {
  //       type: "line" as const,
  //       xKey: "date",
  //       yKey: "black",
  //       yName: "black",
  //       strokeWidth: 3,
  //       stroke: "#000000",
  //       marker: {
  //         fill: "black",
  //         stroke: "black",
  //         size: 8,
  //       },
  //     },
  //     {
  //       type: "line" as const,
  //       xKey: "date",
  //       yKey: "white",
  //       yName: "white",
  //       strokeWidth: 3,
  //       stroke: "#BFBFBF",
  //       marker: {
  //         fill: "grey",
  //         stroke: "grey",
  //         size: 8,
  //       },
  //     },
  //   ],
  //   legend: {
  //     position: "bottom",
  //     item:{
  //       marker:{
  //         shape:'square'
  //       }
  //     }
  //   },
  //   axes: [
  //     {
  //       type: "category",
  //       position: "bottom",
  //       title: {
  //         text: "Date",
  //         fontSize: 10,
  //         fontFamily: "Roboto",
  //       },
  //       label: {
  //         fontSize: 8,
  //         fontFamily: "Roboto",
  //         autoRotate:false,
  //         avoidCollisions:true
  //       },
  //     },
  //     {
  //       type: "number",
  //       position: "left",
  //       title: {
  //         text: "No Of SKU-Locations",
  //         fontSize: 10,
  //         fontFamily: "Roboto",
  //       },
  //     },
  //   ],
  // };


  const numbers = Array.from(Array(90), (_, index) => index + 1);
  if (isLoading) {
    return <OverlayLoader />;
  }

  return (
    <div style={{ margin: "25px 20px 0px 20px" , height:'75%'}}>
      <div
        style={{
          display: "flex",
          top: 221,
          left: 239,
          width: 900,
          height: 59,
          opacity: 1,
          alignItems: "center",
          marginBottom:'8px'
        }}
      >
        <div style={{ paddingLeft: 20, width: 210 }}>
          <label
            style={{
              fontStyle: "normal",
              fontVariant: "normal",
              fontWeight: 300,
              fontSize: 14,
              fontFamily: "Roboto",
            }}
          >
            <b>Minimum Ageing:</b>
          </label>
          <select
            onChange={handleAgeChange}
            value={age}
            style={{
              marginLeft: "4px",
              textAlign: "center",
              width: 40,
              height: 28,
              border: "1px solid #838383",
              boxShadow: " 0px 6px 12px #8D8D8D29",
              borderRadius:'6px'
            }}
          >
            {numbers.map((number) => (
              <option key={number} value={number}>
                {number}
              </option>
            ))}
          </select>
        </div>

        <VFHorizon
          setHorizon={setHorizon}
          OnHorizonChange={OnHorizonChange}
          horizon={horizon}
          styles={{width:'500px'}}
        />

      </div>
      <div style={{ marginLeft: "10px", marginRight: "10px", height: "88%"}}>
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
            {chartParams1.title}
          </div>
          <div style={{ marginLeft: 10 ,marginBottom:'-5px'}}>
            <VFInfoToolTip infoList={chartParams1.graphInfo} />
          </div>
        </div>
        <div style={{height:'85%'}}><AgCharts options={options} /></div>
      </div>
    </div>
  );
};
export default AvailabilityAgeingTrend;
