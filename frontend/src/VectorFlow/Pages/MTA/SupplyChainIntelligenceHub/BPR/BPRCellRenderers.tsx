
// import { ICellRendererParams } from "ag-grid-enterprise"
import React from "react"
import { BPRColorCellRendererWrapper, 
    BPRTagsCellRendererWrapper,
    BPRRemarksCellRendererWrapper,
    BPRColorCellRendererIcon,
    BPRSubmitRemarkInput
} from "./styles"
import { useUserData } from "../../../../../context";


// interface BPRSubmitRemarkCellRendererProps extends ICellRendererParams{
//     onClick:(params:any)=>void
// }

// interface BPRRemarkHistoryCellRendererProps extends ICellRendererParams{
//     onClick:(e:any,params:any)=>void
// }

// interface ColorMapper {
//     [key: string]: {
//         bg: string;
//         text: string;
//     };
// }

const colorToColorMapper =(color:string)=> {

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
        case "Blue":
            return{
                "bg":"#355FD3",
                "text":"white"
            }
        default:
            return{
                "bg":"white",
                "text":"black"
            }
    }
}

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
        case "Grey":{
            return {
                "bg":"#D3D3D3",
                "text":"black"
            }
        }
        case "Blue": {
            return {
                "bg":"blue",
                "text":"white"
            }
        }
        default:
            return{  
                "bg":"white",
                "text":"black"
            }
    }
}

export const BPRTechColorCellRenderer = (params:any)=>{
    const techColor = params?.data?.TechColor;
    // console.log("techColor", params.data)
    const cellColor = colorMapper(params?.data?.TechColor)

    if(!techColor || techColor.length<0 ){
        return(
            // <BPRColorCellRendererWrapper style={{backgroundColor:cellColor.bg,color:cellColor.text,maxWidth:90}} data-testid='bpr-tech-color-cell'>
            //     NULL
            // </BPRColorCellRendererWrapper>
            <React.Fragment/>
        )
    }

    if(params.data.TechPen== null){
        return (
            <BPRColorCellRendererWrapper onClick={()=>console.log(params)} style={{backgroundColor:cellColor.bg,maxWidth:90}}>
            </BPRColorCellRendererWrapper>        
            )
    }
    if(params.data.TechPen == "") {
        return(
            <BPRColorCellRendererWrapper onClick={()=>console.log(params)} style={{backgroundColor:cellColor.bg,color:cellColor.text,maxWidth:90}}>
                {params.data.TechPen}
            </BPRColorCellRendererWrapper>
        )
    }
    return(
        <BPRColorCellRendererWrapper onClick={()=>console.log(params)} style={{backgroundColor:cellColor.bg,color:cellColor.text,maxWidth:90}}>
            {params.data.TechPen}%
        </BPRColorCellRendererWrapper>
    )
}


export const TextToTextColorMapper = (params:any)=>{

    const styles = colorToColorMapper(params.value)
    return(
        <BPRColorCellRendererWrapper onClick={()=>console.log(params)} style={{backgroundColor:styles.bg,color:styles.text,maxWidth:90}}>
            {params.value}
        </BPRColorCellRendererWrapper>
    )
}

export const BPREcoColorCellRenderer = (params:any)=>{
    
    const ecoColor = params?.data?.EcoColor

    const cellColor = colorMapper(ecoColor)

    if(!ecoColor || ecoColor?.length<0 ){
        return(
            // <BPRColorCellRendererWrapper style={{backgroundColor:cellColor.bg,color:cellColor.text,maxWidth:90}}>
            //     NULL
            // </BPRColorCellRendererWrapper>
            <React.Fragment/>
        )
    }

    if(params.data.EcoPen == null){
        return (
            <BPRColorCellRendererWrapper onClick={()=>console.log(params)} style={{backgroundColor:cellColor.bg,maxWidth:90}}>
            </BPRColorCellRendererWrapper>        
            )
    }

    return(
        <BPRColorCellRendererWrapper style={{backgroundColor:cellColor.bg,color:cellColor.text,maxWidth:90}}>
            {params.data.EcoPen}%
        </BPRColorCellRendererWrapper>
    )
}

export const BPRTagsCellRenderer = (params:any)=>{
    const { user } = useUserData();

    if(!params.value ||  params.value.length===0){
        return null
    }
    return(
        <BPRTagsCellRendererWrapper theme={user.user.theme_ui} style={{height:18,padding:"0px 3px",fontSize:9,width:55}}>
            {params.value}
        </BPRTagsCellRendererWrapper>
    )
}



export const BPRSubmitRemarkCellRenderer = (params:any)=>{


    return(
        <BPRRemarksCellRendererWrapper>
            <BPRSubmitRemarkInput 
            // ref={(ref) => {
            //     if (!ref) return;

            //     ref.onclick = (e:any) => {
            //         params.onClick(e,{skucode:params.data.SKUCode,whcode:params.data.WHCode})
            //         e.stopPropagation();
            //     };
            // }}
            >
                {params.value?params.value:params.data.remarks}
            </BPRSubmitRemarkInput>
        </BPRRemarksCellRendererWrapper>
    )
}

export const BPRRemarksCellRenderer = (params:any)=>{

   
    return (
        <BPRRemarksCellRendererWrapper >
            <BPRColorCellRendererIcon 
            alt="eye icon"
             src="/assets/img/VectorFLOW/BPR/history.svg"
             ref={(ref) => {
                if (!ref) return;
        
                ref.onclick = (e:any) => {
                 params.onClick(e, {skucode:params.data.SKUCode,whcode:params.data.WHCode})
                  e.stopPropagation();
                };
              }}
             />
        </BPRRemarksCellRendererWrapper>
    )
}
