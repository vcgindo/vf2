import { useMemo, useState, useEffect } from "react";
import { Allotment } from "allotment";
import {
  useGetDBMNormSuggestionLoc,
  useGetDBMNormSuggestionPie,
  useGetDBMNormSuggestionSKUs,
  useGetDBMNormSuggestionAgeing,
} from "../../../../../Services/MTA/InsightsAndTrends";
import "allotment/dist/style.css";
import { SCDynamicContainer } from "../style";
import { generateChartOptions } from "../../../../../../helpers/utils";
import VFCharts from "../../../../../../components/VectorFLOW/commons/VFCharts";
import "./styles.css";
import PieChartandGrid from './VFPieChartandGrid'

import { coldefs1, coldefs2, coldefs3, coldefs4 } from "./colDefs";
import {
  chartParams1,
  chartParams2,
  chartParams3,
  chartParams4,
} from "./chartParams";
import OverlayLoader from "../../../../../../VectorFlow/Pages/MTO/Common/Loader";

const DBMNormSuggestions = ({ filter }: { filter: any }) => {
  const { mutateAsync: DBMNormSuggestionLoc, isLoading: isLoadingGraph1 } =
    useGetDBMNormSuggestionLoc();
  // const { data: DBMNormSuggestionLoc, isLoading: isLoadingGraph1 } =
  //   useGetDBMNormSuggestionLoc(filter);
  const { mutateAsync: DBMNormSuggestionPie, isLoading: isLoadingGraph2 } =
    useGetDBMNormSuggestionPie();
  const { mutateAsync: DBMNormSuggestionSKUs, isLoading: isLoadingGraph3 } =
    useGetDBMNormSuggestionSKUs();
  const { mutateAsync: DBMNormSuggestionAgeing, isLoading: isLoadingGraph4 } =
    useGetDBMNormSuggestionAgeing();

  const [DBMSuggestionLocData, SetDBMSuggestionLocData] = useState([]);
  const [ActiveDBMSuggestionData, SetActiveDBMSuggestionData] = useState([]);
  const [DBMSuggestionSkuData, SetDBMSuggestionSkuData] = useState([]);
  const [DBMSuggestionAgeingData, SetDBMSuggestionAgeingData] = useState([]);
  const [isAllDataLoaded, setIsAllDataLoaded] = useState<boolean>(false);

  const [chartThemeOverridesG1, setChartThemeOverridesG1] =
    useState<any>(undefined);
  const [chartThemeOverridesG2, setChartThemeOverridesG2] =
    useState<any>(undefined);
  const [chartThemeOverridesG3, setChartThemeOverridesG3] =
    useState<any>(undefined);
  const [chartThemeOverridesG4, setChartThemeOverridesG4] =
    useState<any>(undefined);

  useEffect(() => {
    const fetchDBMNormSuggestionData = async () => {
      const [
        DBMNormSuggestionLocD,
        ActiveDBMSuggestionDataD,
        DBMSuggestionSkuDataD,
        DBMSuggestionAgeingDataD,
      ] = await Promise.all([
        DBMNormSuggestionLoc(),
        DBMNormSuggestionPie(),
        DBMNormSuggestionSKUs(),
        DBMNormSuggestionAgeing(),
      ]);

      const formattedRowData1 = DBMNormSuggestionLocD?.data?.data;
      SetDBMSuggestionLocData(formattedRowData1);
      setChartThemeOverridesG1(
        generateChartOptions(formattedRowData1, chartParams1, undefined)
      );

      const formattedRowData2 = formatActiveDBMSuggestionData(
        ActiveDBMSuggestionDataD?.data?.data
      );
      ///fwefwe
      SetActiveDBMSuggestionData(formattedRowData2);
      // setChartThemeOverridesG2(generateChartForGraph2(chartParams2)
      // );
      setChartThemeOverridesG2({});

      const formattedRowData3 = sortDBMSuggestionSKUData(
        DBMSuggestionSkuDataD?.data?.data
      );
      SetDBMSuggestionSkuData(formattedRowData3);
      setChartThemeOverridesG3(
        generateChartOptions(formattedRowData3, chartParams3, undefined)
      );

      const formattedRowData4 = DBMSuggestionAgeingDataD?.data?.data;
      SetDBMSuggestionAgeingData(formattedRowData4);
      setChartThemeOverridesG4(
        generateChartOptions(formattedRowData4, chartParams4, undefined)
      );

      setIsAllDataLoaded(true);
    };
    fetchDBMNormSuggestionData();
  }, [filter]);

  const sortDBMSuggestionSKUData = (rowData: any) => {
    return rowData.sort(
      (a: any, b: any) => b.NormInc + b.NormDec - (a.NormInc + a.NormDec)
    );
  };

  const formatActiveDBMSuggestionData = (rowData: any) => {
    const totalCount = rowData?.reduce(
      (acc: any, curr: any) => acc + curr.count,
      0
    );
    const pieData = rowData?.map((row: any) => ({
      suggestion: row.suggestion,
      count: parseFloat(((row.count / totalCount) * 100).toFixed(2)),
    }));
    return pieData;
  };


  // const generateChartForGraph2 = (params:any) =>{
  //   return {
  //     palette: params.palette,
  //     common: {
  //       title:{
  //         fontSize:7,
  //         color:'white',
  //         enabled:true,
  //         text:params.downloadName,
  //       },
  //       legend: params.legend,
  //       axes: {
  //         category: {
  //           title: {
  //             enabled: true,
  //             text: "SKU Code",
  //             position: "bottom",
  //             fontSize:8,
  //             fontFamily:'Roboto'
  //           },
  //           label:{
  //             formatter:(params:any)=>{
  //               if(params.value.value.length > 10) return params.value.toString().slice(0,10) + '...';
  //               return params.value;
  //             },
  //             fontSize:8,
  //             fontFamily:'Roboto'
  //           }
  //         },
  //         number: {
  //           title: {
  //             enabled: true,
  //             text: "Count of Locations",
  //             position: "left",
  //             fontSize:10,
  //             fontFamily:'Roboto'
  //           },
  //         },
  //       },
  //     },
  //   };
  // }


  if (
    isLoadingGraph1 ||
    isLoadingGraph2 ||
    isLoadingGraph3 ||
    isLoadingGraph4 ||
    !isAllDataLoaded
  ) {
    return <OverlayLoader />;
  }

  return (
    <>
      <SCDynamicContainer style={{ height: "81vh" }}>
        <Allotment vertical>
          <Allotment.Pane className="upperPanel" preferredSize={"48%"}>
            <Allotment>
              <Allotment.Pane preferredSize={"48%"}>
                <VFCharts
                  height={"95%"}
                  chartParams={chartParams1}
                  colDefs={coldefs1}
                  rowData={DBMSuggestionLocData}
                  chartProps={chartThemeOverridesG1}
                  containerStyle={{ marginLeft: "0px", marginRight: "10px" }}
                />
              </Allotment.Pane>
              <Allotment.Pane preferredSize={"48%"}>
                
                <PieChartandGrid 
                    height={"100%"}
                    chartParams={chartParams2}
                    colDefs={coldefs2}
                    rowData={ActiveDBMSuggestionData}
                    chartProps={chartThemeOverridesG2}
                    containerStyle={{ marginLeft: "17px", marginRight: "0px" }}
                />
                {/* <VFCharts
                  height={"95%"}
                  chartParams={chartParams2}
                  colDefs={coldefs2}
                  rowData={ActiveDBMSuggestionData}
                  chartProps={chartThemeOverridesG2}
                  containerStyle={{ marginLeft: "17px", marginRight: "0px" }}
                /> */}

              </Allotment.Pane>
            </Allotment>
          </Allotment.Pane>

          <Allotment.Pane className="bottomPanel" preferredSize={"48%"}>
            <Allotment>
              <Allotment.Pane preferredSize={"48%"}>
                <VFCharts
                  height={"95%"}
                  chartParams={chartParams3}
                  colDefs={coldefs3}
                  rowData={DBMSuggestionSkuData}
                  chartProps={chartThemeOverridesG3}
                  containerStyle={{ marginLeft: "0px", marginRight: "10px" }}
                />
              </Allotment.Pane>
              <Allotment.Pane preferredSize={"48%"}>
                <VFCharts
                  height={"95%"}
                  chartParams={chartParams4}
                  colDefs={coldefs4}
                  rowData={DBMSuggestionAgeingData}
                  chartProps={chartThemeOverridesG4}
                  containerStyle={{ marginLeft: "17px", marginRight: "0px" }}
                />
              </Allotment.Pane>
            </Allotment>
          </Allotment.Pane>
        </Allotment>
      </SCDynamicContainer>
    </>
  );
};

export default DBMNormSuggestions;

