import VFButtonOutline from "../../VFButtonOutline"
import VFModalCard from "../../VFModalCard"

interface VFWarningModalProps{
    warningMsg:string,
    actionButtonText: string,
    showWarningModal: boolean,
    onCloseWarningModal?: () => void,
    themeUI:any
}

const VFWarningModal = (props: VFWarningModalProps) => {

    const {
        warningMsg,
        actionButtonText,
        showWarningModal,
        onCloseWarningModal,
        themeUI
    } = props

    return (
        <VFModalCard headerText={"Warning"} openModal={showWarningModal} closeModal={onCloseWarningModal} headerIcon={'/assets/img/VectorFLOW/NMS/warning.svg'} closeIcon={'/assets/img/VectorFLOW/NMS/close-dark.svg'}>
            <p data-testid="warning-test" style={{ textAlign: "center", color: "#313131", paddingTop: "36px", fontStyle: "normal", fontVariant: "normal", fontWeight: 300, fontSize: "16px", fontFamily: "Roboto", width: '400px' }}>
                {warningMsg}
            </p>
            <div style={{ display: "flex", gap: "28px", alignItems: "center", justifyContent: "center", paddingTop: "38px", paddingBottom: "36px" }}>
                <VFButtonOutline themeUi={themeUI} onClick={() => onCloseWarningModal && onCloseWarningModal()}>{actionButtonText}</VFButtonOutline>
            </div>
        </VFModalCard>
    )
}

export default VFWarningModal;