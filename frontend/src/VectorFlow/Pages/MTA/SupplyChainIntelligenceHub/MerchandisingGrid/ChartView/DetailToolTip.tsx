import { StoreDetails } from '../../../../../../VectorFlow/types/MCGrid'
import {DetailToolTipWrapper,DetailToolTipHeader,DetailToolTipGrid, DetailToolTipGridRow, DetailToolTipGridHeader, DetailToolTipGridCell, HighlightedRow} from './styles'

const DetailToolTip = (props:{data:StoreDetails})=>{

    const {
        data
    } = props
    return(
        <DetailToolTipWrapper>
            <DetailToolTipHeader>
                Details
            </DetailToolTipHeader>
            <DetailToolTipGrid>
                <DetailToolTipGridRow>
                    <DetailToolTipGridHeader >

                    </DetailToolTipGridHeader>
                    <DetailToolTipGridHeader>
                        Value (Lakhs)
                    </DetailToolTipGridHeader>
                    <DetailToolTipGridHeader >
                        PCs/ %
                    </DetailToolTipGridHeader>
                </DetailToolTipGridRow>
                <DetailToolTipGridRow>
                    <DetailToolTipGridCell>
                        Sales
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data.sales.value}
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data.sales.pcs}
                    </DetailToolTipGridCell>
                </DetailToolTipGridRow>
                <DetailToolTipGridRow>
                    <DetailToolTipGridCell>
                        Gross Margin
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data['gross-margin'].value}
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data['gross-margin'].pcs}
                    </DetailToolTipGridCell>
                </DetailToolTipGridRow>
                <HighlightedRow style={{borderRadius:'4px 4px 0px 0px'}}>
                    <DetailToolTipGridCell>
                       Planned Range
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data['planned-range'].value}
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data['planned-range'].pcs}
                    </DetailToolTipGridCell>
                </HighlightedRow>
                <HighlightedRow style={{borderBottom:'dashed 1px white'}}>
                    <DetailToolTipGridCell>
                       Range Available
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data['range-available'].value}
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data['range-available'].pcs}
                    </DetailToolTipGridCell>
                </HighlightedRow>
                <HighlightedRow style={{borderRadius:'0px 0px 4px 4px'}}>
                    <DetailToolTipGridCell>
                       Gap
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data.gap.value}
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        {data.gap.pcs}
                    </DetailToolTipGridCell>
                </HighlightedRow>
                
                {/* <DetailToolTipGridRow>
                    <DetailToolTipGridCell>
                        Sales
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        
                    </DetailToolTipGridCell>
                    <DetailToolTipGridCell>
                        
                    </DetailToolTipGridCell>
                </DetailToolTipGridRow> */}
            </DetailToolTipGrid>
        </DetailToolTipWrapper>
    )
}

export default DetailToolTip