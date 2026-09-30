import {useState, useEffect} from "react";
import { Allotment } from "allotment";
import "allotment/dist/style.css";
import {SCDynamicContainer} from '../style';
import { useGetChronicUnavailabilityLoc,useGetChronicUnavailabilitySku} from "../../../../../Services/MTA/InsightsAndTrends";
import VFCharts from "../../../../../../components/VectorFLOW/commons/VFCharts";
import { coldefs1, coldefs2 } from "./colDef";
import { chartParams1, chartParams2} from './chartParams'
import { generateChartOptions } from '../../../../../../helpers/utils'
import OverlayLoader from "../../../../../../VectorFlow/Pages/MTO/Common/Loader";

const ChronicUnavailabilityCharts = ({filter}:{filter:any}) => {

    const { mutateAsync: ChronicUnavailabilityLoc, isLoading: isLoadingChronicLoc } =
    useGetChronicUnavailabilityLoc();
    const { mutateAsync: ChronicUnavailabilitySku, isLoading: isLoadingChronicSku } =
    useGetChronicUnavailabilitySku();

    const [ChronicUnavailabilityLocData, SetChronicUnavailabilityLocD]=useState([]);
    const [ChronicUnavailabilitySkuData, SetActiveDBMSuggestionData]=useState([]);

    const [chartThemeOverridesG1 , setChartThemeOverridesG1] = useState<any>(undefined)
    const [chartThemeOverridesG2 , setChartThemeOverridesG2] = useState<any>(undefined)

    const [rowData1,setRowData1] = useState<any>([])
    const [rowData2,setRowData2] = useState<any>([])

    useEffect(() => {
        const fetchDBMNormSuggestionData = async ()=>{
          const ChronicUnavailabilityLocs =  await  ChronicUnavailabilityLoc();
          SetChronicUnavailabilityLocD(ChronicUnavailabilityLocs?.data?.data);
          const ChronicUnavailabilitySkus = await ChronicUnavailabilitySku();
          SetActiveDBMSuggestionData(ChronicUnavailabilitySkus?.data?.data);
         
        }
        fetchDBMNormSuggestionData();
       
      }, [filter]);


    const convertToInt = (data:any)=>{
        return data?.map((row:any)=>{
            const tempObj:any = {};
            Object.keys(row).forEach((key:string)=>{
                const value = parseFloat(row[key])
                if(key==='sku'){
                    tempObj[key] = row[key];
                }else if(!isNaN(value)){
                    tempObj[key] = value
                }else{
                    tempObj[key] = row[key];
                }
            })
            return {...tempObj}
        })
    }

    const sortData = (data:any,key:string) => {
        if(data){
            data?.sort((row1:any,row2:any)=>{
                return (row2[key]) - (row1[key])
            })
    
            return [...data]
        }
        return []
    }


    useEffect(()=>{
        if(ChronicUnavailabilityLocData){
            const formattedRowData1 = sortData(convertToInt(ChronicUnavailabilityLocData),'countSku')
            setRowData1(formattedRowData1)
            setChartThemeOverridesG1(generateChartOptions(formattedRowData1,chartParams1,undefined))
        }
        if(ChronicUnavailabilitySkuData){
            const formattedRowData2 = sortData(convertToInt(ChronicUnavailabilitySkuData),'countLoc')
            setRowData2(formattedRowData2)
            setChartThemeOverridesG2(generateChartOptions(formattedRowData2,chartParams2,undefined))
        }
    },[ChronicUnavailabilityLocData,ChronicUnavailabilitySkuData])


   if(isLoadingChronicSku || isLoadingChronicLoc){
        return <OverlayLoader/>
    } 
    return(
        <>
            <SCDynamicContainer style={{marginTop:'10px'}}>
                <Allotment>
                    <Allotment.Pane minSize={440} preferredSize={'50%'}>

                        <VFCharts     
                            height={'95%'}
                            chartParams={chartParams1}
                            colDefs={coldefs1}
                            rowData={rowData1}
                            chartProps={chartThemeOverridesG1}
                            containerStyle={{marginLeft:'0px',marginRight:'10px'}}
                        />


                    </Allotment.Pane>
                    <Allotment.Pane minSize={440} preferredSize={'50%'} >
                        
                        <VFCharts     
                            height={'95%'}
                            chartParams={chartParams2}
                            colDefs={coldefs2}
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

export default ChronicUnavailabilityCharts;