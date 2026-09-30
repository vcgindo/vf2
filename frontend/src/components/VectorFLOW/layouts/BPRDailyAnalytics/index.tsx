
import { ColDef } from 'ag-grid-enterprise'
import React, { useMemo,useEffect ,useState} from 'react'
import { useSelector } from 'react-redux'
import { useLocation } from 'react-router'
import { RootState } from '../../../../redux/store/store'
import { routerToAnalyticsStringMap } from '../../../../helpers/BPRConstants'
import { useGetAnalyticsData } from '../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR'
import { toast } from "react-toastify";
import {
    BPRDailyAnalyticsHeader,
    BPRDailyAnalyticsContainer,
    BPRDailyAnalyticsTableCell,
    BPRDailyAnalyticsTableContainer,
    BPRDailyAnalyticsTableHeader,
    BPRDailyAnalyticsTableHeaderContainer,
    BPRDailyAnalyticsTableRow,
    BPRDailyAnalyticsTableRowContainer,
    BPRDailyAnalyticStatusBar,
    BPRDailyAnalyticsWrapper,
    BPRDailyAnalyticsTableChangeIcon,
    BPRDailyAnalyticsTableNoChangeWrapper,
    BPRDailyAnalyticStatusBarSection,
    BPRDailyAnalyticsTableCellHeader,
    BPRDailyAnalyticsTableCellText,
    BPRDailyAnalyticsTableCellIcon
} from './styles'
import { useUserData } from '../../../../context'

interface BPRDailyAnalyticsProps{
    colDefs:ColDef[]
}

