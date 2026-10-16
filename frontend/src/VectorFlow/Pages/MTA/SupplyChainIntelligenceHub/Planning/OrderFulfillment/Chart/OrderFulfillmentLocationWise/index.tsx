import {useState, useEffect} from "react";
import { Allotment } from "allotment";
import "allotment/dist/style.css";
// import "../../styles.css";
import { ColDef } from "ag-grid-enterprise";
import {SCDynamicContainer} from '../../styles';
import VFCharts from "../../../../../../../../components/VectorFLOW/commons/VFCharts";
import {convertToInt, getProductAndLocationHeirarchiesFromEnv,generateChartOptions} from '../../../../../../../../helpers/utils';
import { chartParams1 , chartParams2 } from './chartParams' 
import { useSelector } from "react-redux";
import { RootState } from "../../../../../../../../redux/store/store";
interface OrderFulfillmentProps{
    data:any
}


const OrderFulfillmentLocationWise = ({data}:OrderFulfillmentProps) => {

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

        const customColdefs:ColDef[] = [
            {
                field:'location',
                headerName:'Location Name',
                colId:'location',
            },
            {
                field:'overdue',
                headerName:'Overdue',
                colId:'overdue',
                filter:"agNumberColumnFilter"
            },
            {
                field:'due',
                headerName:'Due',
                colId:'due',
                filter:"agNumberColumnFilter"

            },
            {
                field:'others',
                headerName:'Others',
                colId:'others',
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

    const colDefs1 = mapUIConfigToColdefs1(data['maximumOverdueOrders']['uiconfig']);

    const mapUIConfigToColdefs2 = (columns:Array<{header:string,colCode:string}>) => {
        let colDefs = [];

        const customColdefs:ColDef[] = [
            {
                field:'location',
                headerName:'Location Name',
                colId:'location',
            },
            {
                field:'greater',
                headerName:'Gap > 67%',
                colId:'greater',
                filter:"agNumberColumnFilter"

            },
            {
                field:'between',
                headerName:'33% <= Gap <= 67%',
                colId:'between',
                filter:"agNumberColumnFilter"

            },
            {
                field:'smaller',
                headerName:'Gap < 33%',
                colId:'smaller',
                filter:"agNumberColumnFilter"

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

    const colDefs2 = mapUIConfigToColdefs2(data['maxSkuWithGap']['uiconfig']);

    // P1 F4: preserve API title-specific ranking and stable code tie ordering.


    useEffect(()=>{
        const formattedRowData1 = convertToInt(data['maximumOverdueOrders']['data'],['overdue','due','others'])
        setRowData1(formattedRowData1)
        setChartThemeOverridesG1(generateChartOptions(formattedRowData1,chartParams1,undefined))
        
        const formattedRowData2 = convertToInt(data['maxSkuWithGap']['data'],['greater','between','smaller'])
        setRowData2(formattedRowData2)
        setChartThemeOverridesG2(generateChartOptions(formattedRowData2,chartParams2,undefined))
    },[data])


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

export default OrderFulfillmentLocationWise;
