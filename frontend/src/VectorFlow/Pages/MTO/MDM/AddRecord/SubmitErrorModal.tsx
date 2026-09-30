import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import {SubmitDataTextContainer, SubmitDataButtonWrapper} from './styles'
import { useUserData } from "../../../../../context";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";

interface SubmitErrorModalProps{
    totalCount:number;
    recordCount:number;
    errorCount:number;
    onSuccess:()=>void;
    onCloseModal:()=>void;
}
const SubmitErrorModal=(props:SubmitErrorModalProps)=>{

    const{
        totalCount,
        recordCount,
        errorCount,
        onSuccess,
        onCloseModal
    } = props

    const {user} = useUserData()

    return (
        <VFModalCard headerText="Submit Data" openModal={true} closeModal={onCloseModal} headerIcon={""} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}>
            {
                recordCount!==errorCount
                ?
                <SubmitDataTextContainer>
                    No data was submiited
                   <b>{errorCount}</b>  out of <b>{totalCount}</b>  records are have errors
                </SubmitDataTextContainer>
                :
                <SubmitDataTextContainer>
                    <b>{recordCount}</b> Records submitted successfully!<br/><br/>
                    <b>{errorCount}</b> out of <b>{totalCount}</b> records are have errors
                </SubmitDataTextContainer>
            }
            <SubmitDataButtonWrapper>
                <VFButton themeUi={user.user.theme_ui} style={{color:'gray'}} onClick={onSuccess} width={173} onHoverChild={
                <>
                    Yes 
                </>
                }>
                    Yes 
                </VFButton>
            </SubmitDataButtonWrapper>
        </VFModalCard>
    )
}

export default SubmitErrorModal