import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline"
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { useUserData } from "../../../../../context";
import {DeleteFileModalText, ButtonWrapper} from "./styles"

interface DeleteFileModalProps{
    onFailure:()=>void;
    onSuccess:()=>void;
}

const DeleteFileModal=(props:DeleteFileModalProps)=>{

    const {
    onFailure,
    onSuccess
    }=props

    const {user} = useUserData()

    return(
        <VFModalCard headerText={'Delete file'} closeModal={()=>(console.log())} openModal={true} headerIcon={""} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}>
            <DeleteFileModalText>Are you sure you want to submit the task?</DeleteFileModalText>
            <ButtonWrapper>
                <VFButtonOutline color={"gray"} themeUi={user.user.theme_ui} onClick={onFailure} onHoverChild={
                    <>
                    <img src="/assets/img/VectorFLOW/NMS/close-white.svg" style={{height:"13px", width:"13px", opacity:"1",paddingRight:"17px"}}/>
                    No
                    </>
                }>
                    <img src="/assets/img/VectorFLOW/NMS/close.svg" style={{height:"13px", width:"13px", opacity:"1",paddingRight:"17px"}}/> 
                    No</VFButtonOutline>
                <VFButton themeUi={user.user.theme_ui} onClick={onSuccess}>
                    <img src="/assets/img/VectorFLOW/NMS/tick.svg" style={{height:"13px", width:"13px", opacity:"1",paddingRight:"17px"}}/>
                    Yes</VFButton>
            </ButtonWrapper>
        </VFModalCard>
    )
}

export default DeleteFileModal