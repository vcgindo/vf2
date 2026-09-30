import {BPRColorCellRendererWrapper} from '../../SupplyChainIntelligenceHub/BPR/styles'


const colorMapper =(color:string)=> {
    if(color==="White"){
        return {
            "bg":"white",
            "text":"black"
        }
    }
    if(color==="Green"){
        return {
            "bg":"#418D18",
            "text":"white"
        }
    }
    if(color==="Yellow"){
        return {
            "bg":"#EBBF2B",
            "text":"white"
        }
    }
    if(color==="Red"){
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
    const color = params.value

    const cellColor = colorMapper(color)
    

    if(!color){
        return(
            <BPRColorCellRendererWrapper style={{backgroundColor:"white",color:"black",maxWidth:90}} data-testid='color-cell'>
                NULL
            </BPRColorCellRendererWrapper>
        )
    }

    return(
        <BPRColorCellRendererWrapper style={{backgroundColor:cellColor.bg,color:cellColor.text,maxWidth:90}} data-testid='color-cell'>
            {color}
        </BPRColorCellRendererWrapper>
    )
}

export default ColorCellRenderer