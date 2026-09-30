import {BPRColorCellRendererWrapper} from '../../SupplyChainIntelligenceHub/BPR/styles'
import { Black, Green, Red, white, Yellow, Blue,gray, Grey } from '../../../../../styles/global'

const colorMapper =(color:string)=> {
    if(color==="White"){
        return {
            "bg": white,
            "text":Black
        }
    }
    if(color==="Green"){
        return {
            "bg":Green,
            "text":white
        }
    }
    if(color==="Yellow"){
        return {
            "bg":Yellow,
            "text":white
        }
    }
    if(color==="Red"){
        return {
            "bg":Red,
            "text":white
        }
    }
    if(color==="Blue"){
        return {
            "bg":Blue,
            "text":white
        }
    }
    if(color==="Grey"){
        return {
            "bg":Grey,
            "text":Black
        }
    }
    return{
        "bg":Black,
        "text":white
    }

}

const BTRColorCellRenderer = (params:any)=>{

    const color = parseFloat(params.value)
    const cellColor = colorMapper(params.data?.['C'+params.colDef.colId]);

    if(color===null || color===undefined || isNaN(color)){
        return(
            <BPRColorCellRendererWrapper style={{backgroundColor:gray,color:Black,maxWidth:85}} data-testid='color-cell'>
              X
            </BPRColorCellRendererWrapper>
        )

    }
    if(color==-99999999.00){
        return(
            <BPRColorCellRendererWrapper style={{backgroundColor:cellColor.bg,color:cellColor.bg,maxWidth:85}} data-testid='color-cell'>
               -999.99%
            </BPRColorCellRendererWrapper>
        )
    }

    return(
        <BPRColorCellRendererWrapper style={{backgroundColor:cellColor.bg,color:cellColor.text,maxWidth:85}} data-testid='color-cell'>
            {color.toFixed(2)}%
        </BPRColorCellRendererWrapper>
    )
}

export default BTRColorCellRenderer