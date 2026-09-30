import {useMemo} from 'react'
import { useUserData } from "../../../../../context"
import { RRRAnalyticsContainer, RRRAnalyticsHeader, RRRAnalyticsTableContainer, RRRAnalyticsTableHeaderWrapper, RRRAnalyticsWrapper,RRRAnalyticsTableHeader, RRRAnalyticsTableSubHeader, RRRAnalyticsTableSubHeaderSection, RRRAnalyticsSeperator, RRRAnalyticsTableRowContainer, RRRAnalyticsTableRow, RRRAnalyticsTableCell, RRRAnalyticsTableColorCell, RRRAnalyticsTableCustomCell, RRRAnalyticsTableColorCellLabel } from "../RationedRequirementReport/styles"
import { useGetBORAnalyticsData } from '../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BuyerOrderReport'
import _ from 'lodash'


const BORAnalytics = ()=>{

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    const {data} = useGetBORAnalyticsData()

   

    const rowData = useMemo(()=>{
        if(data && data.data && data.data.data && Array.isArray(data.data.data)){
            const result:any = {

            }
            const rawData = _.omit(data.data.data[0],'tob')
            Object.keys(rawData).map((k:string)=>{
                result[k] = rawData[k][0]
            })
            return result
        }
        return {
            "tor": 
              {
                "rs": 0,
                "ns": 0,
                "sc": 0
              }
            ,
            "toy": 
              {
                "rs": 0,
                "ns": 0,
                "sc": 0
              }
            ,
            "tog": 
              {
                "rs": 0,
                "ns": 0,
                "sc": 0
              }
            
          }
    },[data])

    const summation = useMemo(()=>{
        return {
            ns:rowData.tor.ns + rowData.toy.ns + rowData.tog.ns,
            rs:rowData.tor.rs + rowData.toy.rs + rowData.tog.rs,
            sc:rowData.tor.sc + rowData.toy.sc + rowData.tog.sc
        }
    },[rowData])

    return(
        <RRRAnalyticsWrapper>
           <RRRAnalyticsContainer themeUi={themeUi}>
                <RRRAnalyticsHeader style={{paddingLeft:'10px'}}>Analytics</RRRAnalyticsHeader>
                <RRRAnalyticsTableContainer>
                    <RRRAnalyticsTableHeaderWrapper>
                        <RRRAnalyticsTableHeader style={{maxWidth:'60px'}}>
                            Colors
                        </RRRAnalyticsTableHeader>
                        <RRRAnalyticsTableHeader>
                            <RRRAnalyticsTableSubHeader>
                                Requirement
                            </RRRAnalyticsTableSubHeader>
                            <RRRAnalyticsTableSubHeader>
                               <RRRAnalyticsTableSubHeaderSection >
                                    SKU Loc
                               </RRRAnalyticsTableSubHeaderSection>
                               <RRRAnalyticsSeperator themeUi={themeUi}/>
                               <RRRAnalyticsTableSubHeaderSection>
                                   Req Sum
                               </RRRAnalyticsTableSubHeaderSection>
                               <RRRAnalyticsSeperator themeUi={themeUi}/>
                               <RRRAnalyticsTableSubHeaderSection>
                                  Unique Supp. Count
                               </RRRAnalyticsTableSubHeaderSection>
                            </RRRAnalyticsTableSubHeader>
                        </RRRAnalyticsTableHeader>
                        
                    </RRRAnalyticsTableHeaderWrapper>
                    <RRRAnalyticsTableRowContainer>
                        <RRRAnalyticsTableRow>
                                <RRRAnalyticsTableCell style={{maxWidth:'60px'}}>
                                <RRRAnalyticsTableColorCell style={{backgroundColor:'#F02424'}}/>
                                <RRRAnalyticsTableColorCellLabel>TOR</RRRAnalyticsTableColorCellLabel>
                                </RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCell>
                                    <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                        {rowData.tor.ns}
                                    </RRRAnalyticsTableCustomCell>
                                    <RRRAnalyticsSeperator themeUi={themeUi}/>
                                    <RRRAnalyticsTableCustomCell>
                                        {rowData.tor.rs}
                                    </RRRAnalyticsTableCustomCell>
                                    <RRRAnalyticsSeperator themeUi={themeUi}/>
                                    <RRRAnalyticsTableCustomCell>
                                        {rowData.tor.sc}
                                    </RRRAnalyticsTableCustomCell>
                                </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                        <RRRAnalyticsTableRow>
                                <RRRAnalyticsTableCell style={{maxWidth:'60px'}}>
                                <RRRAnalyticsTableColorCell style={{backgroundColor:'#E3B92D'}}/>
                                <RRRAnalyticsTableColorCellLabel>TOY</RRRAnalyticsTableColorCellLabel>
                                </RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCell>
                                    <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                        {rowData.toy.ns}
                                    </RRRAnalyticsTableCustomCell>
                                    <RRRAnalyticsSeperator themeUi={themeUi}/>
                                    <RRRAnalyticsTableCustomCell>
                                        {rowData.toy.rs}
                                    </RRRAnalyticsTableCustomCell>
                                    <RRRAnalyticsSeperator themeUi={themeUi}/>
                                    <RRRAnalyticsTableCustomCell>
                                        {rowData.toy.sc}
                                    </RRRAnalyticsTableCustomCell>
                                </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                        <RRRAnalyticsTableRow style={{border:'none'}}>
                                <RRRAnalyticsTableCell style={{maxWidth:'60px'}}>
                                    <RRRAnalyticsTableColorCell style={{backgroundColor:'#418D18'}}/>
                                    <RRRAnalyticsTableColorCellLabel>TOG</RRRAnalyticsTableColorCellLabel>
                                </RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCell>
                                    <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                        {rowData.tog.ns}
                                    </RRRAnalyticsTableCustomCell>
                                    <RRRAnalyticsSeperator themeUi={themeUi}/>
                                    <RRRAnalyticsTableCustomCell>
                                        {rowData.tog.rs}
                                    </RRRAnalyticsTableCustomCell>
                                    <RRRAnalyticsSeperator themeUi={themeUi}/>
                                    <RRRAnalyticsTableCustomCell>
                                        {rowData.tog.sc}
                                    </RRRAnalyticsTableCustomCell>
                                </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                        <RRRAnalyticsTableRow style={{color:"white",backgroundColor:'black',borderRadius:'0px 0px  4px 4px',margin:'0px -8px -4px -8px',width:'auto',padding:'0px 8px 0px  8px'}}>
                            <RRRAnalyticsTableCell style={{maxWidth:'60px'}}>
                                Total
                            </RRRAnalyticsTableCell>
                            <RRRAnalyticsTableCell>
                                <RRRAnalyticsTableCustomCell style={{width:'100%'}}>
                                    {summation.ns}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator style={{backgroundColor:'white'}} themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {summation.rs}
                                </RRRAnalyticsTableCustomCell>
                                <RRRAnalyticsSeperator style={{backgroundColor:'white'}} themeUi={themeUi}/>
                                <RRRAnalyticsTableCustomCell>
                                    {summation.sc}
                                </RRRAnalyticsTableCustomCell>
                            </RRRAnalyticsTableCell>
                        </RRRAnalyticsTableRow>
                    </RRRAnalyticsTableRowContainer>
                </RRRAnalyticsTableContainer>
           </RRRAnalyticsContainer>
        </RRRAnalyticsWrapper>
    )
}

export default BORAnalytics