import { useState, useEffect } from "react";
import { Allotment } from "allotment";
import "allotment/dist/style.css";
import "../../../styles.css";
import { ColDef } from "ag-grid-enterprise";
import { SCDynamicContainer } from "../../../styles";
import { chartParams1, chartParams2 } from "./chartParams";
import {colDefForPie as colDefs2} from '../../../colDefs'
import {convertToInt, getProductAndLocationHeirarchiesFromEnv, generateChartOptions} from '../../../../../../../../../helpers/utils';
import VFCharts from "../../../../../../../../../components/VectorFLOW/commons/VFCharts";
import { useSelector } from "react-redux";
import { RootState } from "../../../../../../../../../redux/store/store";

 
interface ExpediteChildDispatchesProps {
  data: any;
}
 
const ExpediteDispatches = ({ data }: ExpediteChildDispatchesProps) => {
 
  const [chartThemeOverridesG1 , setChartThemeOverridesG1] = useState<any>(undefined)
  const [chartThemeOverridesG2 , setChartThemeOverridesG2] = useState<any>(undefined)
 
  const [customizedChartParams1,setCustomizedChartParams1] = useState<any>(undefined)
 
  const [rowData1,setRowData1] = useState<any>([])
  const [rowData2,setRowData2] = useState<any>([])
  const [colDefs1 , setColDefs1] = useState<any>([])
  const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
  const PRODUCT_PERMISSION_L1 = EnvConfig['PRODUCT_PERMISSION_L1']; 
  const PRODUCT_PERMISSION_L2 = EnvConfig['PRODUCT_PERMISSION_L2']; 
  const PRODUCT_PERMISSION_L3 = EnvConfig['PRODUCT_PERMISSION_L3']; 
  
  const LOCATION_PERMISSION_L1 = EnvConfig['LOCATION_PERMISSION_L1']; 
  const LOCATION_PERMISSION_L2 = EnvConfig['LOCATION_PERMISSION_L2']; 
  const LOCATION_PERMISSION_L3 = EnvConfig['LOCATION_PERMISSION_L3']; 
 
const mapUIConfigToColdefs1 = (columns:Array<{header:string,colCode:string}>) => {
    let colDefs = [];
 
    const customColdefs: ColDef[] = [
      {
        field: "WHDescription",
        headerName: "Receiving Location Name",
        colId: "WHDescription",
      },
    ];
   
    colDefs = columns.map((column:{header:string,colCode:string})=>{
        const customColdef = getProductAndLocationHeirarchiesFromEnv(column,{} , PRODUCT_PERMISSION_L1 , PRODUCT_PERMISSION_L2 , PRODUCT_PERMISSION_L3 , LOCATION_PERMISSION_L1 , LOCATION_PERMISSION_L2 , LOCATION_PERMISSION_L3); 
        if(customColdef) return customColdef;
        return {
            field:column['colCode'],
            colId:column['colCode'],
            headerName:column['header']
        }
    })
    return [...customColdefs,...colDefs];
}
 
 
  const getParentLocationColdefs = (data: any):any => {
    const dynamicColdefs: ColDef[] = [];  
    const columnHash:any = {};
    data.forEach((row:any)=>{
      row['count'].forEach((colObj:any)=>{
        if(!columnHash[colObj['pwc']]){
          columnHash[colObj['pwc']] = 1;
          dynamicColdefs.push({
            field: colObj['pwc'],
            headerName: colObj['pwc'],
            colId: colObj['pwc'],
          });
        }
      })
    })
    return dynamicColdefs;
  };
 
 
  const generateRowObj = (data:any) => {
    const parentLocationColdefs = getParentLocationColdefs(data);
    const rowObj: any = {
      ln: "",
    };
    parentLocationColdefs.forEach((colDef:any)=>{
      rowObj[colDef['field']] = 0
    })
   
    return rowObj;
  };
 
  const mapDataToRowData = (data: any) => {
     
    const rowData: any = [];
    data.forEach(
      (row:any) => {
        const rowObj = {...row,...generateRowObj(data)};
        row["count"].forEach(
          (subRow: { pwc: string; count: string }) => {
            rowObj[subRow.pwc] = parseInt(subRow.count, 10);
          }
        );
        rowData.push(rowObj);
      }
    );
 
    return rowData;
  };
 
 
  const sortRowData1 = (rowdata: any) => {
    const processedData = rowdata.map((row: any) => {
      // Create row object with additional attributes
      const rowObj = { ...row};
 
      // Calculate total count by summing up all counts in the 'count' array
      const totalCount = row.count.reduce((sum: number, subRow: any) =>
        sum + parseInt(subRow.count, 10), 0
      );
 
      // Attach totalCount for sorting
      return { ...rowObj, totalCount };
    });
 
    // Sort array based on totalCount in descending order
    processedData.sort((a: any, b: any) => b.totalCount - a.totalCount);
 
    // Remove totalCount before returning
    return processedData.map(({ totalCount, ...rest }: any) => rest);
  };
 
 
  const filterNonEmptyDynamicColumns = (data: any): string[] => {
    const validColumnSet = new Set<string>();
 
    // Consider only the top 10 rows
    const top10Data = data.slice(0, 10);
 
    // Track columns that appear in at least one row of the top 10
    top10Data.forEach((row: any) => {
      row['count'].forEach((colObj: any) => {
        validColumnSet.add(colObj['pwc']);
      });
    });
 
    return Array.from(validColumnSet);
  };
 
 
 
  useEffect(()=>{
 
    const formattedRowData1 = sortRowData1(mapDataToRowData(data["maxPipelineInvBlackRedSKUWithRationedQuantityAvailableAtParentuiconfig"]['data']))
    setRowData1(formattedRowData1)
 
    const dynamicColumns = getParentLocationColdefs(formattedRowData1)
   
    const cutomizedChartParams = generateCustomizedChartParams(chartParams1,formattedRowData1)
    setCustomizedChartParams1(cutomizedChartParams)
 
    setColDefs1([...mapUIConfigToColdefs1(data['maxPipelineInvBlackRedSKUWithRationedQuantityAvailableAtParentuiconfig']['uiconfig']),...dynamicColumns])
 
    setChartThemeOverridesG1(generateChartOptions(formattedRowData1,cutomizedChartParams,undefined))
 
 
   
    const formattedRowData2 = convertToInt(data["prePostRationing"],['pre','post'])
    setRowData2(formattedRowData2)
    setChartThemeOverridesG2(generateChartOptions(formattedRowData2,chartParams2,undefined))
  },[])
 
 
  const generateCustomizedChartParams = (chartParams:any,rowdata:any) =>{
    const overridenChartparams = {...chartParams}
    const dynamicFeilds = filterNonEmptyDynamicColumns(rowdata)
 
    const defaultColForChart = {
      columns: [ "WHDescription", ...dynamicFeilds],
      start:0,
      end:9
    }
    overridenChartparams.defaultColForChart = defaultColForChart
 
    overridenChartparams.chartKey.Yaxis = dynamicFeilds
    const customizedSeriesData = dynamicFeilds.map(field => ({
      type: 'bar',
      xKey: 'WHDescription',
      stacked: true,
      barPadding: 0.2,
      yKey: field,
      yName: field
    }));
    overridenChartparams.series = customizedSeriesData
    return overridenChartparams
  }

 
  return (
    <>
      <SCDynamicContainer style={{height:'77vh'}}>
        <Allotment>
          <Allotment.Pane preferredSize={"50%"}>
               
              {customizedChartParams1 !==undefined && (
                  <VFCharts    
                    height={'95%'}
                    chartParams={customizedChartParams1}
                    colDefs={colDefs1}
                    rowData={rowData1}
                    chartProps={chartThemeOverridesG1}
                    containerStyle={{marginLeft:'0px',marginRight:'10px'}}
                    />
                  )}
 
          </Allotment.Pane>
          <Allotment.Pane preferredSize={"50%"} minSize={500}>
 
                    <VFCharts    
                      height={'95%'}
                      chartParams={chartParams2}
                      colDefs={colDefs2}
                      rowData={rowData2}
                      chartProps={chartThemeOverridesG2}
                      containerStyle={{marginLeft:'17px',marginRight:'0px'}}
                  />
 
          </Allotment.Pane>
        </Allotment>
      </SCDynamicContainer>
    </>
  );
};
export default ExpediteDispatches;