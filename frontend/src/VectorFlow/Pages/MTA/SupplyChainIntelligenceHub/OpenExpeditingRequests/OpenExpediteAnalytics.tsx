import { useMemo } from "react"
import { useUserData } from "../../../../../context"
import {  useGetOpenExpediteAnalytics } from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR"
import { BPRParticularAnalyticsWrapper,BPRParticularAnalyticsTableWrapper, BPRParticularAnalyticsTableHeaderWrapper, BPRParticularAnalyticsTableHeader, BPRParticularAnalyticsTableRowWrapper, BPRParticularAnalyticsTableRow, BPRParticularAnalyticsTableCell } from "../../Logistics/InTransitWhereAbouts/styles"


const OpenExpediteAnalytics = ()=>{


    const {data} = useGetOpenExpediteAnalytics()

    const rowData = useMemo(()=>{
        if(data)return data.data.data[0]
        return {nr:0,ur:0,sumplpd:0}
    },[data])

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    return(
        <BPRParticularAnalyticsWrapper>
            <BPRParticularAnalyticsTableWrapper themeUi={themeUi}>
                <BPRParticularAnalyticsTableHeaderWrapper>
                    <BPRParticularAnalyticsTableHeader style={{textAlign:'left'}}>
                        Particulars
                    </BPRParticularAnalyticsTableHeader>
                    <BPRParticularAnalyticsTableHeader style={{textAlign:'right',maxWidth:80}}>
                        Count (Today)
                    </BPRParticularAnalyticsTableHeader>
                </BPRParticularAnalyticsTableHeaderWrapper>
                <BPRParticularAnalyticsTableRowWrapper>
                    <BPRParticularAnalyticsTableRow>
                        <BPRParticularAnalyticsTableCell style={{textAlign:'left'}}>
                            Sum Potential Loss Of Margin
                        </BPRParticularAnalyticsTableCell>
                        <BPRParticularAnalyticsTableCell style={{textAlign:'right',maxWidth:80}}>
                            {rowData.sumplpd}
                        </BPRParticularAnalyticsTableCell>
                    </BPRParticularAnalyticsTableRow>
                    <BPRParticularAnalyticsTableRow>
                        <BPRParticularAnalyticsTableCell style={{textAlign:'left'}}>
                            No. of Requests
                        </BPRParticularAnalyticsTableCell>
                        <BPRParticularAnalyticsTableCell style={{textAlign:'right',maxWidth:80}}>
                            {rowData.nr}
                        </BPRParticularAnalyticsTableCell>
                    </BPRParticularAnalyticsTableRow>
                    <BPRParticularAnalyticsTableRow>
                        <BPRParticularAnalyticsTableCell style={{textAlign:'left'}}>
                            No. of Unactioned Requests
                        </BPRParticularAnalyticsTableCell>
                        <BPRParticularAnalyticsTableCell style={{textAlign:'right',maxWidth:80}}>
                            {rowData.ur}
                        </BPRParticularAnalyticsTableCell>
                    </BPRParticularAnalyticsTableRow>
                </BPRParticularAnalyticsTableRowWrapper>
            </BPRParticularAnalyticsTableWrapper>

        </BPRParticularAnalyticsWrapper>
    )
}

export default OpenExpediteAnalytics