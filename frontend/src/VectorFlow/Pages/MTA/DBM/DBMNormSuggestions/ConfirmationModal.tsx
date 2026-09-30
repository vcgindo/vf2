import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline";
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import {ConfirmationDataTextContainer, ConfirmationDataButtonWrapper} from './styles'
import { useUserData } from "../../../../../context";
 
interface ConfirmationDataModalProps{
    mode: "norm" | "sleep";
    onFailure:()=>void;
    onSuccess:()=>void;
    onCloseModal:()=>void;
}
const ConfirmationDataModal=(props:ConfirmationDataModalProps)=>{
 
    const{
        onFailure,
        onSuccess,
        onCloseModal,
        mode,
    } = props
 
    const {user} = useUserData()
 
    return (
        <VFModalCard headerText="Confirmation!" openModal={true} closeModal={onCloseModal} headerIcon={""} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}>
            <ConfirmationDataTextContainer>
            {mode === "sleep"
                    ? "Selected SKU Code and Location Code will be sleep. Are you sure?"
                    : "Selected norms will be accepted. Are you sure?"}
            </ConfirmationDataTextContainer>
            <ConfirmationDataButtonWrapper>
                <VFButtonOutline themeUi={user.user.theme_ui} onClick={onFailure} onHoverChild={
                <>
                    No  
                </>
                }>
                    No
                </VFButtonOutline>
                <VFButton themeUi={user.user.theme_ui} onClick={onSuccess}>
                    Yes
                </VFButton>
            </ConfirmationDataButtonWrapper>
        </VFModalCard>
    )
}
 
export default ConfirmationDataModal