import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { useUserData } from "../../../../../context";
import {ApproveModalText, ApproveButtonWrapper} from "./styles"

interface ApproveModalProps{
    onSuccess:()=>void;
}

const ApproveModal=(props:ApproveModalProps)=>{

    const {
    onSuccess
    }=props

    const {user} = useUserData()

    return(
        <VFModalCard headerText={'Approve/Reject'} closeModal={()=>(console.log())} openModal={true} headerIcon={""} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}>
            <ApproveModalText>Data Submitted Successfully</ApproveModalText>
            <ApproveButtonWrapper>
                <VFButton themeUi={user.user.theme_ui} onClick={onSuccess} width={107}>
                    <img src="/assets/img/VectorFLOW/NMS/tick.svg" style={{height:"13px", width:"13px", opacity:"1",paddingRight:"17px"}}/>
                    Ok</VFButton>
            </ApproveButtonWrapper>
        </VFModalCard>
    )
}

export default ApproveModal