import {useMemo} from 'react'
import { useUserData } from "../../../../../context"
import { RRRAnalyticsContainer, RRRAnalyticsHeader, RRRAnalyticsTableContainer, RRRAnalyticsTableHeaderWrapper, RRRAnalyticsWrapper,RRRAnalyticsTableHeader,  RRRAnalyticsTableRowContainer, RRRAnalyticsTableRow, RRRAnalyticsTableCell} from "../../SupplyChainIntelligenceHub/RationedRequirementReport/styles"
import { useGetDBMAnalyticsData } from '../../../../../VectorFlow/Services/MTA/DBM'


const DBMAnalytics = ()=>{

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    const {data} = useGetDBMAnalyticsData()

   

    const rowData = useMemo(()=>{
        if(data && data.data && data.data.data && Array.isArray(data.data.data)){
            const result:any = {

            }
            const rawData = data.data.data[0]
            Object.keys(rawData).map((k:string)=>{
                result[k] = rawData[k][0]
            })
            return result
        }
        return {
            "nofsugg": {
                "u": 0,
                "d": 0
            },
            "acc": {
                "u": 0,
                "d": 0
            },
            "sleep": {
                "u": 0,
                "d": 0
            }
        }
    },[data])

    console.log(rowData)


    return(
        <RRRAnalyticsWrapper>
           <RRRAnalyticsContainer themeUi={themeUi}>
                <RRRAnalyticsHeader style={{paddingLeft:'10px'}}>Analytics</RRRAnalyticsHeader>
                <RRRAnalyticsTableContainer style={{padding:'4px 10px'}}>
                    <RRRAnalyticsTableHeaderWrapper>
                        <RRRAnalyticsTableHeader style={{maxWidth:'60px'}}/>
                        <RRRAnalyticsTableHeader>
                            No Of<br/> Upward
                        </RRRAnalyticsTableHeader>
                        <RRRAnalyticsTableHeader>
                            No Of<br/> Downward
                        </RRRAnalyticsTableHeader>
                    </RRRAnalyticsTableHeaderWrapper>
                    <RRRAnalyticsTableRowContainer>
                        <RRRAnalyticsTableRow style={{border:'none'}}>
                            <RRRAnalyticsTableCell style={{height:'40px',maxWidth:'60px',textAlign:'center'}}>
                                No Of Suggestion 
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell style={{height:'40px'}}>
                                {rowData.nofsugg.u}
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell style={{height:'40px'}}>
                                {rowData.nofsugg.d}
                            </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                        <RRRAnalyticsTableRow style={{border:'none'}}>
                            <RRRAnalyticsTableCell style={{height:'40px',maxWidth:'60px',textAlign:'center'}}>
                                Suggestion Accepted 
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell style={{height:'40px'}}>
                                {rowData.acc.u}
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell style={{height:'40px'}}>
                                {rowData.acc.d}
                            </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                        <RRRAnalyticsTableRow style={{border:'none'}}>
                            <RRRAnalyticsTableCell style={{height:'40px',maxWidth:'60px',textAlign:'center'}}>
                                Suggestion Put On Sleep
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell style={{height:'40px'}}>
                                {rowData.sleep.u}
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell style={{height:'40px'}}>
                                {rowData.sleep.d}
                            </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                    </RRRAnalyticsTableRowContainer>
                </RRRAnalyticsTableContainer>
           </RRRAnalyticsContainer>
        </RRRAnalyticsWrapper>
    )
}

export default DBMAnalytics