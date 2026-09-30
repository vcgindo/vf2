import { seasonalityQuickFilterData } from "../../../../helpers/MDMConstants"
import { SeasonalityQuickFilterType } from "../../../../VectorFlow/types/MDM"
import { SeasonalityColorCellRendererWrapper, SeasonalityGrapCellRendererWrapper } from "./styles";


export const SeasonalityGraphCellRenderer = (params:any)=>{

    const onChartClick = () => {
        params.onShowChart(params.data);
    }
    
    return(
        <SeasonalityGrapCellRendererWrapper >
            <img src="/assets/img/VectorFLOW/NMS/seasonality-graph-icon.svg" height={28} width={28} onClick={onChartClick} data-testid="graph-icon"/>
        </SeasonalityGrapCellRendererWrapper>
    )
}


export const SeasonalityColorCellRenderer = (params:any)=>{

    const stateColor = seasonalityQuickFilterData.find((s:SeasonalityQuickFilterType)=>s.id.includes(params.data.sts))?.color || 'white'

    return <SeasonalityColorCellRendererWrapper stateColor={stateColor}/>
}