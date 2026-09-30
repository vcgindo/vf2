import {useState, useEffect, useMemo} from "react";
import { Allotment } from "allotment";
import "allotment/dist/style.css";
import "../../styles.css";
import {SCDynamicContainer} from '../../styles';
import {convertToInt, getProductAndLocationHeirarchiesFromEnv, generateChartOptions} from '../../../../../../../../helpers/utils';
import VFCharts from "../../../../../../../../components/VectorFLOW/commons/VFCharts";
import {createChartParams} from './chartParams'
import { useSelector } from "react-redux";
import { RootState } from "../../../../../../../../redux/store/store";
interface ExcessInventoryProps{
    data:any
}

const ExcessInventoryLocationWise = ({data}:ExcessInventoryProps) => {
    
    const [chartThemeOverridesG1 , setChartThemeOverridesG1] = useState<any>(undefined)
    const [chartThemeOverridesG2 , setChartThemeOverridesG2] = useState<any>(undefined)

    const [rowData1,setRowData1] = useState<any>([])
    const [rowData2,setRowData2] = useState<any>([])

    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const currency = EnvConfig?.CURRENCY || 'Rupee';
    const PRODUCT_PERMISSION_L1 = EnvConfig['PRODUCT_PERMISSION_L1']; 
    const PRODUCT_PERMISSION_L2 = EnvConfig['PRODUCT_PERMISSION_L2']; 
    const PRODUCT_PERMISSION_L3 = EnvConfig['PRODUCT_PERMISSION_L3']; 
    
    const LOCATION_PERMISSION_L1 = EnvConfig['LOCATION_PERMISSION_L1']; 
    const LOCATION_PERMISSION_L2 = EnvConfig['LOCATION_PERMISSION_L2']; 
    const LOCATION_PERMISSION_L3 = EnvConfig['LOCATION_PERMISSION_L3']; 
    // Generate the two different chart parameter objects from the single function
    const chartParams1 = useMemo(() => createChartParams('sku', currency), [currency]);
    const chartParams2 = useMemo(() => createChartParams('value', currency), [currency]);

    const mapUIConfigToColdefs1 = (columns:Array<{header:string,colCode:string}>) => {
        let colDefs = [];

        const customColdefs = [
            {
                field:'WHDescription',
                colId:'WHDescription',
                headerName:'Location Name',
                
            },
            {
                field:'SKUCounts',
                colId:'SKUCounts',
                headerName:'Count Of SKUs',
                filter:"agNumberColumnFilter",
            }
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

    const colDefs1 = mapUIConfigToColdefs1(data['topTenLocationsWithExcessInventorySkuCount']['uiconfig']);

    const mapUIConfigToColdefs2 = (columns:Array<{header:string,colCode:string}>) => {
        let colDefs = [];

        const customColdefs = [
            {
                field:'WHDescription',
                colId:'WHDescription',
                headerName:'Location Name'
            },
            {
                field:'SumOfAmount',
                colId:'SumOfAmount',
                headerName:'Value in (Lakhs)',
                filter:"agNumberColumnFilter"
            }
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

    const colDefs2 = mapUIConfigToColdefs2(data['topTenLocationsWithExcessInventoryValue']['uiconfig']);

    const sortData = (data:any,key:string) => {
        data.sort((row1:any,row2:any)=>{
            return (row2[key]) - (row1[key])
        })
        return [...data];
    }

    const scaleDown = (data:any,key:string,divisor:number)=>{
        return data.map((row:any)=>{
            const temp = {...row};
            const valueToScaleDown = (row[key] === "" || row[key] == null) ? 0 : row[key];
            temp[key] = parseInt(valueToScaleDown,10)/divisor;
            return temp;
        })
    }


    useEffect(()=>{
        const formattedRowData1 = sortData(convertToInt(data['topTenLocationsWithExcessInventorySkuCount']['data'],['SKUCounts']),'SKUCounts')
        setRowData1(formattedRowData1)
        setChartThemeOverridesG1(generateChartOptions(formattedRowData1,chartParams1,undefined))
        
        const formattedRowData2 = scaleDown(sortData(convertToInt(data['topTenLocationsWithExcessInventoryValue']['data'],['SumOfAmount']),'SumOfAmount'),'SumOfAmount',100000)
        setRowData2(formattedRowData2)
        setChartThemeOverridesG2(generateChartOptions(formattedRowData2,chartParams2,undefined))
    },[])

     
    return(
        <>
            <SCDynamicContainer>
                <Allotment>

                    <Allotment.Pane minSize={440} preferredSize={'50%'}>

                        <VFCharts     
                            height={'95%'}
                            chartParams={chartParams1}
                            colDefs={colDefs1}
                            rowData={rowData1}
                            chartProps={chartThemeOverridesG1}
                            containerStyle={{marginLeft:'0px',marginRight:'10px'}}
                        />

                    </Allotment.Pane>

                    <Allotment.Pane minSize={440} preferredSize={'50%'}>

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

export default ExcessInventoryLocationWise;