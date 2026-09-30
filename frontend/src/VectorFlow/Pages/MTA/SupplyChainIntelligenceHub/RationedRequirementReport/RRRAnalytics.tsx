import {useMemo} from 'react'
import { useGetRRRAnalyticsData } from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/RRR"
import { useUserData } from "../../../../../context"
import { RRRAnalyticsContainer, RRRAnalyticsHeader, RRRAnalyticsTableContainer, RRRAnalyticsTableHeaderWrapper, RRRAnalyticsWrapper,RRRAnalyticsTableHeader, RRRAnalyticsTableSubHeader, RRRAnalyticsTableSubHeaderSection, RRRAnalyticsSeperator, RRRAnalyticsTableRowContainer, RRRAnalyticsTableRow, RRRAnalyticsTableCell, RRRAnalyticsTableColorCell, RRRAnalyticsTableCustomCell } from "./styles"



const RRRAnalytics = ()=>{

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    const {data} = useGetRRRAnalyticsData()

    const rowData = useMemo(()=>{
        if(data && data.data && data.data.data && Array.isArray(data.data.data))return data.data.data[0]
        return {
            "br": 0,
            "rr": 0,
            "yr": 0,
            "gr": 0,
            "bc": 0,
            "rc": 0,
            "yc": 0,
            "gc": 0,
            "brr": 0,
            "rrr": 0,
            "yrr": 0,
            "grr": 0,
            "brc": 0,
            "rrc": 0,
            "yrc": 0,
            "grc": 0
          }
    },[data])

    const summation = useMemo(()=>{
        return {
            rt:rowData.br + rowData.rr + rowData.yr + rowData.gr,
            ct:rowData.bc + rowData.rc + rowData.yc + rowData.gc,
            rrt:rowData.brr + rowData.rrr + rowData.yrr + rowData.grr,
            rct:rowData.brc + rowData.rrc + rowData.yrc + rowData.grc
        }
    },[rowData])

    return(
        <RRRAnalyticsWrapper>
           <RRRAnalyticsContainer themeUi={themeUi}>
                <RRRAnalyticsHeader style={{paddingLeft:'4px'}}>Analytics</RRRAnalyticsHeader>
                <RRRAnalyticsTableContainer>
                    <RRRAnalyticsTableHeaderWrapper>
                        <RRRAnalyticsTableHeader style={{maxWidth:'40px'}}>
                            Colors
                        </RRRAnalyticsTableHeader>
                        <RRRAnalyticsTableHeader>
                            <RRRAnalyticsTableSubHeader>
                                Requirement
                            </RRRAnalyticsTableSubHeader>
                            <RRRAnalyticsTableSubHeader>
                               <RRRAnalyticsTableSubHeaderSection style={{width:'100%'}}>
                                    Qty
                               </RRRAnalyticsTableSubHeaderSection>
                               <RRRAnalyticsSeperator themeUi={themeUi}/>
                               <RRRAnalyticsTableSubHeaderSection>
                                   SKU Loc
                               </RRRAnalyticsTableSubHeaderSection>
                            </RRRAnalyticsTableSubHeader>
                        </RRRAnalyticsTableHeader>
                        <RRRAnalyticsTableHeader>
                            <RRRAnalyticsTableSubHeader>
                                Rationing
                            </RRRAnalyticsTableSubHeader>
                            <RRRAnalyticsTableSubHeader>
                               <RRRAnalyticsTableSubHeaderSection style={{width:'100%'}}>
                                    Qty
                               </RRRAnalyticsTableSubHeaderSection>
                               <RRRAnalyticsSeperator themeUi={themeUi}/>
                               <RRRAnalyticsTableSubHeaderSection>
                                   SKU Loc
                               </RRRAnalyticsTableSubHeaderSection>
                            </RRRAnalyticsTableSubHeader>
                        </RRRAnalyticsTableHeader>
                    </RRRAnalyticsTableHeaderWrapper>
                    <RRRAnalyticsTableRowContainer>
                        <RRRAnalyticsTableRow>
                            <RRRAnalyticsTableCell style={{maxWidth:'40px'}}>
                               <RRRAnalyticsTableColorCell style={{backgroundColor:'black'}}/>
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {rowData.br}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {rowData.bc}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {rowData.brr}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {rowData.brc}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                        <RRRAnalyticsTableRow>
                            <RRRAnalyticsTableCell style={{maxWidth:'40px'}}>
                               <RRRAnalyticsTableColorCell style={{backgroundColor:'#F02424'}}/>
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {rowData.rr}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {rowData.rc}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {rowData.rrr}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {rowData.rrc}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                        <RRRAnalyticsTableRow>
                            <RRRAnalyticsTableCell style={{maxWidth:'40px'}}>
                               <RRRAnalyticsTableColorCell style={{backgroundColor:'#E3B92D'}}/>
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {rowData.yr}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {rowData.yc}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {rowData.yrr}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {rowData.yrc}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                        <RRRAnalyticsTableRow style={{border:'none'}}>
                            <RRRAnalyticsTableCell style={{maxWidth:'40px'}}>
                               <RRRAnalyticsTableColorCell style={{backgroundColor:'#418D18'}}/>
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {rowData.gr}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {rowData.gc}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {rowData.grr}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {rowData.grc}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                        <RRRAnalyticsTableRow style={{color:"white",backgroundColor:'black',borderRadius:'0px 0px  4px 4px',margin:'0px -8px -4px -8px',width:'auto',padding:'0px 8px 0px  8px'}}>
                            <RRRAnalyticsTableCell style={{maxWidth:'40px'}}>
                                Total
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {summation.rt}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator style={{backgroundColor:'white'}} themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {summation.ct}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {summation.rrt}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator style={{backgroundColor:'white'}} themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {summation.rct}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                    </RRRAnalyticsTableRowContainer>
                </RRRAnalyticsTableContainer>
           </RRRAnalyticsContainer>
        </RRRAnalyticsWrapper>
    )
}

export default RRRAnalytics