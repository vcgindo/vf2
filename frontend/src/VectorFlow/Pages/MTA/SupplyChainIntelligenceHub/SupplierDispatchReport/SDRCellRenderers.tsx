import {SDRColorCellRendererWrapper} from './styles'

const colorMapper =(color:string)=> {

    switch (color){
        case "White":
            return {
                "bg":"white",
                "text":"black"
            }
        case "Yellow":
            return {
                "bg":"#EBBF2B",
                "text":"white"
            }
        case "Green":
            return {
                "bg":"#418D18",
                "text":"white"
            }
        case "Red":
            return {
                "bg":"#F04D4D",
                "text":"white"
            }
        case "Black":
            return{
                "bg":"#000000",
                "text":"white"
            }
        default:
            return{
                "bg":"white",
                "text":"black"
            }
    }
}
export const SDRDispatchColorCellRenderer = (params:any)=>{

    const ecoColor = params.data?.DispatchColor

    const cellColor = colorMapper(ecoColor)

    if(!ecoColor || ecoColor.lenght<1){
        return(
            ""  
            // <SDRColorCellRendererWrapper style={{backgroundColor:cellColor.bg,color:cellColor.text}}>
            //     NULL
            // </SDRColorCellRendererWrapper>
        )
    }

    return(
        <SDRColorCellRendererWrapper style={{backgroundColor:cellColor.bg,color:cellColor.text}}>
            {params.data.DispatchPen}%
        </SDRColorCellRendererWrapper>
    )
}
