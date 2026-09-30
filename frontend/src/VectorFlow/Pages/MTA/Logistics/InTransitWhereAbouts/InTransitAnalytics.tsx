import { useMemo } from "react"
import { useUserData } from "../../../../../context"
import { useGetInTransitWhereAboutAnalytics } from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR"
import { BPRParticularAnalyticsWrapper,BPRParticularAnalyticsTableWrapper, BPRParticularAnalyticsTableHeaderWrapper, BPRParticularAnalyticsTableHeader, BPRParticularAnalyticsTableRowWrapper, BPRParticularAnalyticsTableRow, BPRParticularAnalyticsTableCell } from "./styles"


const InTransitAnalytics = ()=>{


    const {data} = useGetInTransitWhereAboutAnalytics()

    const rowData = useMemo(()=>{
        if(data)return data.data.data[0]
        return {d:0,it:0}
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
                            InTransit
                        </BPRParticularAnalyticsTableCell>
                        <BPRParticularAnalyticsTableCell style={{textAlign:'right',maxWidth:80}}>
                            {rowData.it}
                        </BPRParticularAnalyticsTableCell>
                    </BPRParticularAnalyticsTableRow>
                    <BPRParticularAnalyticsTableRow>
                        <BPRParticularAnalyticsTableCell style={{textAlign:'left'}}>
                            Delayed
                        </BPRParticularAnalyticsTableCell>
                        <BPRParticularAnalyticsTableCell style={{textAlign:'right',maxWidth:80}}>
                            {rowData.d}
                        </BPRParticularAnalyticsTableCell>
                    </BPRParticularAnalyticsTableRow>
                </BPRParticularAnalyticsTableRowWrapper>
            </BPRParticularAnalyticsTableWrapper>

        </BPRParticularAnalyticsWrapper>
    )
}

export default InTransitAnalytics