const BPRDailyAnalytics = (props:BPRDailyAnalyticsProps)=>{

    const {
        colDefs
    } =props
    const [rowData,setRowData] = useState<Array<any>>([])

    const {mutateAsync:getAnalyticsData,isLoading} = useGetAnalyticsData()
    const {currentCategory,currentTab} = useSelector((state:RootState)=>state.mta.planning)
    const MTAVFMultiFilter = useSelector((state: RootState) => state.mta.mtaVFMultiFilter);

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    
    const summation = useMemo(()=>{
        let temp = 0
         rowData.forEach((row:any)=>{
            temp +=row.techCount
        })
        return temp
    },[rowData])

    function transformAnalyticsData(data: Array<any>): Array<any> {
        if (!data || data.length === 0 || !data[0]) {
            return [];
        }
        const analyticsData = data[0];
        const colors = ['Black', 'Red', 'Yellow', 'Green', 'White', 'Blue', 'Grey'];
        
        const result = colors.map(color => ({
            color: color,
            techCount: analyticsData[`OnHand${color}`] || 0,
            ecoCount: analyticsData[`Pipeline${color}`] || 0,
        }));

        return result;
    }
      


    // const onGetAnalyticsData = async()=>{
    //     try{
    //         // const data = await getAnalyticsData({reportname :payloadString})
    //         // setRowData(aggregateAnalyticsData(activeReportData , lastRunDate))
    //     }catch(err:any){
    //         setRowData([])
    //     }

    // }

    const onGetAnalyticsData = async(filter:any)=>{
        const pathname:string = location.pathname;
        let payloadString = "";
        if(location.pathname==='/mta/supply-chain-intelligence-hub/planning'){
            if(currentCategory!==""){
                switch(currentCategory){
                    case "GITFromParent":
                        payloadString = "gitparent"
                        break
                    case "GITToChild":
                        payloadString = currentTab==="locationWise" ? "gitchildlocation" : "gitchildtransporter"
                        break
                    case "ExpediteFromParent":
                        payloadString = "expediteparent"
                        break
                    case "ExpediteToChild":
                        payloadString = "expeditechild"
                        break
                    case "ExcessInventory":
                        payloadString = "excessinventory"
                        break
                    case "OrderFulfillment":
                        payloadString = "orderfulfillment"
                        break
                    default:
                        return
                }
            }
            else{
                payloadString = "planning"
            }
        }
        else payloadString = routerToAnalyticsStringMap[pathname]
        try{
            const rowData =await  getAnalyticsData({
                id: 1,
                name: payloadString,
                fields: [],
                filters:filter,
            })
            
            if(rowData.data.data) {
                setRowData(transformAnalyticsData(rowData.data.data));
            }
            else setRowData([])
        }
        catch (Exception:any){
            toast.dismiss()
            toast.error("Error in loading Analytics Data")
            setRowData([])
        }
    }
    useEffect(()=>{
        onGetAnalyticsData(MTAVFMultiFilter)
    },[MTAVFMultiFilter])





    
    
    if(isLoading){
        return(
            <BPRDailyAnalyticsWrapper>
                <BPRDailyAnalyticsContainer theme={themeUi} style={{aspectRatio:'0.9',width:'90%'}}>
                    <BPRDailyAnalyticsHeader theme={themeUi}>
                        Analytics (SKU Locations)
                    </BPRDailyAnalyticsHeader>
                    <div style={{width:'100%',height:'100%',display:'grid',placeItems:'center'}}>
                    <p style={{color:'white'}}>Loading ...</p>
                    </div>
                </BPRDailyAnalyticsContainer>
            </BPRDailyAnalyticsWrapper>
        )
    }
    
    if(!rowData || !Array.isArray(rowData) || rowData?.length===0){
        return(
            <BPRDailyAnalyticsWrapper>
                <BPRDailyAnalyticsContainer theme={themeUi} style={{aspectRatio:'0.9',width:'90%'}}>
                    <BPRDailyAnalyticsHeader theme={themeUi}>
                        Analytics (SKU Locations)
                    </BPRDailyAnalyticsHeader>
                    <div style={{width:'100%',height:'100%',display:'grid',placeItems:'center'}}>
                    <p style={{color:'white'}}>No data to show</p>
                    </div>
                </BPRDailyAnalyticsContainer>
            </BPRDailyAnalyticsWrapper>
        )
    }
    


    return(
        <BPRDailyAnalyticsWrapper>
            <BPRDailyAnalyticsContainer theme={themeUi}>
            <BPRDailyAnalyticsHeader theme={themeUi}>
                Analytics (SKU Locations)
            </BPRDailyAnalyticsHeader>
            <BPRDailyAnalyticsTableContainer>
                <BPRDailyAnalyticsTableHeaderContainer>
                    {
                        colDefs.map((colDef:ColDef)=>{
                            if(colDef.colId==='color'){
                                return(
                                    <BPRDailyAnalyticsTableHeader style={{width:110}}/>
                                )
                            }
                            return(
                                <BPRDailyAnalyticsTableHeader>
                                    {colDef.headerName}
                                </BPRDailyAnalyticsTableHeader>
                            )
                        })
                    }
                </BPRDailyAnalyticsTableHeaderContainer>
                <BPRDailyAnalyticsTableRowContainer>
                    {rowData.map((row:any)=>{
                        return(
                            <BPRDailyAnalyticsTableRow>
                               {Object.keys(row).map((key:string)=>{
                                   if(key==='color'){
                                        return(
                                            <BPRDailyAnalyticsTableCell style={{backgroundColor:row[key],width:60,boxShadow: "0px 3px 12px #AFAFAF"}}/>
                                        )
                                   }
                                  if(key=='techCount'){
                                    return(
                                        <React.Fragment>
                                            <BPRDailyAnalyticsTableCell>
                                                <BPRDailyAnalyticsTableCellHeader>{row[key]}</BPRDailyAnalyticsTableCellHeader>
                                                {/* <BPRDailyAnalyticsTableCellText>{getCellText(row.techChange,'techChange')}</BPRDailyAnalyticsTableCellText> */}
                                            </BPRDailyAnalyticsTableCell>
                                            {/* <BPRDailyAnalyticsTableCell>
                                                {getCellIcons(row.techChange)}
                                            </BPRDailyAnalyticsTableCell> */}
                                        </React.Fragment>
                                    )
                                  }
                                  if( key==='ecoCount'){
                                    return(
                                        <React.Fragment>
                                            <BPRDailyAnalyticsTableCell>
                                                <BPRDailyAnalyticsTableCellHeader>{row[key]}</BPRDailyAnalyticsTableCellHeader>
                                                {/* <BPRDailyAnalyticsTableCellText>{getCellText(row.ecoChange,'ecoChange')}</BPRDailyAnalyticsTableCellText> */}
                                            </BPRDailyAnalyticsTableCell>
                                           {/* <BPRDailyAnalyticsTableCell>
                                                {getCellIcons(row.ecoChange)}
                                           </BPRDailyAnalyticsTableCell> */}
                                        </React.Fragment>
                                    )
                                  }
                               })}
                            </BPRDailyAnalyticsTableRow>
                        )
                    })}
                </BPRDailyAnalyticsTableRowContainer>
            </BPRDailyAnalyticsTableContainer>
            <BPRDailyAnalyticStatusBar>
                <BPRDailyAnalyticStatusBarSection>
                    Total
                </BPRDailyAnalyticStatusBarSection>
                <BPRDailyAnalyticStatusBarSection>
                    {summation}
                </BPRDailyAnalyticStatusBarSection>
            </BPRDailyAnalyticStatusBar>
        </BPRDailyAnalyticsContainer>
        </BPRDailyAnalyticsWrapper>
    )
}

export default BPRDailyAnalytics