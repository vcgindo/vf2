import {BPRColorCellRendererWrapper} from '../../SupplyChainIntelligenceHub/BPR/styles'

const colorMapper =(color:number)=> {
    if(color<0){
        return {
            "bg":"#cecece",
            "text":"black"
        }
    }
    if(color>=0 && color<33.33){
        return {
            "bg":"#418D18",
            "text":"white"
        }
    }
    if(color>=33.33 && color<66.67){
        return {
            "bg":"#EBBF2B",
            "text":"white"
        }
    }
    if(color>=66.67 && color<100.00){
        return {
            "bg":"#F04D4D",
            "text":"white"
        }
    }
    return{
        "bg":"#000000",
        "text":"white"
    }

}

 const ColorCellRenderer = (params:any)=>{

    const color = parseFloat(params.value)


    const cellColor = colorMapper(params.value)

    if(color===null || color===undefined || isNaN(color)){
        return(
            <>
            
            </>
        )
    }

    if(color<=-99999999.00){
        return(
            <BPRColorCellRendererWrapper style={{backgroundColor:cellColor.bg,color:cellColor.text,maxWidth:85}} data-testid='color-cell'>
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

export default ColorCellRenderer