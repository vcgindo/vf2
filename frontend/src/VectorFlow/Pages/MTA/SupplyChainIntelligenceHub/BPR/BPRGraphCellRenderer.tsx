import { BPRGraphCellRendererWrapper } from "./styles"


const BPRGraphCellRenderer = (params:any)=>{
    return(
        <BPRGraphCellRendererWrapper src="/assets/img/VectorFLOW/NMS/seasonality-graph-icon.svg" onClick={()=>params.onOpenDailyDataGraph(params)}/>
    )
}

export default BPRGraphCellRenderer