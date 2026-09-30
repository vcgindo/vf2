import {useState, useEffect} from "react";
import { Allotment } from "allotment";
import "allotment/dist/style.css";
import {SCDynamicContainer} from '../../../styles';
import {convertToInt, getProductAndLocationHeirarchiesFromEnv, generateChartOptions} from '../../../../../../../../../helpers/utils';
import { chartParams1 , chartParams2 } from './chartParams' 
import VFCharts from "../../../../../../../../../components/VectorFLOW/commons/VFCharts";
import { useSelector } from "react-redux";
import { RootState } from "../../../../../../../../../redux/store/store";

interface CreateAvailabilityAtParentProps{
    data:any
}


const CreateAvailabilityAtParent = ({data}:CreateAvailabilityAtParentProps) => {

    const [chartThemeOverridesG1 , setChartThemeOverridesG1] = useState<any>(undefined)
    const [chartThemeOverridesG2 , setChartThemeOverridesG2] = useState<any>(undefined)

    const [rowData1,setRowData1] = useState<any>([])
    const [rowData2,setRowData2] = useState<any>([])

    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const PRODUCT_PERMISSION_L1 = EnvConfig['PRODUCT_PERMISSION_L1']; 
    const PRODUCT_PERMISSION_L2 = EnvConfig['PRODUCT_PERMISSION_L2']; 
    const PRODUCT_PERMISSION_L3 = EnvConfig['PRODUCT_PERMISSION_L3']; 
    
    const LOCATION_PERMISSION_L1 = EnvConfig['LOCATION_PERMISSION_L1']; 
    const LOCATION_PERMISSION_L2 = EnvConfig['LOCATION_PERMISSION_L2']; 
    const LOCATION_PERMISSION_L3 = EnvConfig['LOCATION_PERMISSION_L3']; 

    const mapUIConfigToColdefs1 = (columns:Array<{header:string,colCode:string}>) => {
        let colDefs = [];

        const customColdefs = [
            {
                field:'WHDescription',
                colId:'WHDescription',
                headerName:'Parent Location Name'
            },
            {
                field:'Counts',
                colId:'Counts',
                headerName:'Count Of SKU Locations',
                filter:"agNumberColumnFilter"

            },
            {
                field:'BlackCount',
                colId:'BlackCount',
                headerName:'Black',
                filter:"agNumberColumnFilter"

              },
              {
                  field:'RedCount',
                  colId:'RedCount',
                  headerName:'Red',
                  filter:"agNumberColumnFilter"

              },
          
        ]
        
        colDefs = columns.map((column:{header:string,colCode:string})=>{
            const customColdef = getProductAndLocationHeirarchiesFromEnv(column,{} , PRODUCT_PERMISSION_L1 , PRODUCT_PERMISSION_L2 , PRODUCT_PERMISSION_L3 , LOCATION_PERMISSION_L1 , LOCATION_PERMISSION_L2 , LOCATION_PERMISSION_L3);  

            if(customColdef) return customColdef
            return {
                field:column['colCode'],
                colId:column['colCode'],
                headerName:column['header']
            }
        })
        return [...customColdefs,...colDefs];
    }

    const colDefs1 = mapUIConfigToColdefs1(data['maxEcoBlackRedWithNilRationedStockForRecievingLocations']['uiconfig']);

    const mapUIConfigToColdefs2 = (columns:Array<{header:string,colCode:string}>) => {
        let colDefs = [];


        const customColdefs = [
            {
                field:'WHDescription',
                colId:'WHDescription',
                headerName:'Parent Location Name'
            },
            {
                field:'SKUCounts',
                colId:'SKUCounts',
                headerName:'Count Of SKU Locations',
                filter:"agNumberColumnFilter"

            },
            {
                field:'BlackCount',
                colId:'BlackCount',
                headerName:'Black',
                filter:"agNumberColumnFilter"

              },
              {
                  field:'RedCount',
                  colId:'RedCount',
                  headerName:'Red',
                  filter:"agNumberColumnFilter"

              },
        ]
        
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

    const colDefs2 = mapUIConfigToColdefs2(data['maxContinousEcoBlackRedWithNilRationedStockAvailableForRecievingLocations']['uiconfig']);


    const sortData = (data:any,key:string|string[],) => {
    
        data.sort((row1:any,row2:any)=>{
          if(typeof key === 'string') return (row2[key]) - (row1[key])
      
          if(Array.isArray(key) && key.length > 0){
            const row1Sum = key.reduce((accumulator,currentKey:string)=>accumulator + row1[currentKey],0);
            const row2Sum = key.reduce((accumulator,currentKey:string)=>accumulator + row2[currentKey],0);
            return row2Sum-row1Sum
          }
          
        })
        return [...data];
      }


    useEffect(()=>{
        const formattedRowData1 = sortData(convertToInt(data['maxEcoBlackRedWithNilRationedStockForRecievingLocations']['data'],['BlackCount','RedCount']),['BlackCount','RedCount'])
        setRowData1(formattedRowData1)
        setChartThemeOverridesG1(generateChartOptions(formattedRowData1,chartParams1,undefined))
        
        const formattedRowData2 = sortData(convertToInt(data['maxContinousEcoBlackRedWithNilRationedStockAvailableForRecievingLocations']['data'],['BlackCount','RedCount']),['BlackCount','RedCount'])
        setRowData2(formattedRowData2)
        setChartThemeOverridesG2(generateChartOptions(formattedRowData2,chartParams2,undefined))
    },[])

    const getChartToolbarItems:any = () => ['chartDownload'];
     
    return(
        <>
            <SCDynamicContainer>
                <Allotment>
                    <Allotment.Pane>


                    <VFCharts     
                        height={'95%'}
                        chartParams={chartParams1}
                        colDefs={colDefs1}
                        rowData={rowData1}
                        chartProps={chartThemeOverridesG1}
                        containerStyle={{marginLeft:'0px',marginRight:'10px'}}
                        />


                    </Allotment.Pane>
                    <Allotment.Pane>

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
    )
    
}

export default CreateAvailabilityAtParent;