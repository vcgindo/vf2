import React from "react";
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard";
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import { useUserData } from "../../../../../context";


interface WarningModalProps{
    rowsPerPage:number
    count:number
    showAll:boolean
    onSuccess:()=>void
    onFailure:()=>void
    onCloseModal:()=>void
    
    
}


const WarningModal = (props:WarningModalProps) =>{

    const {
        rowsPerPage,
        count,
        onFailure,
        onSuccess,
        onCloseModal,
        showAll,
    } = props

    const {user} = useUserData()

    if(count===0 && !showAll){
        return(
        <VFModalCard headerText={"Warning"} openModal={true} closeModal={onCloseModal} headerIcon={'/assets/img/VectorFLOW/NMS/warning.svg'} closeIcon={'/assets/img/VectorFLOW/NMS/close-dark.svg'}>
            <p data-testid="warning-test" style={{textAlign:"center", color: "#313131", paddingTop:"36px", fontStyle:"normal", fontVariant:"normal",fontWeight:300,fontSize:"16px",fontFamily:"Roboto",width:'400px'}}>
                There is no data available for selected filters
                </p> 
            <div style={{display:"flex",gap:"28px", alignItems:"center", justifyContent:"center", paddingTop:"38px", paddingBottom:"36px"}}>
                <VFButtonOutline  themeUi={user.user.theme_ui} onClick={onFailure}>OK</VFButtonOutline>
            </div>
        </VFModalCard>
        )
    }

    if(count===0){
        return(
            <VFModalCard headerText={"Warning"} openModal={true} closeModal={onCloseModal} headerIcon={'/assets/img/VectorFLOW/NMS/warning.svg'} closeIcon={'/assets/img/VectorFLOW/NMS/close-dark.svg'}>
                <p data-testid="warning-test" style={{textAlign:"center", color: "#313131", paddingTop:"36px", fontStyle:"normal", fontVariant:"normal",fontWeight:300,fontSize:"16px",fontFamily:"Roboto",width:'400px'}}>
                    There is no data available 
                    </p> 
                <div style={{display:"flex",gap:"28px", alignItems:"center", justifyContent:"center", paddingTop:"38px", paddingBottom:"36px"}}>
                    <VFButtonOutline  themeUi={user.user.theme_ui} onClick={onFailure}>OK</VFButtonOutline>
                </div>
            </VFModalCard>
            )
    }

    return(
       <VFModalCard headerText={"Warning"} openModal={true} closeModal={onCloseModal} headerIcon={'/assets/img/VectorFLOW/NMS/warning.svg'} closeIcon={'/assets/img/VectorFLOW/NMS/close-dark.svg'}>
            <p data-testid="warning-test" style={{textAlign:"center", color: "#313131", paddingTop:"36px", fontStyle:"normal", fontVariant:"normal",fontWeight:300,fontSize:"16px",fontFamily:"Roboto"}}>This filter returns <b>{count}</b> {count>rowsPerPage ? `records that will be open across mutiple pages` :count>1? `records`:`record`}.<br/>Do you want to continue?</p> 
            <div style={{zoom:'0.8',display:"flex",gap:"28px", alignItems:"center", justifyContent:"flex-end",padding:'10px 20px 10px 30px',margin:'50px -80px 0px -80px',borderTop:'dashed 1px gray'}}>
           <VFButtonOutline themeUi={user.user.theme_ui} onClick={onFailure}>No</VFButtonOutline>
           <VFButton themeUi={user.user.theme_ui} onClick={onSuccess}>Yes</VFButton>
           </div>
       </VFModalCard>
    )
}

export default WarningModal;